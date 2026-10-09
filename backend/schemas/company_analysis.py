from typing import List, Optional, Union
from pydantic import BaseModel, Field


class CompanyAnalysisOutput(BaseModel):
    """
    Comprehensive company analysis covering founding, growth,
    milestones, strategic turning points, and decline/success factors.
    """
    company_name: str = Field(..., description="Company name")
    overview: str = Field(..., description="1. Company overview and core mission")
    founding_story: str = Field(..., description="2. Founding story and origin background")
    original_problem: str = Field(..., description="3. Original problem the company set out to solve")
    business_model: str = Field(..., description="4. Business model, pricing, and monetization mechanisms")
    target_customers: Union[List[str], str] = Field(..., description="5. Primary target customer profiles and segments")
    early_growth: str = Field(..., description="6. Early growth trajectory and initial traction metrics")
    growth_strategy: str = Field(..., description="7. Core growth strategy and acquisition channels")
    funding_and_expansion: str = Field(..., description="8. Funding history, capital raised, and geographical expansion")
    major_milestones: List[str] = Field(default_factory=list, description="9. Major chronological milestones")
    growth_drivers: List[str] = Field(default_factory=list, description="10. Primary growth drivers and catalysts")
    turning_points: List[str] = Field(default_factory=list, description="11. Critical inflection points in trajectory")
    warning_signs: List[str] = Field(default_factory=list, description="12. Early warning signs or governance/financial red flags")
    competition: Union[List[str], str] = Field(..., description="13. Competitive dynamics and rivals")
    market_changes: Union[List[str], str] = Field(..., description="14. Broader macroeconomic, industry, and regulatory shifts")
    strategic_mistakes: List[str] = Field(default_factory=list, description="15. Strategic mistakes and miscalculations")
    financial_problems: List[str] = Field(default_factory=list, description="16. Financial, burn rate, or unit economics problems")
    reasons_for_decline_or_failure: List[str] = Field(default_factory=list, description="17. Concrete reasons for decline or failure (or 'N/A - Thriving' if operating successfully)")
    current_status: str = Field(..., description="18. Current status and latest situation based on evidence")
    lessons_for_founders: List[str] = Field(default_factory=list, description="19. Actionable lessons and takeaways for founders")

    # Clear distinction of evidence credibility
    facts: List[str] = Field(
        default_factory=list,
        description="FACT: Directly verified claims grounded in web sources (funding, verified dates, reported revenue, filings).",
    )
    inferences: List[str] = Field(
        default_factory=list,
        description="INFERENCE: Logical deductions drawn from reported operational and market evidence.",
    )
    hypotheses: List[str] = Field(
        default_factory=list,
        description="HYPOTHESIS: Analytical interpretations or strategic hypotheses regarding decisions and outcomes.",
    )
