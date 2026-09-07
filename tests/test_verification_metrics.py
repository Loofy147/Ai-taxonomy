"""Tests for formal verification engine and procedure health metrics (PIVS)."""

import pytest
from procedure_intelligence.verification import (
    Predicate,
    HoareTriple,
    WeakestPrecondition,
    VerificationError,
)
from procedure_intelligence.metrics import PIVSCalculator
from procedure_intelligence.taxonomy import procedure, get_procedure_metadata, SideEffectLevel


def test_predicate_evaluation():
    pred1 = Predicate("x > 0 and y == 'active'")
    assert pred1.evaluate({"x": 10, "y": "active"}) is True
    assert pred1.evaluate({"x": -5, "y": "active"}) is False

    pred_error = Predicate("undefined_var == 1")
    with pytest.raises(VerificationError):
        pred_error.evaluate({})


def test_hoare_triple_verification():
    triple = HoareTriple(
        precondition=Predicate("balance >= amount and amount > 0"),
        command="withdraw",
        postcondition=Predicate("balance == old_balance - amount"),
    )

    initial_state = {"balance": 100, "amount": 30, "old_balance": 100}
    final_state = {"balance": 70, "amount": 30, "old_balance": 100}

    assert triple.verify(initial_state, final_state) is True

    invalid_initial = {"balance": 20, "amount": 30, "old_balance": 20}
    with pytest.raises(VerificationError):
        triple.verify(invalid_initial, final_state)


def test_weakest_precondition_calculation():
    # Postcondition Q: balance >= 0
    # Assignment: balance := balance - amount
    # wp(balance := balance - amount, balance >= 0) -> (balance - amount) >= 0
    post_q = Predicate("balance >= 0")
    wp_pred = WeakestPrecondition.calculate_wp("balance", "balance - amount", post_q)

    assert "balance - amount" in wp_pred.expression
    assert wp_pred.evaluate({"balance": 100, "amount": 40}) is True
    assert wp_pred.evaluate({"balance": 30, "amount": 50}) is False


def test_pivs_score_calculation():
    @procedure(
        name="critical_op",
        description="A critical mutative database procedure",
        side_effect=SideEffectLevel.NON_REVERSIBLE,
        input_schema={"type": "object", "properties": {"id": {"type": "integer"}}},
        preconditions=["id > 0"],
        postconditions=["status == 'deleted'"],
    )
    def critical_op(id: int):
        return True

    meta = get_procedure_metadata(critical_op)
    score = PIVSCalculator.compute_pivs(meta, total_invocations=100, successful_invocations=95)

    assert 0.0 <= score.pivs <= 100.0
    assert score.schema_clarity == 1.0
    assert score.historical_reliability == 0.95
    assert score.complexity_penalty > 0
