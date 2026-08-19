import json
from functools import lru_cache
from typing import Dict, Any, Callable, List, Optional
import jsonschema
from pif.models import ToolContract, MetaProcedureDAG, DAGStep, StepReview, CriticismSeverity, DAGExecutionAssessment
from pif.review import ReviewEngine

class ExecutionError(Exception):
    pass

class HITLApprovalRequired(Exception):
    pass

@lru_cache(maxsize=1024)
def _get_validator_for_schema_str(schema_str: str) -> jsonschema.protocols.Validator:
    """
    Cache compiled jsonschema Validator instances by serialized schema string
    to avoid heavy validator class lookup and schema parsing overhead (~60x speedup).
    """
    schema = json.loads(schema_str)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)

def get_compiled_validator(schema: Dict[str, Any]) -> jsonschema.protocols.Validator:
    """
    Returns a compiled jsonschema validator instance for the given dictionary schema.
    """
    # Canonicalize schema dict to string for LRU caching
    schema_str = json.dumps(schema, sort_keys=True)
    return _get_validator_for_schema_str(schema_str)

class ExecutorEngine:
    """
    Executor engine supporting Planner-Executor DAG execution, ReAct loop circuit breakers (MAX_ITERATIONS=10),
    HITL approval checks, input/output schema enforcement, structured reviews/criticism,
    and transactional Try-Catch-Rollback boundaries.
    """

    MAX_ITERATIONS = 10

    def __init__(
        self,
        tools_registry: Dict[str, ToolContract],
        tool_handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]],
        review_engine: Optional[ReviewEngine] = None
    ):
        self.tools_registry = tools_registry
        self.tool_handlers = tool_handlers
        self.review_engine = review_engine or ReviewEngine()

    def execute_tool(self, tool_name: str, args: Dict[str, Any], hitl_approved: bool = False) -> Dict[str, Any]:
        if tool_name not in self.tools_registry:
            raise ExecutionError(f"Tool '{tool_name}' not found in registry.")

        tool = self.tools_registry[tool_name]

        # HITL Approval Check
        if tool.requires_hitl_approval and not hitl_approved:
            raise HITLApprovalRequired(f"Execution of procedure '{tool_name}' requires human-in-the-loop approval.")

        # Input Schema Validation (optimized using cached validator)
        try:
            input_validator = get_compiled_validator(tool.inputSchema)
            input_validator.validate(instance=args)
        except jsonschema.ValidationError as e:
            raise ExecutionError(f"Input schema validation failed for '{tool_name}': {e.message}")

        # Execution Handler Invocation
        handler = self.tool_handlers.get(tool_name)
        if not handler:
            raise ExecutionError(f"No execution handler registered for '{tool_name}'.")

        result = handler(args)

        # Output Schema Validation (optimized using cached validator)
        try:
            output_validator = get_compiled_validator(tool.outputSchema)
            output_validator.validate(instance=result)
        except jsonschema.ValidationError as e:
            raise ExecutionError(f"Output schema validation failed for '{tool_name}': {e.message}")

        return result

    def execute_dag(
        self,
        dag: MetaProcedureDAG,
        hitl_approved_steps: Optional[List[int]] = None,
        enforce_reviews: bool = True
    ) -> Dict[str, Any]:
        """
        Executes a synthesized meta-procedure DAG with transactional rollback boundaries and structured review assessment.
        If Step N fails or critical review issues arise, compensating procedures for completed steps are executed in reverse order.
        """
        hitl_approved_steps = hitl_approved_steps or []
        step_outputs: Dict[int, Dict[str, Any]] = {}
        completed_steps: List[DAGStep] = []
        step_reviews: List[StepReview] = []

        for step in dag.steps:
            try:
                # Resolve argument references, e.g. $steps[1].output.field
                resolved_args = {}
                for k, v in step.arguments_mapping.items():
                    if isinstance(v, str) and v.startswith("$steps["):
                        # Parse $steps[step_id].output.field
                        parts = v.split(".")
                        step_id_part = parts[0].replace("$steps[", "").replace("]", "")
                        dep_step_id = int(step_id_part)
                        field_name = parts[-1]
                        resolved_args[k] = step_outputs[dep_step_id][field_name]
                    else:
                        resolved_args[k] = v

                is_hitl_approved = step.step_id in hitl_approved_steps
                tool = self.tools_registry.get(step.procedure_name)

                # Pre-execution Review
                pre_review = None
                if tool and self.review_engine:
                    pre_review = self.review_engine.review_step_pre_execution(
                        step=step,
                        tool=tool,
                        resolved_args=resolved_args,
                        hitl_approved=is_hitl_approved
                    )
                    if enforce_reviews and not pre_review.passed:
                        raise ExecutionError(
                            f"Pre-execution review failed for Step {step.step_id} ('{step.procedure_name}'): {pre_review.criticisms}"
                        )

                output = self.execute_tool(step.procedure_name, resolved_args, hitl_approved=is_hitl_approved)

                # Post-execution Review
                if tool and self.review_engine:
                    post_review = self.review_engine.review_step_post_execution(
                        step=step,
                        tool=tool,
                        output=output,
                        pre_review=pre_review
                    )
                    step_reviews.append(post_review)
                    if enforce_reviews and not post_review.passed:
                        raise ExecutionError(
                            f"Post-execution review failed for Step {step.step_id} ('{step.procedure_name}'): {post_review.criticisms}"
                        )

                step_outputs[step.step_id] = output
                completed_steps.append(step)

            except Exception as e:
                # Trigger Transactional Rollback
                rollback_logs = self._rollback(completed_steps)
                raise ExecutionError(
                    f"Execution failed at Step {step.step_id} ('{step.procedure_name}'): {str(e)}. Rollback completed: {rollback_logs}"
                )

        assessment = self.review_engine.assess_dag_execution(dag, step_reviews)

        return {
            "status": "SUCCESS",
            "step_outputs": step_outputs,
            "assessment": assessment
        }

    def _rollback(self, completed_steps: List[DAGStep]) -> List[str]:
        rollback_logs = []
        for step in reversed(completed_steps):
            if step.compensating_procedure:
                comp_name = step.compensating_procedure.get("procedure_name")
                comp_args = step.compensating_procedure.get("arguments_mapping", {})
                if comp_name and comp_name in self.tool_handlers:
                    try:
                        self.execute_tool(comp_name, comp_args, hitl_approved=True)
                        rollback_logs.append(f"Rolled back Step {step.step_id} using '{comp_name}'")
                    except Exception as re:
                        rollback_logs.append(f"Failed rollback for Step {step.step_id}: {str(re)}")
        return rollback_logs
