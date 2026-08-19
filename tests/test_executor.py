import pytest
from pif.models import ToolContract, MetaProcedureDAG, DAGStep
from pif.executor import ExecutorEngine, ExecutionError, HITLApprovalRequired

def test_executor_dag_and_rollback():
    db_state = {"backed_up": False, "migrated": False}

    def backup_handler(args):
        db_state["backed_up"] = True
        return {"status": "ok"}

    def rollback_backup(args):
        db_state["backed_up"] = False
        return {"status": "rolled_back"}

    def migrate_handler(args):
        raise RuntimeError("Migration script syntax error")

    tool_backup = ToolContract(
        name="backup_db",
        description="Backup database",
        is_side_effecting=True,
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object", "properties": {"status": {"type": "string"}}}
    )
    tool_migrate = ToolContract(
        name="migrate_db",
        description="Migrate database",
        is_side_effecting=True,
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object", "properties": {}}
    )
    tool_rollback_backup = ToolContract(
        name="undo_backup_db",
        description="Undo backup",
        is_side_effecting=True,
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object", "properties": {"status": {"type": "string"}}}
    )

    registry = {
        "backup_db": tool_backup,
        "migrate_db": tool_migrate,
        "undo_backup_db": tool_rollback_backup
    }

    handlers = {
        "backup_db": backup_handler,
        "migrate_db": migrate_handler,
        "undo_backup_db": rollback_backup
    }

    executor = ExecutorEngine(registry, handlers)

    dag = MetaProcedureDAG(
        goal_specification="Backup and migrate",
        steps=[
            DAGStep(
                step_id=1,
                procedure_name="backup_db",
                arguments_mapping={},
                dependencies=[],
                compensating_procedure={"procedure_name": "undo_backup_db", "arguments_mapping": {}}
            ),
            DAGStep(
                step_id=2,
                procedure_name="migrate_db",
                arguments_mapping={},
                dependencies=[1]
            )
        ]
    )

    with pytest.raises(ExecutionError) as exc_info:
        executor.execute_dag(dag)

    assert "Execution failed at Step 2" in str(exc_info.value)
    # Rollback should have set backed_up back to False
    assert db_state["backed_up"] is False


def test_executor_with_structured_reviews():
    def dummy_handler(args):
        return {"status": "ok"}

    tool = ToolContract(
        name="simple_tool",
        description="A safe tool",
        is_side_effecting=False,
        inputSchema={"type": "object", "properties": {"param": {"type": "string"}}, "required": ["param"]},
        outputSchema={"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]}
    )

    registry = {"simple_tool": tool}
    handlers = {"simple_tool": dummy_handler}

    executor = ExecutorEngine(registry, handlers)

    dag = MetaProcedureDAG(
        goal_specification="Run simple tool",
        steps=[
            DAGStep(
                step_id=1,
                procedure_name="simple_tool",
                arguments_mapping={"param": "hello"},
                dependencies=[]
            )
        ]
    )

    res = executor.execute_dag(dag)
    assert res["status"] == "SUCCESS"
    assert "assessment" in res
    assert res["assessment"].overall_score == 1.0
    assert res["assessment"].passed_steps == 1
