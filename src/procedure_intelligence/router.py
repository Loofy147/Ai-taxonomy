"""Tool router pattern for intent classification and schema context pruning (I_total reduction)."""

from typing import Any, Callable, Dict, List, Optional
import json

from procedure_intelligence.taxonomy import ProcedureMetadata, get_procedure_metadata


class ToolRouter:
    """Classifies user intent and injects only relevant tool schemas into context window."""

    def __init__(self) -> None:
        self._registry: Dict[str, Callable] = {}

    def register(self, func: Callable) -> None:
        """Registers a procedure callable."""
        meta = get_procedure_metadata(func)
        name = meta.name if meta else func.__name__
        self._registry[name] = func

    def list_all_procedures(self) -> List[ProcedureMetadata]:
        """Returns metadata for all registered procedures."""
        metas = []
        for func in self._registry.values():
            meta = get_procedure_metadata(func)
            if meta:
                metas.append(meta)
        return metas

    def route_intent(self, intent_query: str, max_tools: int = 3) -> List[ProcedureMetadata]:
        """Filters registered tools based on intent keywords to avoid context token bloat."""
        query_words = set(intent_query.lower().split())
        scored_tools = []

        for name, func in self._registry.items():
            meta = get_procedure_metadata(func)
            if not meta:
                continue

            # Calculate keyword overlap score
            text = f"{meta.name} {meta.description} {' '.join(meta.tags)}".lower()
            score = sum(1 for word in query_words if word in text)

            scored_tools.append((score, meta))

        # Sort descending by relevance score
        scored_tools.sort(key=lambda x: x[0], reverse=True)

        selected = [meta for score, meta in scored_tools if score > 0][:max_tools]
        # If no keywords matched, fallback to top max_tools
        if not selected and scored_tools:
            selected = [meta for _, meta in scored_tools[:max_tools]]

        return selected

    def get_pruned_context_schemas(self, intent_query: str, max_tools: int = 3) -> List[Dict[str, Any]]:
        """Returns JSON schemas for relevant tools formatted for LLM context injection."""
        relevant_metas = self.route_intent(intent_query, max_tools=max_tools)
        schemas = []
        for meta in relevant_metas:
            schemas.append({
                "name": meta.name,
                "description": meta.description,
                "parameters": meta.input_schema,
                "returns": meta.output_schema,
            })
        return schemas
