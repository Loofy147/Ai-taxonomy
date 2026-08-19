import pytest
import jsonschema
from pif.schema import validate_tool_contract, validate_meta_procedure

def test_tool_contract_validation():
    valid_tool = {
        "name": "backup_database",
        "description": "Triggers a full database backup to cloud storage.",
        "category": "atomic",
        "is_side_effecting": True,
        "requires_hitl_approval": True,
        "inputSchema": {
            "type": "object",
            "properties": {"db_name": {"type": "string"}},
            "required": ["db_name"]
        },
        "outputSchema": {
            "type": "object",
            "properties": {"snapshot_id": {"type": "string"}},
            "required": ["snapshot_id"]
        }
    }
    validate_tool_contract(valid_tool)

    invalid_tool = {
        "name": "invalid name with spaces",
        "description": "Invalid tool"
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_tool_contract(invalid_tool)

def test_meta_procedure_validation():
    valid_dag = {
        "goal_specification": "Migrate schema and backup database",
        "steps": [
            {
                "step_id": 1,
                "procedure_name": "backup_database",
                "arguments_mapping": {"db_name": "production"},
                "dependencies": []
            }
        ]
    }
    validate_meta_procedure(valid_dag)
