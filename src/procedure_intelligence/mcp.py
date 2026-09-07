"""Model Context Protocol (MCP) transport adapters with security & URL validation."""

from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlparse
import json

from procedure_intelligence.taxonomy import ProcedureMetadata, get_procedure_metadata
from procedure_intelligence.schema import SchemaValidator, SchemaValidationError


class SecurityError(Exception):
    """Raised when security checks like authorization URL validation fail."""
    pass


def validate_authorization_server_url(url: str, allowed_domains: Optional[List[str]] = None) -> bool:
    """Validates remote MCP authorization server URLs to prevent SSRF and data exfiltration."""
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        raise SecurityError(f"Invalid scheme in authorization server URL: {parsed.scheme}. Must be HTTP or HTTPS.")

    if not parsed.netloc:
        raise SecurityError("Authorization server URL missing domain hostname.")

    if allowed_domains:
        domain = parsed.netloc.split(":")[0]
        if not any(domain == allowed or domain.endswith("." + allowed) for allowed in allowed_domains):
            raise SecurityError(f"Domain '{domain}' is not in allowed authorization server domains list.")

    return True


class MCPAdapter:
    """Model Context Protocol (MCP) integration layer (supporting local stdio and remote HTTP/SSE over JSON-RPC 2.0)."""

    def __init__(self, transport_type: str = "stdio", server_url: Optional[str] = None) -> None:
        self.transport_type = transport_type
        self.server_url = server_url
        self._registered_tools: Dict[str, Callable] = {}

        if server_url and transport_type in ("http", "sse"):
            validate_authorization_server_url(server_url)

    def register_tool(self, func: Callable) -> None:
        """Registers a procedure as an MCP tool."""
        meta = get_procedure_metadata(func)
        tool_name = meta.name if meta else func.__name__
        self._registered_tools[tool_name] = func

    def list_mcp_tools(self) -> Dict[str, Any]:
        """Returns MCP tools list compliant with MCP JSON-RPC protocol specification."""
        tools = []
        for name, func in self._registered_tools.items():
            meta = get_procedure_metadata(func)
            if meta:
                input_schema = SchemaValidator.enforce_strict_input_schema(meta)
                tools.append({
                    "name": meta.name,
                    "description": meta.description,
                    "inputSchema": input_schema,
                    "outputSchema": meta.output_schema,
                })
            else:
                tools.append({
                    "name": name,
                    "description": func.__doc__ or name,
                    "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                })
        return {"tools": tools}

    def handle_jsonrpc_request(self, request_payload: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Handles incoming JSON-RPC 2.0 request (tools/list or tools/call)."""
        if isinstance(request_payload, str):
            payload = json.loads(request_payload)
        else:
            payload = request_payload

        req_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params", {})

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": self.list_mcp_tools(),
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self._registered_tools:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method/Tool '{tool_name}' not found."},
                }

            func = self._registered_tools[tool_name]
            meta = get_procedure_metadata(func)

            try:
                if meta:
                    SchemaValidator.validate_input(meta, arguments)

                result = func(**arguments)

                if meta:
                    SchemaValidator.validate_output(meta, result)

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": str(result)}]},
                }
            except Exception as err:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": f"Tool execution failed: {str(err)}"},
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not supported."},
            }
