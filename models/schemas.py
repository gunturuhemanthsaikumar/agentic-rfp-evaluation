from typing import List
from pydantic import BaseModel, Field

class CriterionResult(BaseModel):
    criterion_id: int
    score: float
    max_score: float
    justification: str = ""
    evidence: str = ""
    evidence_page: int = 0

class LLMScorecard(BaseModel):
    supplier_name: str
    criteria: List[CriterionResult]
    risks: List[str] = Field(default_factory=list)
    overall_summary: str = ""

class SupplierMetadata(BaseModel):
    supplier_name: str
    submission_date: str
    experience_rating: float = Field(ge=0, le=10)
