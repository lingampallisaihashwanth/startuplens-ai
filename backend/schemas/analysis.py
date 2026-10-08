from typing import List, Optional
from pydantic import BaseModel, Field


class MarketAnalysisOutput(BaseModel):
    market_signals: List[str] = Field(default_factory=list, description="Validated market signals and indicators")
    customer_segments: List[str] = Field(default_factory=list, description="Target customer segments and audiences")
    competitors: List[str] = Field(default_factory=list, description="Existing players and competitive landscape")
    market_gaps: List[str] = Field(default_factory=list, description="Unaddressed customer needs and white spaces")
    why_now: List[str] = Field(default_factory=list, description="Tailwinds, regulatory, or technological why-now triggers")
    trends: Optional[List[str]] = Field(default_factory=list, description="Synthesized trends")
    problems: Optional[List[str]] = Field(default_factory=list, description="Recurring problems")
