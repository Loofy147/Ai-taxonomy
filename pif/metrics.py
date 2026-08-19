from typing import Dict, Any
from pif.models import ToolContract

class PIVSEvaluator:
    """
    Computes Procedure Intelligence Viability Score (PIVS) based on:
    PIVS = w1 * Clarity + w2 * SchemaRigor + w3 * SuccessRate - w4 * RiskFactor
    """

    def __init__(
        self,
        w_clarity: float = 0.25,
        w_schema: float = 0.35,
        w_success: float = 0.30,
        w_risk: float = 0.10
    ):
        self.w_clarity = w_clarity
        self.w_schema = w_schema
        self.w_success = w_success
        self.w_risk = w_risk

    def evaluate_tool(self, tool: ToolContract, historical_success_rate: float = 1.0) -> Dict[str, Any]:
        """
        Evaluates PIVS score [0.0, 1.0] for a given ToolContract.
        """
        # 1. Description Clarity Score
        desc_words = tool.description.strip().split()
        c_score = min(len(desc_words) / 10.0, 1.0) # Normalized clarity up to 10 words

        # 2. Schema Rigor Score
        r_score = 0.0
        in_props = tool.inputSchema.get("properties", {})
        in_req = tool.inputSchema.get("required", [])
        out_props = tool.outputSchema.get("properties", {})

        if in_props:
            r_score += 0.4
        if in_req:
            r_score += 0.3
        if out_props:
            r_score += 0.3

        # 3. Success Rate Score
        s_rate = max(0.0, min(historical_success_rate, 1.0))

        # 4. Risk Factor
        risk = 0.0
        if tool.is_side_effecting:
            risk += 0.5
        if tool.requires_hitl_approval:
            # Having HITL mitigates raw risk
            risk -= 0.2

        pivs = (
            self.w_clarity * c_score +
            self.w_schema * r_score +
            self.w_success * s_rate -
            self.w_risk * risk
        )

        pivs_normalized = max(0.0, min(pivs, 1.0))

        return {
            "pivs_score": round(pivs_normalized, 4),
            "clarity_score": round(c_score, 2),
            "schema_rigor_score": round(r_score, 2),
            "success_rate": round(s_rate, 2),
            "risk_factor": round(risk, 2)
        }
