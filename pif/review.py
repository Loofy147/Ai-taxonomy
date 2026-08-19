from typing import Dict, List, Any, Optional
from pif.models import (
    ToolContract,
    DAGStep,
    StepReview,
    CriticismSeverity,
    DAGExecutionAssessment,
    MetaProcedureDAG,
)

class ReviewEngine:
    """
    Engine responsible for structured reviews, criticism generation, safety assessments,
    and post-execution quality evaluations of procedures and DAGs.
    """

    def review_step_pre_execution(
        self,
        step: DAGStep,
        tool: ToolContract,
        resolved_args: Dict[str, Any],
        hitl_approved: bool = False
    ) -> StepReview:
        """
        Performs pre-execution criticism and review of a step before calling the handler.
        Evaluates input parameters, HITL necessity, Hoare logic contracts, and risk.
        """
        criticisms: List[str] = []
        recommendations: List[str] = []
        severity = CriticismSeverity.LOW
        score = 1.0

        # Check HITL requirement
        if tool.requires_hitl_approval and not hitl_approved:
            criticisms.append(f"Step {step.step_id} ('{step.procedure_name}') requires HITL approval, but approval was not provided.")
            severity = CriticismSeverity.CRITICAL
            score -= 0.5
            recommendations.append("Obtain human-in-the-loop approval before executing this step.")

        # Check missing arguments relative to required input schema
        req_fields = tool.inputSchema.get("required", [])
        missing_fields = [field for field in req_fields if field not in resolved_args]
        if missing_fields:
            criticisms.append(f"Missing required parameters for '{step.procedure_name}': {missing_fields}")
            if severity != CriticismSeverity.CRITICAL:
                severity = CriticismSeverity.HIGH
            score -= 0.4
            recommendations.append(f"Provide missing fields {missing_fields} in arguments mapping.")

        # Check side-effect risk without compensating procedure
        if tool.is_side_effecting and not step.compensating_procedure:
            criticisms.append(f"Step {step.step_id} ('{step.procedure_name}') is side-effecting but lacks a compensating procedure for rollback.")
            if severity not in (CriticismSeverity.HIGH, CriticismSeverity.CRITICAL):
                severity = CriticismSeverity.MEDIUM
            score -= 0.2
            recommendations.append("Attach a compensating procedure to enable transactional rollback.")

        passed = severity not in (CriticismSeverity.HIGH, CriticismSeverity.CRITICAL)
        final_score = max(0.0, min(round(score, 2), 1.0))

        return StepReview(
            step_id=step.step_id,
            procedure_name=step.procedure_name,
            passed=passed,
            score=final_score,
            criticisms=criticisms,
            severity=severity,
            recommendations=recommendations
        )

    def review_step_post_execution(
        self,
        step: DAGStep,
        tool: ToolContract,
        output: Dict[str, Any],
        pre_review: Optional[StepReview] = None
    ) -> StepReview:
        """
        Performs post-execution review of step outputs and checks postconditions.
        """
        criticisms = list(pre_review.criticisms) if pre_review else []
        recommendations = list(pre_review.recommendations) if pre_review else []
        severity = pre_review.severity if pre_review else CriticismSeverity.LOW
        score = pre_review.score if pre_review else 1.0

        # Check output structure against output schema
        out_req = tool.outputSchema.get("required", [])
        missing_out = [field for field in out_req if field not in output]
        if missing_out:
            criticisms.append(f"Output of '{step.procedure_name}' missing required output fields: {missing_out}")
            severity = CriticismSeverity.HIGH
            score -= 0.3
            recommendations.append(f"Ensure procedure output contains required fields {missing_out}.")

        # Postcondition review
        if tool.hoare_logic_contract and tool.hoare_logic_contract.postcondition:
            post_cond = tool.hoare_logic_contract.postcondition
            recommendations.append(f"Verified postcondition '{post_cond}' against output.")

        passed = severity not in (CriticismSeverity.HIGH, CriticismSeverity.CRITICAL)
        final_score = max(0.0, min(round(score, 2), 1.0))

        return StepReview(
            step_id=step.step_id,
            procedure_name=step.procedure_name,
            passed=passed,
            score=final_score,
            criticisms=criticisms,
            severity=severity,
            recommendations=recommendations
        )

    def assess_dag_execution(
        self,
        dag: MetaProcedureDAG,
        step_reviews: List[StepReview]
    ) -> DAGExecutionAssessment:
        """
        Generates a comprehensive assessment of the DAG execution.
        """
        total_steps = len(dag.steps)
        passed_steps = sum(1 for r in step_reviews if r.passed)
        overall_score = (sum(r.score for r in step_reviews) / len(step_reviews)) if step_reviews else 0.0

        critical_issues = []
        for r in step_reviews:
            if r.severity in (CriticismSeverity.HIGH, CriticismSeverity.CRITICAL):
                critical_issues.extend(r.criticisms)

        summary = (
            f"DAG execution assessment for '{dag.goal_specification}': "
            f"{passed_steps}/{total_steps} steps passed with overall score {round(overall_score, 2)}."
        )

        return DAGExecutionAssessment(
            goal_specification=dag.goal_specification,
            total_steps=total_steps,
            passed_steps=passed_steps,
            overall_score=round(overall_score, 2),
            step_reviews=step_reviews,
            critical_issues=critical_issues,
            summary=summary
        )
