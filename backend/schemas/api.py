from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.schemas.research import ResearchOutput, ResearchSource
from backend.schemas.analysis import MarketAnalysisOutput
from backend.schemas.opportunity import Opportunity, OpportunityScore


class AnalyzeRequest(BaseModel):
    topic: str = Field(..., min_length=2, description="Topic to research (minimum 2 characters)")
    document_ids: Optional[List[str]] = Field(default_factory=list, description="IDs of uploaded research documents to include")
    model: Optional[str] = Field(
        None,
        description="Model ID to use: 'auto', 'gemini-balanced', 'groq-fast', 'groq-reasoning', 'mistral-small'. Defaults to DEFAULT_MODEL setting.",
    )


class AnalyzeResponse(BaseModel):
    id: str = Field(..., description="Unique research session identifier")
    session_id: str = Field(..., description="Unique session ID (alias)")
    topic: str = Field(..., description="Researched topic")
    created_at: Optional[str] = Field(None, description="ISO timestamp of session creation")
    updated_at: Optional[str] = Field(None, description="ISO timestamp of session last update")
    retrieved_at: Optional[str] = Field(None, description="ISO timestamp when fresh web research was retrieved")
    model_used: Optional[str] = Field(None, description="Model or model ID used for the research run")
    provider_used: Optional[str] = Field(None, description="Provider that served the response")
    fallback_used: Optional[bool] = Field(False, description="Whether a fallback provider was used")
    fallback_reason: Optional[str] = Field(None, description="Reason a fallback provider was used, if any")
    research_disclaimer: Optional[str] = Field(None, description="Freshness and web retrieval disclaimer")
    research: ResearchOutput = Field(..., description="Research findings and signals")
    analysis: MarketAnalysisOutput = Field(..., description="Synthesized market analysis")
    opportunities: List[Opportunity] = Field(..., description="Hypothesized startup opportunities")
    sources: List[ResearchSource] = Field(..., description="Collected source references")


class SessionSummary(BaseModel):
    id: str = Field(..., description="Unique research session identifier")
    session_id: str = Field(..., description="Unique session ID (alias)")
    topic: str = Field(..., description="Researched topic")
    created_at: str = Field(..., description="ISO timestamp")
    updated_at: str = Field(..., description="ISO timestamp")
    model_used: Optional[str] = Field(None, description="Model used for research")
    sources_count: int = Field(0, description="Count of sources associated with session")
    opportunities_count: int = Field(0, description="Count of opportunities generated")


class DeleteSessionResponse(BaseModel):
    message: str = "Session deleted successfully"
    session_id: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    created_at: str
    section_count: int


class DocumentDetailResponse(DocumentResponse):
    content_text: str
    sections: List[Dict[str, str]]


class ModelProfile(BaseModel):
    """Legacy Gemini-only profile schema kept for backward compat with existing tests."""
    id: str
    name: str
    description: str
    model_name: str
    is_default: bool = False


# New multi-provider model schemas
class MultiModelEntry(BaseModel):
    id: str
    display_name: str
    provider: str
    model: Optional[str] = None
    speed: Optional[str] = None
    reasoning_level: Optional[str] = None


class MultiModelListResponse(BaseModel):
    default: str
    models: List[MultiModelEntry]


class ModelListResponse(BaseModel):
    """Legacy response schema for backward compat."""
    models: List[ModelProfile]
    default_model: str


class SaveIdeaRequest(BaseModel):
    session_id: Optional[str] = None
    topic: str
    title: str
    problem: str
    customer: str
    solution: str
    why_now: str
    competitors: List[str] = Field(default_factory=list)
    mvp_features: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    score: Optional[OpportunityScore] = None


class SavedIdeaResponse(BaseModel):
    id: str
    session_id: Optional[str] = None
    topic: str
    title: str
    problem: str
    customer: str
    solution: str
    why_now: str
    competitors: List[str] = Field(default_factory=list)
    mvp_features: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    score: Optional[OpportunityScore] = None
    created_at: str


class CreateTrackerRequest(BaseModel):
    topic: str
    session_id: Optional[str] = None


class ResearchTrackerResponse(BaseModel):
    id: str
    topic: str
    session_id: Optional[str] = None
    status: str
    last_updated: str
    next_update: str
    created_at: str


class MarketSignalResponse(BaseModel):
    id: str
    tracker_id: Optional[str] = None
    topic: str
    signal_type: str
    title: str
    change_summary: str
    evidence: Optional[str] = None
    detected_at: str


class WeeklyReportResponse(BaseModel):
    id: str
    week_start: str
    week_end: str
    title: str
    summary: str
    top_opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    market_signals: List[Dict[str, Any]] = Field(default_factory=list)
    new_competitors: List[str] = Field(default_factory=list)
    recommended_next_step: Optional[str] = None
    created_at: str


class ExportRequest(BaseModel):
    format: str = Field(..., description="pdf | markdown | json")
    session_id: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "StartupLens AI API"
    message: Optional[str] = "StartupLens AI API is running"
