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

def validate_tool_contract(tool_dict: Dict[str, Any]) -> None:
    """
    Validates a tool contract dictionary against schemas/tool_contract.json
    """
    jsonschema.validate(instance=tool_dict, schema=TOOL_CONTRACT_SCHEMA)

def validate_meta_procedure(meta_dict: Dict[str, Any]) -> None:
    """
    Validates a synthesized meta procedure DAG dictionary against schemas/meta_procedure.json
    """
    jsonschema.validate(instance=meta_dict, schema=META_PROCEDURE_SCHEMA)
