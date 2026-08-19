from typing import List, Dict, Any, Set
from pif.models import ToolContract

class ToolRouter:
    """
    Fast O(1) Tool Router and Context Pruning Engine.
    Filters candidate tools based on user intent keywords and categories to prevent quadratic context window bloat I_total.
    """

    def __init__(self, registry: Dict[str, ToolContract]):
        self.registry = registry

    def route_and_filter(self, user_intent: str, top_k: int = 5) -> List[ToolContract]:
        """
        Evaluates user intent and returns top_k candidate ToolContracts.
        Prunes unnecessary tool schemas from the system context.
        """
        intent_tokens = set(user_intent.lower().split())
        scored_tools = []

        for tool in self.registry.values():
            score = 0
            # Name match
            tool_name_tokens = set(tool.name.lower().replace("_", " ").split())
            score += len(intent_tokens.intersection(tool_name_tokens)) * 3

            # Description match
            desc_tokens = set(tool.description.lower().split())
            score += len(intent_tokens.intersection(desc_tokens)) * 1

            # Category bonus
            if tool.category.lower() in intent_tokens:
                score += 2

            scored_tools.append((score, tool))

        # Sort descending by score
        scored_tools.sort(key=lambda x: x[0], reverse=True)

        # If score is 0, still return up to top_k to avoid empty set
        return [tool for score, tool in scored_tools[:top_k]]

    @staticmethod
    def calculate_token_savings(total_tools_count: int, filtered_tools_count: int, avg_schema_tokens: int = 250) -> Dict[str, Any]:
        """
        Calculates token usage reduction achieved by router pruning.
        """
        raw_tokens = total_tools_count * avg_schema_tokens
        pruned_tokens = filtered_tools_count * avg_schema_tokens
        saved_tokens = raw_tokens - pruned_tokens
        reduction_percentage = (saved_tokens / raw_tokens * 100) if raw_tokens > 0 else 0.0

        return {
            "unfiltered_schema_tokens": raw_tokens,
            "pruned_schema_tokens": pruned_tokens,
            "tokens_saved": saved_tokens,
            "reduction_percentage": round(reduction_percentage, 2)
        }
