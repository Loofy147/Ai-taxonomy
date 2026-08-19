from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class CriticismSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class HoareTriple(BaseModel):
    precondition: str = Field(..., description="Precondition logic formula {P}")
    postcondition: str = Field(..., description="Postcondition logic formula {Q}")

class ToolContract(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$", min_length=1, max_length=128)
    description: str
    category: str = Field(default="atomic")
    is_side_effecting: bool = True
    requires_hitl_approval: bool = False
    hoare_logic_contract: Optional[HoareTriple] = None
    inputSchema: Dict[str, Any]
    outputSchema: Dict[str, Any]

class DAGStep(BaseModel):
    step_id: int = Field(..., ge=1)
    procedure_name: str
    arguments_mapping: Dict[str, Any]
    dependencies: List[int] = Field(default_factory=list)
    compensating_procedure: Optional[Dict[str, Any]] = None

class VerificationProof(BaseModel):
    weakest_precondition: str
    certified_safe: bool

class MetaProcedureDAG(BaseModel):
    goal_specification: str
    verification_proof: Optional[VerificationProof] = None
    steps: List[DAGStep]

class StepReview(BaseModel):
    step_id: int = Field(..., ge=1)
    procedure_name: str
    passed: bool
    score: float = Field(..., ge=0.0, le=1.0, description="Quality/safety score from 0.0 to 1.0")
    criticisms: List[str] = Field(default_factory=list)
    severity: CriticismSeverity = Field(default=CriticismSeverity.LOW)
    recommendations: List[str] = Field(default_factory=list)

class DAGExecutionAssessment(BaseModel):
    goal_specification: str
    total_steps: int
    passed_steps: int
    overall_score: float = Field(..., ge=0.0, le=1.0)
    step_reviews: List[StepReview] = Field(default_factory=list)
    critical_issues: List[str] = Field(default_factory=list)
    summary: str
