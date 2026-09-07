"""Quantifiable health metrics for procedures, including Procedure Intelligence Viability Score (PIVS)."""

from dataclasses import dataclass
from typing import Dict, Optional
import math

from procedure_intelligence.taxonomy import ProcedureMetadata, SideEffectLevel


@dataclass
class PIVSScore:
    pivs: float
    schema_clarity: float
    complexity_penalty: float
    historical_reliability: float


class PIVSCalculator:
    """Computes Procedure Intelligence Viability Score (PIVS).

    PIVS = (SchemaClarity * HistoricalReliability) / (1 + ComplexityPenalty)
    Scaled to [0.0, 100.0].
    """

    @staticmethod
    def calculate_schema_clarity(metadata: ProcedureMetadata) -> float:
        """Evaluates clarity based on schema specification, descriptions, and preconditions."""
        score = 0.5  # Base score
        if metadata.description and len(metadata.description) > 10:
            score += 0.2
        if metadata.input_schema and "properties" in metadata.input_schema:
            props = metadata.input_schema["properties"]
            if props:
                score += 0.15
        if metadata.preconditions and metadata.postconditions:
            score += 0.15
        return min(score, 1.0)

    @staticmethod
    def calculate_complexity_penalty(metadata: ProcedureMetadata) -> float:
        """Calculates complexity penalty based on arguments and side effects."""
        num_args = 0
        if metadata.input_schema and "properties" in metadata.input_schema:
            num_args = len(metadata.input_schema["properties"])

        side_effect_weight = 0.1
        if metadata.dimensions.side_effect == SideEffectLevel.MUTATIVE_REVERSIBLE:
            side_effect_weight = 0.3
        elif metadata.dimensions.side_effect == SideEffectLevel.NON_REVERSIBLE:
            side_effect_weight = 0.6

        penalty = (num_args * 0.05) + side_effect_weight
        return penalty

    @classmethod
    def compute_pivs(
        cls,
        metadata: ProcedureMetadata,
        total_invocations: int = 10,
        successful_invocations: int = 10,
    ) -> PIVSScore:
        """Computes PIVS score given procedure metadata and historical telemetry."""
        clarity = cls.calculate_schema_clarity(metadata)
        complexity = cls.calculate_complexity_penalty(metadata)

        reliability = (
            successful_invocations / total_invocations
            if total_invocations > 0
            else 1.0
        )

        raw_score = (clarity * reliability) / (1.0 + complexity)
        pivs = round(raw_score * 100.0, 2)

        return PIVSScore(
            pivs=pivs,
            schema_clarity=round(clarity, 2),
            complexity_penalty=round(complexity, 2),
            historical_reliability=round(reliability, 2),
        )
