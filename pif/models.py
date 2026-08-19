from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

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
