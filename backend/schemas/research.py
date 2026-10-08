from typing import List, Optional
from pydantic import BaseModel, Field


class ResearchSource(BaseModel):
    title: str = Field(..., description="Title of the source")
    url: str = Field(..., description="Source URL")
    published_at: Optional[str] = Field(None, description="Publication date when available")
    snippet: Optional[str] = Field(None, description="Extracted snippet or summary")
    source_type: Optional[str] = Field("web", description="Type of source: 'web', 'document', 'news', 'academic', 'historical'")
    retrieved_at: Optional[str] = Field(None, description="ISO timestamp when the source was retrieved")
    freshness_label: Optional[str] = Field(None, description="Human-readable relative age or freshness status")
    is_historical: Optional[bool] = Field(False, description="True if source provides historical context rather than current evidence")
    page_or_section: Optional[str] = Field(None, description="Page or section citation e.g. 'p. 12', 'Section 2'")
    authority: Optional[str] = Field(None, description="Source authority label e.g. 'Primary', 'News', 'Document', 'Market Research'")


class ResearchOutput(BaseModel):
    topic: str = Field(..., description="Topic researched")
    trends: List[str] = Field(default_factory=list, description="Emerging market and technology trends")
    startups: List[str] = Field(default_factory=list, description="Relevant startups and companies in the space")
    problems: List[str] = Field(default_factory=list, description="Identified customer pain points")
    market_signals: List[str] = Field(default_factory=list, description="Signals such as funding, demand, shifts")
    sources: List[ResearchSource] = Field(default_factory=list, description="Verified references")
    retrieved_at: Optional[str] = Field(None, description="ISO timestamp when research was completed")
