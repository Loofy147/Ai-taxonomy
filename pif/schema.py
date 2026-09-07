import json
from pathlib import Path
from typing import Dict, Any
import jsonschema

SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"

def load_schema(schema_name: str) -> Dict[str, Any]:
    schema_path = SCHEMAS_DIR / schema_name
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

TOOL_CONTRACT_SCHEMA = load_schema("tool_contract.json")
META_PROCEDURE_SCHEMA = load_schema("meta_procedure.json")

# Pre-compile validators for static framework schemas to avoid re-parsing overhead
_TOOL_CONTRACT_VALIDATOR = jsonschema.validators.validator_for(TOOL_CONTRACT_SCHEMA)(TOOL_CONTRACT_SCHEMA)
_META_PROCEDURE_VALIDATOR = jsonschema.validators.validator_for(META_PROCEDURE_SCHEMA)(META_PROCEDURE_SCHEMA)

def validate_tool_contract(tool_dict: Dict[str, Any]) -> None:
    """
    Validates a tool contract dictionary against schemas/tool_contract.json
    """
    _TOOL_CONTRACT_VALIDATOR.validate(instance=tool_dict)

def validate_meta_procedure(meta_dict: Dict[str, Any]) -> None:
    """
    Validates a synthesized meta procedure DAG dictionary against schemas/meta_procedure.json
    """
    _META_PROCEDURE_VALIDATOR.validate(instance=meta_dict)
