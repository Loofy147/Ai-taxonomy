"""Tests for router, orchestration (DAG, ReAct, HITL, Rollback), and MCP adapter."""

import pytest
from procedure_intelligence.taxonomy import procedure, get_procedure_metadata, SideEffectLevel
from procedure_intelligence.router import ToolRouter
from procedure_intelligence.orchestration import (
    PlannerExecutor,
    ReActAgent,
    TransactionManager,
    HITLGuard,
    HITLApprovalRequired,
)
from procedure_intelligence.mcp import MCPAdapter, validate_authorization_server_url, SecurityError


@procedure(name="compress_file", description="Compresses log files on disk", tags=["file", "compression"])
def compress_file(filepath: str) -> str:
    return f"{filepath}.gz"


@procedure(
    name="delete_database",
    description="Permanently drops database tables",
    side_effect=SideEffectLevel.NON_REVERSIBLE,
)
def delete_database(db_name: str) -> str:
    return f"Database {db_name} deleted"


def test_tool_router():
    router = ToolRouter()
    router.register(compress_file)
    router.register(delete_database)

    pruned = router.route_intent("please compress my log files", max_tools=1)
    assert len(pruned) == 1
    assert pruned[0].name == "compress_file"

    schemas = router.get_pruned_context_schemas("compress")
    assert len(schemas) == 1
    assert schemas[0]["name"] == "compress_file"


def test_hitl_guard():
    meta_non_rev = get_procedure_metadata(delete_database)
    guard = HITLGuard()

    with pytest.raises(HITLApprovalRequired):
        guard.verify_permission(meta_non_rev, action_id="delete_db_action")

    # Grant approval
    guard.grant_approval("delete_db_action")
    assert guard.verify_permission(meta_non_rev, action_id="delete_db_action") is True


def test_transaction_rollback():
    state = {"files_created": []}

    def create_file(path: str):
        state["files_created"].append(path)
        return path

    def remove_file(args: dict):
        state["files_created"].remove(args["path"])

    def failing_step(path: str):
        raise RuntimeError("Disk write failure")

    tx_manager = TransactionManager()

    # Step 1 succeeds
    tx_manager.execute_transactional(create_file, {"path": "file1.txt"}, rollback_action=remove_file)
    assert state["files_created"] == ["file1.txt"]

    # Step 2 fails and triggers rollback of step 1
    with pytest.raises(RuntimeError):
        tx_manager.execute_transactional(failing_step, {"path": "file2.txt"})

    assert state["files_created"] == []  # Rolled back file1.txt


def test_planner_executor_dag():
    registry = {
        "compress_file": compress_file,
    }
    planner = PlannerExecutor(registry)
    dag_nodes = [
        {"name": "compress_file", "args": {"filepath": "/var/log/app.log"}},
    ]

    res = planner.execute_dag(dag_nodes)
    assert res["compress_file"] == "/var/log/app.log.gz"


def test_react_agent_loop():
    registry = {"compress_file": compress_file}
    agent = ReActAgent(registry, max_iterations=3)

    def mock_step_generator(task: str, history: list):
        if not history:
            return {
                "thought": "I need to compress the file",
                "action": "compress_file",
                "action_args": {"filepath": "data.csv"},
            }
        return {
            "thought": "File compressed successfully. Task complete.",
            "is_done": True,
            "final_output": "Compressed data.csv into data.csv.gz",
        }

    out = agent.run_loop("Compress data.csv", mock_step_generator)
    assert out["status"] == "COMPLETED"
    assert out["final_output"] == "Compressed data.csv into data.csv.gz"


def test_mcp_adapter():
    mcp = MCPAdapter(transport_type="stdio")
    mcp.register_tool(compress_file)

    tools = mcp.list_mcp_tools()
    assert len(tools["tools"]) == 1
    assert tools["tools"][0]["name"] == "compress_file"

    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "compress_file",
            "arguments": {"filepath": "access.log"},
        },
    }

    resp = mcp.handle_jsonrpc_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["result"]["content"][0]["text"] == "access.log.gz"


def test_validate_authorization_server_url():
    assert validate_authorization_server_url("https://auth.example.com/oauth") is True

    with pytest.raises(SecurityError):
        validate_authorization_server_url("ftp://auth.example.com")

    with pytest.raises(SecurityError):
        validate_authorization_server_url("https://untrusted.com", allowed_domains=["example.com"])
