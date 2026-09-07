import pytest
from pif.models import ToolContract, DAGStep, MetaProcedureDAG, CriticismSeverity, HoareTriple
from pif.review import ReviewEngine

def test_pre_execution_review_hitl_missing():
    tool = ToolContract(
        name="drop_db",
        description="Destructive table drop procedure",
        is_side_effecting=True,
        requires_hitl_approval=True,
        inputSchema={"type": "object", "properties": {"table": {"type": "string"}}, "required": ["table"]},
        outputSchema={"type": "object"}
    )
    step = DAGStep(
        step_id=1,
        procedure_name="drop_db",
        arguments_mapping={"table": "users"},
        dependencies=[]
    )

    review_engine = ReviewEngine()
    review = review_engine.review_step_pre_execution(
        step=step,
        tool=tool,
        resolved_args={"table": "users"},
        hitl_approved=False
    )

    assert review.passed is False
    assert review.severity == CriticismSeverity.CRITICAL
    assert any("HITL approval" in c for c in review.criticisms)

def test_post_execution_review_and_assessment():
    tool = ToolContract(
        name="backup_db",
        description="Creates database backup",
        is_side_effecting=True,
        hoare_logic_contract=HoareTriple(
            precondition="db_online",
            postcondition="backup_created"
        ),
        inputSchema={"type": "object", "properties": {"db": {"type": "string"}}, "required": ["db"]},
        outputSchema={"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]}
    )
    step = DAGStep(
        step_id=1,
        procedure_name="backup_db",
        arguments_mapping={"db": "prod"},
        dependencies=[],
        compensating_procedure={"procedure_name": "delete_backup", "arguments_mapping": {}}
    )

    review_engine = ReviewEngine()
    pre_review = review_engine.review_step_pre_execution(step, tool, {"db": "prod"}, hitl_approved=True)
    assert pre_review.passed is True

    post_review = review_engine.review_step_post_execution(step, tool, {"status": "ok"}, pre_review)
    assert post_review.passed is True
    assert post_review.score == 1.0

    dag = MetaProcedureDAG(goal_specification="Prod Backup", steps=[step])
    assessment = review_engine.assess_dag_execution(dag, [post_review])

    assert assessment.passed_steps == 1
    assert assessment.overall_score == 1.0
    assert "1/1 steps passed" in assessment.summary
