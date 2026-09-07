"""Formal system state verification engine utilizing Hoare-logic triples {P} C {Q} and Weakest Preconditions wp."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
import ast


class VerificationError(Exception):
    """Raised when formal safety verification checks fail."""
    pass


@dataclass
class Predicate:
    """Represents a formal condition/predicate over system state."""
    expression: str  # e.g., "balance >= amount" or "file_exists == True"

    def evaluate(self, state: Dict[str, Any]) -> bool:
        """Evaluates predicate expression against given state environment safely."""
        try:
            return bool(eval(self.expression, {"__builtins__": {}}, dict(state)))
        except Exception as e:
            raise VerificationError(f"Error evaluating predicate '{self.expression}': {e}") from e


@dataclass
class HoareTriple:
    """Formal specification triple {P} C {Q}."""
    precondition: Predicate  # P
    command: str              # C (description or code identifier)
    postcondition: Predicate # Q

    def verify(self, initial_state: Dict[str, Any], final_state: Dict[str, Any]) -> bool:
        """Verifies if P holds on initial state AND Q holds on final state."""
        if not self.precondition.evaluate(initial_state):
            raise VerificationError(f"Precondition '{self.precondition.expression}' failed on initial state {initial_state}.")
        if not self.postcondition.evaluate(final_state):
            raise VerificationError(f"Postcondition '{self.postcondition.expression}' failed on final state {final_state}.")
        return True


class WeakestPrecondition:
    """Weakest Precondition solver wp(V := E, Q)."""

    @staticmethod
    def substitute(postcondition_expr: str, var_name: str, expr: str) -> str:
        """Computes wp(var_name := expr, Q) by substituting var_name with expr in Q."""
        # Simple AST-based substitution for accuracy
        class SubstitutionTransformer(ast.NodeTransformer):
            def visit_Name(self, node: ast.Name) -> ast.AST:
                if node.id == var_name:
                    parsed_expr = ast.parse(expr, mode='eval').body
                    return parsed_expr
                return node

        try:
            tree = ast.parse(postcondition_expr, mode='eval')
            transformed = SubstitutionTransformer().visit(tree)
            ast.fix_missing_locations(transformed)
            return ast.unparse(transformed)
        except Exception:
            # Fallback string replacement if AST parsing fails
            return postcondition_expr.replace(var_name, f"({expr})")

    @classmethod
    def calculate_wp(cls, assignment_var: str, assignment_expr: str, postcondition: Predicate) -> Predicate:
        """Calculates weakest precondition predicate wp(V := E, Q)."""
        wp_expr = cls.substitute(postcondition.expression, assignment_var, assignment_expr)
        return Predicate(expression=wp_expr)
