"""Tests for procedure taxonomy and schema validation modules."""

import pytest
from procedure_intelligence.taxonomy import (
    procedure,
    get_procedure_metadata,
    ExecutionNature,
    Statefulness,
    SideEffectLevel,
    MetaLevel,
)
from procedure_intelligence.schema import SchemaValidator, SchemaValidationError


def test_procedure_decorator_default():
    @procedure(name="simple_calc", description="Performs addition")
    def add(a: int, b: int) -> int:
        return a + b

    meta = get_procedure_metadata(add)
    assert meta is not None
    assert meta.name == "simple_calc"
    assert meta.description == "Performs addition"
    assert meta.dimensions.execution_nature == ExecutionNature.DETERMINISTIC
    assert meta.dimensions.statefulness == Statefulness.STATELESS
    assert meta.dimensions.side_effect == SideEffectLevel.READ_ONLY


def test_strict_schema_validation_success():
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["query"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "count": {"type": "integer"},
        },
    }

    @procedure(
        name="search_db",
        input_schema=input_schema,
        output_schema=output_schema,
    )
    def search_db(query: str, limit: int = 10):
        return {"count": 5}

    meta = get_procedure_metadata(search_db)

    # Valid arguments
    SchemaValidator.validate_input(meta, {"query": "SELECT 1", "limit": 10})

    # Valid return output
    res = search_db("SELECT 1")
    SchemaValidator.validate_output(meta, res)


def test_strict_schema_validation_extra_properties():
    input_schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer"},
        },
        "required": ["user_id"],
    }

    @procedure(name="get_user", input_schema=input_schema)
    def get_user(user_id: int):
        return {"user_id": user_id}

    meta = get_procedure_metadata(get_user)

    # Passing extra undeclared property should raise SchemaValidationError due to additionalProperties=False
    with pytest.raises(SchemaValidationError):
        SchemaValidator.validate_input(meta, {"user_id": 1, "injected_param": "malicious"})


def test_schema_validation_invalid_type():
    input_schema = {
        "type": "object",
        "properties": {
            "amount": {"type": "number"},
        },
    }

    @procedure(name="transfer", input_schema=input_schema)
    def transfer(amount: float):
        return True

    meta = get_procedure_metadata(transfer)

    with pytest.raises(SchemaValidationError):
        SchemaValidator.validate_input(meta, {"amount": "not_a_number"})
