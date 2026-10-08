import logging
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

# Ensure repository root and backend directory are always present in sys.path
_current_dir = Path(__file__).resolve().parent
_repo_root = _current_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from backend.config import settings
from backend.schemas.api import (
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse,
    ErrorResponse,
    ErrorDetail,
    SessionSummary,
    DeleteSessionResponse,
    DocumentResponse,
    DocumentDetailResponse,
    ModelProfile,
    ModelListResponse,
    MultiModelEntry,
    MultiModelListResponse,
    SaveIdeaRequest,
    SavedIdeaResponse,
    CreateTrackerRequest,
    ResearchTrackerResponse,
    MarketSignalResponse,
    WeeklyReportResponse,
    ExportRequest,
)
from backend.schemas.opportunity import OpportunityScore, calculate_confidence_label
# Keep legacy gemini_service import for backward-compat with existing tests
from backend.services.gemini_service import (
    GeminiServiceError,
    GeminiRateLimitError,
    GeminiQuotaExhaustedError,
    GeminiServiceUnavailableError,
    GeminiAuthError,
    gemini_service,
)
from backend.llm import llm_router
from backend.llm.base import (
    LLMError,
    LLMRateLimitError,
    LLMQuotaExhaustedError,
    LLMServiceUnavailableError,
    LLMAuthError,
    LLMInvalidRequestError,
)
from backend.llm.registry import model_registry
from backend.services.tavily_service import TavilyServiceError
from backend.services.document_service import document_service, DocumentValidationError, DocumentParseError
from backend.services.model_router import model_router as legacy_model_router
from backend.services.export_service import export_service
from backend.agents.research_agent import research_agent
from backend.agents.opportunity_agent import opportunity_agent
from backend.database.db import db

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("startuplens")

# Log configuration status safely without printing secret keys
key_status = settings.validate_keys()
logger.info(
    f"Configuration initialized — "
    f"Gemini: {key_status['gemini_configured']}, "
    f"Groq: {key_status['groq_configured']}, "
    f"Mistral: {key_status['mistral_configured']}, "
    f"Tavily: {key_status['tavily_configured']}"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and clean up on shutdown."""
    try:
        db.init_db()
        logger.info("SQLite database tables verified on startup.")
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {e}", exc_info=True)
    yield


app = FastAPI(
    title="StartupLens AI API",
    description="Multi-Agent Startup Opportunity Intelligence System powered by Google Gemini and Tavily",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS configuration for production and development
cors_origins = settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format validation errors according to StartupLens API specification."""
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "Invalid request parameter.")
    loc = first_error.get("loc", [])

    if "topic" in loc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "INVALID_TOPIC",
                    "message": "Topic must contain at least 2 characters.",
                }
            },
        )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": msg,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPExceptions cleanly."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Mask unexpected errors to prevent leaking stack traces or sensitive values."""
    logger.error(f"Unhandled exception during request {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the request.",
            }
        },
    )


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint as defined in API.md."""
    return {"message": "StartupLens AI API is running"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Standard health check endpoint with provider validation status."""
    return HealthResponse(
        status="ok",
        service="StartupLens AI API",
        message="StartupLens AI API is running",
    )


@app.get("/config/status", tags=["Configuration"])
async def config_status() -> Dict[str, Any]:
    """Provider health status endpoint. Never returns API keys."""
    provider_statuses = llm_router.provider_statuses()
    overall = llm_router.overall_status()

    return {
        "status": overall,
        "providers": provider_statuses,
        "default_model": model_registry.get_default_model_id(),
        # Legacy fields kept for backward compat with existing tests
        "keys": settings.validate_keys(),
        "llm_provider": "Multi-Provider (Gemini / Groq / Mistral)",
        "configured_model": settings.GEMINI_MODEL,
        "model": settings.GEMINI_MODEL,
        "search_provider": "Tavily",
    }


# ==========================================
# MODEL DISCOVERY ENDPOINT
# ==========================================

@app.get("/models", tags=["Models"])
async def list_models():
    """Return available AI models (only those with configured API keys)."""
    return llm_router.list_models_response()


# ==========================================
# PHASE 1: DOCUMENT RESEARCH ENDPOINTS
# ==========================================

@app.post("/documents/upload", response_model=DocumentResponse, tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    """Upload research document (PDF, DOCX, TXT, MD) and extract structured content."""
    try:
        content = await file.read()
        parsed = document_service.parse_document(filename=file.filename or "uploaded_file", file_bytes=content)
        db.save_document(parsed)
        return DocumentResponse(
            id=parsed["id"],
            filename=parsed["filename"],
            file_type=parsed["file_type"],
            file_size=parsed["file_size"],
            created_at=parsed["created_at"],
            section_count=len(parsed.get("sections", [])),
        )
    except DocumentValidationError as ve:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "DOCUMENT_VALIDATION_ERROR", "message": str(ve)}},
        )
    except DocumentParseError as pe:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": "DOCUMENT_PARSE_ERROR", "message": str(pe)}},
        )
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "Failed to upload document."}},
        )


@app.get("/documents/{doc_id}", response_model=DocumentDetailResponse, tags=["Documents"])
async def get_document(doc_id: str):
    """Retrieve document metadata and extracted text sections."""
    doc = db.get_document(doc_id=doc_id)
    if not doc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": f"Document '{doc_id}' not found."}},
        )
    return DocumentDetailResponse(
        id=doc["id"],
        filename=doc["filename"],
        file_type=doc["file_type"],
        file_size=doc["file_size"],
        created_at=doc["created_at"],
        section_count=len(doc.get("sections", [])),
        content_text=doc["content_text"],
        sections=doc.get("sections", []),
    )


@app.delete("/documents/{doc_id}", tags=["Documents"])
async def delete_document(doc_id: str):
    """Remove an uploaded document."""
    deleted = db.delete_document(doc_id=doc_id)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": f"Document '{doc_id}' not found."}},
        )
    return {"message": "Document deleted successfully", "document_id": doc_id}


# ==========================================
# RESEARCH & OPPORTUNITY PIPELINE
# ==========================================

@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid topic or request"},
        401: {"model": ErrorResponse, "description": "Gemini authentication failed"},
        429: {"model": ErrorResponse, "description": "Gemini free-tier rate limit reached"},
        503: {"model": ErrorResponse, "description": "AI or web research service unavailable"},
        500: {"model": ErrorResponse, "description": "Pipeline failure"},
    },
    tags=["Research"],
)
async def analyze_topic(request: AnalyzeRequest):
    """
    Run the research → opportunity pipeline for a topic.
    Includes attached documents and requested Gemini model.
    """
    topic = request.topic.strip()
    if len(topic) < 2:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "INVALID_TOPIC",
                    "message": "Topic must contain at least 2 characters.",
                }
            },
        )

    # Resolve model via the new multi-provider router
    raw_model = (request.model or "auto").strip().lower()
    if raw_model == "auto":
        resolved_model_id = "auto"
    else:
        try:
            resolved_model_id = llm_router.resolve_model_id(request.model)
        except ValueError as ve:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "INVALID_MODEL",
                        "message": str(ve),
                    }
                },
            )

    session_id = f"session_{uuid.uuid4().hex[:12]}"
    logger.info(
        f"Processing research session [{session_id}] topic='{topic}' model_id='{resolved_model_id}'"
    )

    try:
        # Step 1: Research+Analysis Agent
        research_result, analysis_result = research_agent.run(
            topic=topic,
            document_ids=request.document_ids or [],
            model_id=resolved_model_id,
        )

        # Step 2: Opportunity Agent with scoring
        opportunities = opportunity_agent.run(
            research=research_result,
            analysis=analysis_result,
            model_id=resolved_model_id,
        )

        last_exec = (
            getattr(opportunity_agent, "last_execution", None)
            or getattr(research_agent, "last_execution", None)
            or {}
        )
        provider_used = last_exec.get("provider")
        fallback_used = bool(last_exec.get("fallback_used", False))
        fallback_reason = last_exec.get("fallback_reason")
        effective_model = last_exec.get("model") or resolved_model_id

        # Step 3: Persist session to SQLite
        try:
            db.save_analysis_session(
                session_id=session_id,
                topic=topic,
                research=research_result,
                analysis=analysis_result,
                opportunities=opportunities,
                sources=research_result.sources,
                model_used=effective_model,
            )
        except Exception as db_err:
            logger.error(f"Database persistence failed for session [{session_id}]: {db_err}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "PERSISTENCE_ERROR",
                        "message": "Analysis succeeded but failed to persist results.",
                    }
                },
            )

        retrieved_at = research_result.retrieved_at or datetime.now(timezone.utc).isoformat()
        disclaimer = f"Based on web sources retrieved on {retrieved_at}."
        if request.document_ids:
            disclaimer += f" Includes {len(request.document_ids)} attached research document(s)."

        return AnalyzeResponse(
            id=session_id,
            session_id=session_id,
            topic=topic,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            retrieved_at=retrieved_at,
            model_used=effective_model,
            provider_used=provider_used,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            research_disclaimer=disclaimer,
            research=research_result,
            analysis=analysis_result,
            opportunities=opportunities,
            sources=research_result.sources,
        )

    except TavilyServiceError as e:
        logger.error(f"Tavily web research unavailable for '{topic}': {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "WEB_RESEARCH_FAILED",
                    "message": "Current web research could not be completed. Try again when web research is available.",
                }
            },
        )
    except (LLMQuotaExhaustedError, GeminiQuotaExhaustedError) as e:
        logger.warning(f"LLM quota exhausted for session [{session_id}] topic='{topic}': {e}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "AI_QUOTA_EXHAUSTED",
                    "message": "The AI service quota has been exhausted. Please try again after the quota resets.",
                }
            },
        )
    except (LLMRateLimitError, GeminiRateLimitError) as e:
        logger.warning(f"LLM rate limit exceeded for session [{session_id}] topic='{topic}': {e}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "AI_RATE_LIMITED",
                    "message": str(e) or "AI service rate limit reached. Please try again shortly.",
                }
            },
        )
    except (LLMServiceUnavailableError, GeminiServiceUnavailableError) as e:
        logger.error(f"LLM service unavailable for session [{session_id}] topic='{topic}': {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "AI_SERVICE_UNAVAILABLE",
                    "message": str(e) or "The AI service is temporarily unavailable. Please try again shortly.",
                }
            },
        )
    except (LLMAuthError, GeminiAuthError) as e:
        logger.error(f"LLM authentication failed for session [{session_id}] topic='{topic}': {e}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "code": "AI_AUTH_ERROR",
                    "message": str(e) or "AI authentication failed. Please verify your API key.",
                }
            },
        )
    except LLMInvalidRequestError as e:
        logger.error(f"LLM invalid request for session [{session_id}]: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "AI_INVALID_REQUEST",
                    "message": "Invalid request sent to AI service.",
                }
            },
        )
    except (LLMError, GeminiServiceError) as e:
        logger.error(f"LLM provider failure for session [{session_id}] topic='{topic}': {e}")
        error_msg = str(e)
        if "400" in error_msg or "invalid" in error_msg.lower():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "AI_INVALID_REQUEST",
                        "message": "Invalid request sent to AI service.",
                    }
                },
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "PIPELINE_ERROR",
                    "message": "Failed to complete opportunity analysis. Please try again.",
                }
            },
        )
    except Exception as e:
        logger.error(f"Error during analysis pipeline for '{topic}': {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "PIPELINE_ERROR",
                    "message": "Failed to complete opportunity analysis. Please try again.",
                }
            },
        )


@app.get(
    "/research",
    response_model=List[SessionSummary],
    tags=["Research"],
)
@app.get(
    "/sessions",
    response_model=List[SessionSummary],
    tags=["Research"],
    include_in_schema=False,
)
async def list_research_sessions(limit: int = 50, offset: int = 0):
    """Return recent saved research sessions."""
    try:
        sessions = db.get_sessions(limit=limit, offset=offset)
        return sessions
    except Exception as e:
        logger.error(f"Error fetching research sessions: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to retrieve research sessions.",
                }
            },
        )


@app.get(
    "/research/{session_id}",
    response_model=AnalyzeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Database failure"},
    },
    tags=["Research"],
)
@app.get(
    "/sessions/{session_id}",
    response_model=AnalyzeResponse,
    include_in_schema=False,
    tags=["Research"],
)
async def get_research_session(session_id: str):
    """Return the complete saved research session."""
    try:
        session_data = db.get_session(session_id=session_id)
        if not session_data:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Research session '{session_id}' not found.",
                    }
                },
            )
        return AnalyzeResponse(**session_data)
    except Exception as e:
        logger.error(f"Error fetching session '{session_id}': {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to retrieve research session.",
                }
            },
        )


@app.delete(
    "/research/{session_id}",
    response_model=DeleteSessionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Database failure"},
    },
    tags=["Research"],
)
@app.delete(
    "/sessions/{session_id}",
    response_model=DeleteSessionResponse,
    include_in_schema=False,
    tags=["Research"],
)
async def delete_research_session(session_id: str):
    """Delete the session and its related data safely."""
    try:
        deleted = db.delete_session(session_id=session_id)
        if not deleted:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Research session '{session_id}' not found.",
                    }
                },
            )
        return DeleteSessionResponse(
            message="Session deleted successfully",
            session_id=session_id,
        )
    except Exception as e:
        logger.error(f"Error deleting session '{session_id}': {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to delete research session.",
                }
            },
        )


# ==========================================
# PHASE 4: OPPORTUNITY SCORE ENDPOINT
# ==========================================

@app.get("/opportunities/{opp_id}/score", response_model=OpportunityScore, tags=["Opportunities"])
async def get_opportunity_score(opp_id: str):
    """Retrieve validation scorecard for a specific opportunity."""
    score = db.get_opportunity_score(opp_id)
    if not score:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": f"Score for opportunity '{opp_id}' not found."}},
        )
    return OpportunityScore(**score)


# ==========================================
# PHASE 6: SAVED IDEAS ENDPOINTS
# ==========================================

@app.post("/saved-ideas", response_model=SavedIdeaResponse, tags=["Saved Ideas"])
async def save_idea(req: SaveIdeaRequest):
    """Save an opportunity hypothesis to SQLite."""
    score_dict = req.score.model_dump() if req.score else None
    opp_dict = {
        "title": req.title,
        "problem": req.problem,
        "customer": req.customer,
        "solution": req.solution,
        "why_now": req.why_now,
        "competitors": req.competitors,
        "mvp_features": req.mvp_features,
        "risks": req.risks,
        "evidence": req.evidence,
        "score": score_dict,
    }

    saved = db.save_idea(
        opportunity=opp_dict,
        session_id=req.session_id,
        topic=req.topic,
    )
    return SavedIdeaResponse(
        id=saved["id"],
        session_id=saved.get("session_id"),
        topic=saved.get("topic") or req.topic,
        title=req.title,
        problem=req.problem,
        customer=req.customer,
        solution=req.solution,
        why_now=req.why_now,
        competitors=req.competitors,
        mvp_features=req.mvp_features,
        risks=req.risks,
        evidence=req.evidence,
        score=req.score,
        created_at=saved["created_at"],
    )


@app.get("/saved-ideas", response_model=List[SavedIdeaResponse], tags=["Saved Ideas"])
async def list_saved_ideas():
    """Retrieve all saved opportunity ideas."""
    ideas = db.get_saved_ideas()
    result = []
    for item in ideas:
        opp = item.get("opportunity", {})
        score_val = None
        if opp.get("score"):
            try:
                score_val = OpportunityScore(**opp["score"])
            except Exception:
                score_val = None

        result.append(
            SavedIdeaResponse(
                id=item["id"],
                session_id=item.get("session_id"),
                topic=item.get("topic") or "General",
                title=opp.get("title", item.get("opportunity_title", "Opportunity")),
                problem=opp.get("problem", ""),
                customer=opp.get("customer", ""),
                solution=opp.get("solution", ""),
                why_now=opp.get("why_now", ""),
                competitors=opp.get("competitors", []),
                mvp_features=opp.get("mvp_features", []),
                risks=opp.get("risks", []),
                evidence=opp.get("evidence", []),
                score=score_val,
                created_at=item["created_at"],
            )
        )
    return result


@app.delete("/saved-ideas/{idea_id}", tags=["Saved Ideas"])
async def delete_saved_idea(idea_id: str):
    """Remove a saved opportunity idea."""
    deleted = db.delete_saved_idea(idea_id_or_title=idea_id)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": f"Saved idea '{idea_id}' not found."}},
        )
    return {"message": "Saved idea deleted successfully", "id": idea_id}


# ==========================================
# PHASE 7 & 8: RESEARCH TRACKER & MARKET SIGNALS
# ==========================================

@app.post("/research-trackers", response_model=ResearchTrackerResponse, tags=["Tracker"])
async def create_tracker(req: CreateTrackerRequest):
    """Enable research tracking for a topic."""
    tracker = db.save_tracker(
        topic=req.topic,
        session_id=req.session_id,
        status="active",
    )
    return ResearchTrackerResponse(**tracker)


@app.get("/research-trackers", response_model=List[ResearchTrackerResponse], tags=["Tracker"])
async def list_trackers():
    """List all research trackers."""
    trackers = db.get_trackers()
    return [ResearchTrackerResponse(**t) for t in trackers]


@app.delete("/research-trackers/{tracker_id}", tags=["Tracker"])
async def delete_tracker(tracker_id: str):
    """Remove or disable a research tracker."""
    deleted = db.delete_tracker(tracker_id)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": f"Tracker '{tracker_id}' not found."}},
        )
    return {"message": "Tracker removed successfully", "id": tracker_id}


@app.post("/research-trackers/{tracker_id}/refresh", tags=["Tracker"])
async def refresh_tracker(tracker_id: str):
    """
    Refresh a tracked topic: queries Tavily for fresh web evidence and detects changes/new market signals.
    """
    tracker = db.get_tracker(tracker_id)
    if not tracker:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": f"Tracker '{tracker_id}' not found."}},
        )

    topic = tracker["topic"]
    logger.info(f"Refreshing tracker '{tracker_id}' for topic: '{topic}'")

    try:
        # Run research on fresh topic
        research_result, analysis_result = research_agent.run(topic=topic)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Detect signals from analysis
        new_signals = []
        for sig_text in (analysis_result.market_signals + research_result.market_signals)[:3]:
            sig_id = f"sig_{uuid.uuid4().hex[:10]}"
            signal_entry = db.save_market_signal(
                signal_id=sig_id,
                tracker_id=tracker_id,
                topic=topic,
                signal_type="market_signal",
                title=f"New Market Signal in {topic}",
                change_summary=sig_text,
                evidence=research_result.sources[0].url if research_result.sources else None,
                detected_at=now_iso,
            )
            new_signals.append(signal_entry)

        db.update_tracker_status(tracker_id, status="active", last_updated=now_iso, next_update="Tomorrow")
        return {"message": "Tracker refreshed successfully", "signals_detected": len(new_signals), "signals": new_signals}

    except Exception as e:
        logger.error(f"Error refreshing tracker '{tracker_id}': {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "REFRESH_ERROR", "message": "Failed to refresh tracker."}},
        )


@app.get("/market-signals", response_model=List[MarketSignalResponse], tags=["Signals"])
async def list_market_signals(tracker_id: Optional[str] = None):
    """Retrieve detected market signals."""
    signals = db.get_market_signals(tracker_id=tracker_id)
    return [MarketSignalResponse(**s) for s in signals]


# ==========================================
# PHASE 9: WEEKLY STARTUP BRIEF
# ==========================================

@app.get("/weekly-reports", response_model=List[WeeklyReportResponse], tags=["Reports"])
async def list_weekly_reports():
    """Retrieve stored weekly research briefing reports."""
    reports = db.get_weekly_reports()
    return [WeeklyReportResponse(**r) for r in reports]


# ==========================================
# PHASE 10: EXPORT ENDPOINT (PDF, Markdown, JSON)
# ==========================================

@app.post("/reports/export", tags=["Export"])
async def export_session(req: ExportRequest):
    """Export research session to PDF, Markdown, or JSON."""
    session_data = db.get_session(session_id=req.session_id)
    if not session_data:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": f"Session '{req.session_id}' not found."}},
        )

    fmt = req.format.lower().strip()
    topic_slug = "".join(c if c.isalnum() else "_" for c in session_data.get("topic", "research"))[:30]

    if fmt == "json":
        json_str = export_service.to_json(session_data)
        return Response(
            content=json_str,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="startuplens_{topic_slug}.json"'},
        )
    elif fmt in ("markdown", "md"):
        md_str = export_service.to_markdown(session_data)
        return Response(
            content=md_str,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="startuplens_{topic_slug}.md"'},
        )
    elif fmt == "pdf":
        try:
            pdf_bytes = export_service.to_pdf_bytes(session_data)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="startuplens_{topic_slug}.pdf"'},
            )
        except Exception as e:
            logger.error(f"PDF generation failed: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": {"code": "PDF_EXPORT_ERROR", "message": "Failed to generate PDF export."}},
            )
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "INVALID_FORMAT", "message": "Supported formats: pdf, markdown, json."}},
        )
