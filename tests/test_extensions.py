import pytest
import pif
from pif import (
    ToolContract,
    MetaProcedureDAG,
    DAGStep,
    ExecutorEngine,
    ExecutionError,
    ToolRouter,
    PIVSEvaluator,
)

def test_package_exports():
    assert hasattr(pif, "ExecutorEngine")
    assert hasattr(pif, "ToolContract")
    assert hasattr(pif, "MetaProcedureDAG")
    assert hasattr(pif, "ToolRouter")
    assert hasattr(pif, "PIVSEvaluator")
    assert hasattr(pif, "FormalVerificationEngine")
    assert hasattr(pif, "ReviewEngine")

def test_executor_deep_reference_resolution():
    def step1_handler(args):
        return {
            "user": {
                "id": 42,
                "profile": {"email": "user@example.com"}
            },
            "tags": ["admin", "active"]
        }

    def step2_handler(args):
        return {
            "processed_id": args["user_id"],
            "user_email": args["email"],
            "primary_tag": args["tag"]
        }

    t1 = ToolContract(
        name="get_user",
        description="Get user details",
        is_side_effecting=False,
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object"}
    )

    t2 = ToolContract(
        name="process_user",
        description="Process user details",
        is_side_effecting=False,
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "email": {"type": "string"},
                "tag": {"type": "string"}
            },
            "required": ["user_id", "email", "tag"]
        },
        outputSchema={"type": "object"}
    )

    registry = {"get_user": t1, "process_user": t2}
    handlers = {"get_user": step1_handler, "process_user": step2_handler}

    executor = ExecutorEngine(registry, handlers)

    dag = MetaProcedureDAG(
        goal_specification="Resolve nested step outputs",
        steps=[
            DAGStep(step_id=1, procedure_name="get_user", arguments_mapping={}, dependencies=[]),
            DAGStep(
                step_id=2,
                procedure_name="process_user",
                arguments_mapping={
                    "user_id": "$steps[1].user.id",
                    "email": "$steps[1].user.profile.email",
                    "tag": "$steps[1].tags.0"
                },
                dependencies=[1]
            )
        ]
    )

    res = executor.execute_dag(dag)
    assert res["status"] == "SUCCESS"
    step2_out = res["step_outputs"][2]
    assert step2_out["processed_id"] == 42
    assert step2_out["user_email"] == "user@example.com"
    assert step2_out["primary_tag"] == "admin"

def test_executor_react_loop_and_circuit_breaker():
    def search_tool(args):
        return {"items": ["result1", "result2"]}

    t1 = ToolContract(
        name="search",
        description="Search items",
        is_side_effecting=False,
        inputSchema={"type": "object", "properties": {"query": {"type": "string"}}},
        outputSchema={"type": "object"}
    )

    registry = {"search": t1}
    handlers = {"search": search_tool}

    executor = ExecutorEngine(registry, handlers)

    # ReAct loop success scenario
    def decide_finish(history, context):
        if not history:
            return {"type": "action", "tool_name": "search", "args": {"query": "test"}}
        return {"type": "finish", "result": history[0]["observation"]["items"]}

    res = executor.execute_react_loop(decide_finish)
    assert res["status"] == "SUCCESS"
    assert res["iterations"] == 2
    assert res["result"] == ["result1", "result2"]

    # ReAct loop circuit breaker scenario
    def decide_infinite(history, context):
        return {"type": "action", "tool_name": "search", "args": {"query": "loop"}}

    with pytest.raises(ExecutionError) as exc_info:
        executor.execute_react_loop(decide_infinite, max_iterations=3)

    assert "exceeded maximum allowed iterations limit" in str(exc_info.value)

def test_pivs_evaluate_registry():
    t1 = ToolContract(
        name="read_data",
        description="Reads data safely",
        is_side_effecting=False,
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object"}
    )
    t2 = ToolContract(
        name="delete_data",
        description="Deletes data permanently",
        is_side_effecting=True,
        requires_hitl_approval=True,
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object"}
    )

    evaluator = PIVSEvaluator()
    summary = evaluator.evaluate_registry({"read_data": t1, "delete_data": t2}, {"read_data": 1.0, "delete_data": 0.8})

    assert summary["total_tools"] == 2
    assert summary["side_effecting_tools"] == 1
    assert summary["hitl_protected_tools"] == 1
    assert summary["average_pivs_score"] > 0.0

def test_router_category_and_score_filtering():
    t1 = ToolContract(
        name="sql_query",
        description="Execute analytical query",
        category="data",
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object"}
    )
    t2 = ToolContract(
        name="sql_backup",
        description="Backup sql database",
        category="ops",
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object"}
    )

    router = ToolRouter({"sql_query": t1, "sql_backup": t2})

    res = router.route_and_filter("sql", category="data")
    assert len(res) == 1
    assert res[0].name == "sql_query"

    res_min_score = router.route_and_filter("unmatched query", min_score=10)
    assert len(res_min_score) == 0
