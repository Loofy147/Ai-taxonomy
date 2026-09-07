from pif.models import ToolContract, MetaProcedureDAG, DAGStep, HoareTriple
from pif.verification import FormalVerificationEngine

def test_formal_verification_weakest_precondition():
    tool1 = ToolContract(
        name="compress_logs",
        description="Compresses logs.",
        hoare_logic_contract=HoareTriple(
            precondition="file_exists(app.log)",
            postcondition="file_exists(app.tar.gz)"
        ),
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object"}
    )

    dag = MetaProcedureDAG(
        goal_specification="Compress logs",
        steps=[
            DAGStep(
                step_id=1,
                procedure_name="compress_logs",
                arguments_mapping={},
                dependencies=[]
            )
        ]
    )

    registry = {"compress_logs": tool1}
    proof = FormalVerificationEngine.verify_dag(
        dag=dag,
        tools_registry=registry,
        initial_state_conditions=["file_exists(app.log)"],
        target_postcondition="file_exists(app.tar.gz)"
    )

    assert proof.certified_safe is True
    assert "file_exists(app.log)" in proof.weakest_precondition
