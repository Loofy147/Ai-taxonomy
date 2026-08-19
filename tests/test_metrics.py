from pif.models import ToolContract
from pif.metrics import PIVSEvaluator

def test_pivs_score_calculation():
    tool = ToolContract(
        name="deploy_service",
        description="Deploys container microservice to Kubernetes cloud cluster safely with health checks",
        category="atomic",
        is_side_effecting=True,
        requires_hitl_approval=True,
        inputSchema={"type": "object", "properties": {"cluster": {"type": "string"}}, "required": ["cluster"]},
        outputSchema={"type": "object", "properties": {"deployment_id": {"type": "string"}}}
    )

    evaluator = PIVSEvaluator()
    metrics = evaluator.evaluate_tool(tool, historical_success_rate=0.95)

    assert metrics["pivs_score"] > 0.7
    assert metrics["schema_rigor_score"] == 1.0
