"""Orchestration engine: Planner-Executor (DAG synthesis), ReActAgent (ReAct loop), TransactionManager, and HITLGuard."""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import time
import logging

from procedure_intelligence.taxonomy import ProcedureMetadata, SideEffectLevel, MetaLevel, get_procedure_metadata
from procedure_intelligence.schema import SchemaValidator, SchemaValidationError

logger = logging.getLogger(__name__)


class HITLApprovalRequired(Exception):
    """Raised when a non-reversible operation requires Human-In-The-Loop approval."""
    pass


class HITLGuard:
    """Human-In-The-Loop approval guard for non-reversible operations."""

    def __init__(self, auto_approve_read_only: bool = True) -> None:
        self.auto_approve_read_only = auto_approve_read_only
        self._approved_actions: set = set()

    def grant_approval(self, action_id: str) -> None:
        """Explicitly grant approval for a non-reversible action."""
        self._approved_actions.add(action_id)

    def verify_permission(self, metadata: ProcedureMetadata, action_id: Optional[str] = None) -> bool:
        """Verifies whether execution is allowed or requires HITL approval."""
        if metadata.dimensions.side_effect == SideEffectLevel.NON_REVERSIBLE:
            act_id = action_id or metadata.name
            if act_id not in self._approved_actions:
                raise HITLApprovalRequired(
                    f"Action '{metadata.name}' has side-effect level NON_REVERSIBLE "
                    f"and requires explicit human approval (action_id: {act_id})."
                )
        return True


class TransactionManager:
    """Handles transactional boundaries, execution history, and rollbacks for mutative actions."""

    def __init__(self) -> None:
        self._history: List[Tuple[Callable, Dict[str, Any], Optional[Callable]]] = []

    def execute_transactional(
        self,
        action: Callable,
        kwargs: Dict[str, Any],
        rollback_action: Optional[Callable] = None,
    ) -> Any:
        """Executes action and registers its rollback procedure."""
        meta = get_procedure_metadata(action)
        if meta:
            SchemaValidator.validate_input(meta, kwargs)

        try:
            result = action(**kwargs)
            if meta:
                SchemaValidator.validate_output(meta, result)
            self._history.append((action, kwargs, rollback_action))
            return result
        except Exception as e:
            logger.error(f"Execution failed during transactional step: {e}. Initiating rollback...")
            self.rollback()
            raise e

    def rollback(self) -> None:
        """Rolls back mutative actions in reverse order."""
        while self._history:
            action, kwargs, rollback_action = self._history.pop()
            if rollback_action:
                try:
                    meta = get_procedure_metadata(action)
                    act_name = meta.name if meta else getattr(action, "__name__", "unknown")
                    logger.info(f"Rolling back step '{act_name}' using registered rollback handler.")
                    rollback_action(kwargs)
                except Exception as rollback_err:
                    logger.critical(f"Rollback handler failed: {rollback_err}")


class PlannerExecutor:
    """Meta-procedural planner synthesizing and executing Directed Acyclic Graphs (DAGs) of sub-procedures."""

    def __init__(self, registry: Dict[str, Callable]) -> None:
        self.registry = registry

    def execute_dag(
        self,
        dag_nodes: List[Dict[str, Any]],
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Executes a linear/topological list of DAG procedure nodes.

        node format: {"name": str, "args": dict, "rollback_name": optional[str]}
        """
        context = dict(initial_context or {})
        tx_manager = TransactionManager()

        for node in dag_nodes:
            proc_name = node["name"]
            if proc_name not in self.registry:
                raise ValueError(f"Procedure '{proc_name}' not found in registry.")

            func = self.registry[proc_name]
            args = node.get("args", {})

            # Resolve dynamic arguments from context variables (e.g. "$step1.output")
            resolved_args = {}
            for k, v in args.items():
                if isinstance(v, str) and v.startswith("$"):
                    key = v[1:]
                    resolved_args[k] = context.get(key, v)
                else:
                    resolved_args[k] = v

            rollback_func = None
            if "rollback_name" in node and node["rollback_name"] in self.registry:
                rollback_func = self.registry[node["rollback_name"]]

            result = tx_manager.execute_transactional(func, resolved_args, rollback_action=rollback_func)
            context[proc_name] = result
            context["_last_result"] = result

        return context


class ReActAgent:
    """Iterative ReAct loop runner with MAX_ITERATIONS limits, execution timeouts, and context trimming."""

    def __init__(
        self,
        registry: Dict[str, Callable],
        max_iterations: int = 10,
        timeout_seconds: float = 30.0,
        hitl_guard: Optional[HITLGuard] = None,
    ) -> None:
        self.registry = registry
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds
        self.hitl_guard = hitl_guard or HITLGuard()

    def run_loop(
        self,
        task: str,
        step_generator: Callable[[str, List[Dict[str, Any]]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Runs Observation -> Thought -> Action -> Reflection loop until task completion or limit reached.

        step_generator function simulates LLM reasoning given task and observation history.
        Returns final outcome dict.
        """
        history: List[Dict[str, Any]] = []
        start_time = time.time()

        for iteration in range(1, self.max_iterations + 1):
            if time.time() - start_time > self.timeout_seconds:
                raise TimeoutError(f"ReAct loop exceeded timeout of {self.timeout_seconds} seconds.")

            # Trim history if token context grows too large (keep last 5 iterations)
            trimmed_history = history[-5:] if len(history) > 5 else history

            # Get next action from step_generator (Thought + Action)
            step_res = step_generator(task, trimmed_history)
            thought = step_res.get("thought", "")
            action_name = step_res.get("action")
            action_args = step_res.get("action_args", {})
            is_done = step_res.get("is_done", False)

            if is_done or not action_name:
                return {
                    "status": "COMPLETED",
                    "final_output": step_res.get("final_output"),
                    "iterations": iteration,
                    "history": history,
                }

            if action_name not in self.registry:
                observation = f"Error: Action '{action_name}' is not registered."
            else:
                func = self.registry[action_name]
                meta = get_procedure_metadata(func)

                try:
                    if meta:
                        self.hitl_guard.verify_permission(meta)
                        SchemaValidator.validate_input(meta, action_args)

                    result = func(**action_args)

                    if meta:
                        SchemaValidator.validate_output(meta, result)

                    observation = result
                except Exception as e:
                    observation = f"Execution Error: {str(e)}"

            history.append({
                "iteration": iteration,
                "thought": thought,
                "action": action_name,
                "action_args": action_args,
                "observation": observation,
            })

        return {
            "status": "MAX_ITERATIONS_REACHED",
            "iterations": self.max_iterations,
            "history": history,
        }
