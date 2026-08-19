"""Schema generation and validation module enforcing strict schema compliance."""

from typing import Any, Dict, Optional
import jsonschema
from jsonschema.exceptions import ValidationError

from procedure_intelligence.taxonomy import ProcedureMetadata


class SchemaValidationError(Exception):
    """Raised when input parameters or output payloads fail strict schema validation."""
    pass


class SchemaValidator:
    """Handles strict JSON schema enforcement for inputs and outputs."""

    @staticmethod
    def enforce_strict_input_schema(metadata: ProcedureMetadata) -> Dict[str, Any]:
        """Ensures the input schema has strict=True semantics: additionalProperties=False."""
        schema = dict(metadata.input_schema)
        if schema.get("type") == "object" and "additionalProperties" not in schema:
            schema["additionalProperties"] = False
        return schema

    @staticmethod
    def validate_input(metadata: ProcedureMetadata, arguments: Dict[str, Any]) -> None:
        """Validates procedure invocation arguments against strict inputSchema."""
        strict_schema = SchemaValidator.enforce_strict_input_schema(metadata)
        try:
            jsonschema.validate(instance=arguments, schema=strict_schema)
        except ValidationError as e:
            raise SchemaValidationError(f"Input validation failed for '{metadata.name}': {e.message}") from e

    @staticmethod
    def validate_output(metadata: ProcedureMetadata, result: Any) -> None:
        """Validates procedure return payloads against outputSchema."""
        if not metadata.output_schema:
            return
        try:
            jsonschema.validate(instance=result, schema=metadata.output_schema)
        except ValidationError as e:
            raise SchemaValidationError(f"Output validation failed for '{metadata.name}': {e.message}") from e
