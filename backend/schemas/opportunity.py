from typing import List, Optional
from pydantic import BaseModel, Field


class OpportunityScore(BaseModel):
    market_demand: int = Field(..., ge=1, le=10, description="Urgency and customer willingness to pay (1-10)")
    competitive_pressure: int = Field(..., ge=1, le=10, description="Room to compete vs incumbents (1-10, higher = less crowded / easier to compete)")
    execution_feasibility: int = Field(..., ge=1, le=10, description="Feasibility of building MVP within 4 weeks (1-10)")
    market_timing: int = Field(..., ge=1, le=10, description="Strength of current 'Why Now' catalysts (1-10)")
    ai_advantage: int = Field(..., ge=1, le=10, description="Degree of technical/AI leverage (1-10)")
    overall_score: int = Field(..., ge=5, le=50, description="Sum of 5 scoring dimensions (5-50)")
    confidence_label: str = Field(..., description="High Potential | Promising | Experimental | Low Confidence")
    rationale: Optional[str] = Field(None, description="Analytical evidence-informed scoring rationale")


def calculate_confidence_label(overall_score: int) -> str:
    """Classify overall opportunity score (5-50) into standard confidence label."""
    if overall_score >= 40:
        return "High Potential"
    elif overall_score >= 32:
        return "Promising"
    elif overall_score >= 22:
        return "Experimental"
    return "Low Confidence"


class Opportunity(BaseModel):
    id: Optional[str] = Field(None, description="Optional opportunity identifier")
    title: str = Field(..., description="Opportunity hypothesis title")
    problem: str = Field(..., description="Core customer problem being addressed")
    customer: str = Field(..., description="Specific target customer persona")
    solution: str = Field(..., description="Proposed solution hypothesis")
    why_now: str = Field(..., description="Why this opportunity is viable today")
    competitors: List[str] = Field(default_factory=list, description="Existing alternative solutions or competitors")
    mvp_features: List[str] = Field(default_factory=list, description="Initial MVP feature scope")
    risks: List[str] = Field(default_factory=list, description="Key execution and market risks")
    evidence: List[str] = Field(default_factory=list, description="Evidence references supporting the hypothesis")
    score: Optional[OpportunityScore] = Field(None, description="Evidence-informed validation scorecard")


class OpportunityOutput(BaseModel):
    opportunities: List[Opportunity] = Field(default_factory=list, description="List of generated opportunity hypotheses")
