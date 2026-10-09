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
from fastapi.responses import JSONResponse, Response, RedirectResponse

from backend.schemas.auth import (
    UserResponse,
    SignupRequest,
    LoginRequest,
    AuthResponse,
    SessionStatusResponse,
)
from backend.services.auth_service import (
    auth_service,
    AuthError,
    OAuthError,
    InvalidCredentialsError,
)

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
    ChatRequest,
    ChatResponse,
)
from backend.schemas.opportunity import OpportunityScore, calculate_confidence_label
from backend.services.intent_service import intent_service, IntentType
from backend.agents.company_agent import company_agent
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
    error_code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = "UNAUTHORIZED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        error_code = "FORBIDDEN"
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        error_code = "NOT_FOUND"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": error_code,
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


# ── Auth Helpers ─────────────────────────────────────────────────────────────

def get_frontend_url() -> str:
    """Resolve primary frontend base URL for OAuth redirects."""
    if settings.FRONTEND_URL:
        return settings.FRONTEND_URL.split(",")[0].strip().rstrip("/")
    return "http://localhost:3000"


def set_session_cookie(response: Response, token: str) -> None:
    """Set secure HTTP-only application session cookie."""
    is_prod = settings.ENVIRONMENT.lower() == "production"
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_EXPIRE_SECONDS,
        httponly=True,
        secure=is_prod,
        samesite="none" if is_prod else "lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Delete session cookie on sign out."""
    is_prod = settings.ENVIRONMENT.lower() == "production"
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        secure=is_prod,
        samesite="none" if is_prod else "lax",
        path="/",
    )


def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """Resolve authenticated user from Bearer header or session cookie."""
    auth_header = request.headers.get("authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        return None
    return auth_service.get_user_from_token(token)


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Enforce authentication on protected routes when REQUIRE_AUTH is enabled."""
    user = get_current_user_optional(request)
    if not user and settings.REQUIRE_AUTH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user


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
# AUTHENTICATION & SOCIAL LOGIN ENDPOINTS
# ==========================================

@app.get("/auth/google", tags=["Authentication"])
async def auth_google(request: Request, redirect_to: Optional[str] = None):
    """Initiate Google OAuth 2.0 / OIDC flow with CSRF protection."""
    frontend_url = get_frontend_url()
    try:
        state = auth_service.create_oauth_state("google", redirect_to=redirect_to)
        auth_url = auth_service.get_google_auth_url(state)
        return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    except OAuthError as oe:
        logger.error(f"Google OAuth initialization failed: {oe}")
        return RedirectResponse(url=f"{frontend_url}/login?error=google_failed", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Unexpected error starting Google OAuth: {e}")
        return RedirectResponse(url=f"{frontend_url}/login?error=google_failed", status_code=status.HTTP_302_FOUND)


@app.get("/auth/google/callback", tags=["Authentication"])
async def auth_google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Handle Google OAuth 2.0 callback, exchange code, verify identity, set cookie."""
    frontend_url = get_frontend_url()
    if error or not code or not state:
        logger.info(f"Google sign-in cancelled or failed with error: {error}")
        err_code = "cancelled" if error in ("access_denied", "user_cancelled_authorize") else "google_failed"
        return RedirectResponse(url=f"{frontend_url}/login?error={err_code}", status_code=status.HTTP_302_FOUND)

    state_record = auth_service.verify_oauth_state(state, "google")
    if not state_record:
        logger.warning(f"Invalid or expired OAuth state for Google: {state}")
        return RedirectResponse(url=f"{frontend_url}/login?error=google_failed", status_code=status.HTTP_302_FOUND)

    try:
        profile = await auth_service.handle_google_callback(code)
        user = auth_service.authenticate_or_link_social_user(profile)
        token, _ = auth_service.create_session_for_user(user)

        target_url = f"{frontend_url}/?auth_success=1"
        response = RedirectResponse(url=target_url, status_code=status.HTTP_302_FOUND)
        set_session_cookie(response, token)
        return response
    except Exception as e:
        logger.error(f"Google OAuth callback processing error: {e}", exc_info=True)
        return RedirectResponse(url=f"{frontend_url}/login?error=google_failed", status_code=status.HTTP_302_FOUND)


@app.get("/auth/github", tags=["Authentication"])
async def auth_github(request: Request, redirect_to: Optional[str] = None):
    """Initiate GitHub OAuth flow with CSRF protection and minimal scopes."""
    frontend_url = get_frontend_url()
    try:
        state = auth_service.create_oauth_state("github", redirect_to=redirect_to)
        auth_url = auth_service.get_github_auth_url(state)
        return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    except OAuthError as oe:
        logger.error(f"GitHub OAuth initialization failed: {oe}")
        return RedirectResponse(url=f"{frontend_url}/login?error=github_failed", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Unexpected error starting GitHub OAuth: {e}")
        return RedirectResponse(url=f"{frontend_url}/login?error=github_failed", status_code=status.HTTP_302_FOUND)


@app.get("/auth/github/callback", tags=["Authentication"])
async def auth_github_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Handle GitHub OAuth callback, exchange code, verify identity, set cookie."""
    frontend_url = get_frontend_url()
    if error or not code or not state:
        logger.info(f"GitHub sign-in cancelled or failed with error: {error}")
        err_code = "cancelled" if error in ("access_denied", "user_cancelled_authorize") else "github_failed"
        return RedirectResponse(url=f"{frontend_url}/login?error={err_code}", status_code=status.HTTP_302_FOUND)

    state_record = auth_service.verify_oauth_state(state, "github")
    if not state_record:
        logger.warning(f"Invalid or expired OAuth state for GitHub: {state}")
        return RedirectResponse(url=f"{frontend_url}/login?error=github_failed", status_code=status.HTTP_302_FOUND)

    try:
        profile = await auth_service.handle_github_callback(code)
        user = auth_service.authenticate_or_link_social_user(profile)
        token, _ = auth_service.create_session_for_user(user)

        target_url = f"{frontend_url}/?auth_success=1"
        response = RedirectResponse(url=target_url, status_code=status.HTTP_302_FOUND)
        set_session_cookie(response, token)
        return response
    except Exception as e:
        logger.error(f"GitHub OAuth callback processing error: {e}", exc_info=True)
        return RedirectResponse(url=f"{frontend_url}/login?error=github_failed", status_code=status.HTTP_302_FOUND)


@app.get("/auth/linkedin", tags=["Authentication"])
async def auth_linkedin(request: Request, redirect_to: Optional[str] = None):
    """Initiate LinkedIn OIDC flow with CSRF protection and minimal scopes."""
    frontend_url = get_frontend_url()
    try:
        state = auth_service.create_oauth_state("linkedin", redirect_to=redirect_to)
        auth_url = auth_service.get_linkedin_auth_url(state)
        return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    except OAuthError as oe:
        logger.error(f"LinkedIn OAuth initialization failed: {oe}")
        return RedirectResponse(url=f"{frontend_url}/login?error=linkedin_failed", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Unexpected error starting LinkedIn OAuth: {e}")
        return RedirectResponse(url=f"{frontend_url}/login?error=linkedin_failed", status_code=status.HTTP_302_FOUND)


@app.get("/auth/linkedin/callback", tags=["Authentication"])
async def auth_linkedin_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Handle LinkedIn OIDC callback, exchange code, verify identity, set cookie."""
    frontend_url = get_frontend_url()
    if error or not code or not state:
        logger.info(f"LinkedIn sign-in cancelled or failed with error: {error}")
        err_code = "cancelled" if error in ("access_denied", "user_cancelled_authorize") else "linkedin_failed"
        return RedirectResponse(url=f"{frontend_url}/login?error={err_code}", status_code=status.HTTP_302_FOUND)

    state_record = auth_service.verify_oauth_state(state, "linkedin")
    if not state_record:
        logger.warning(f"Invalid or expired OAuth state for LinkedIn: {state}")
        return RedirectResponse(url=f"{frontend_url}/login?error=linkedin_failed", status_code=status.HTTP_302_FOUND)

    try:
        profile = await auth_service.handle_linkedin_callback(code)
        user = auth_service.authenticate_or_link_social_user(profile)
        token, _ = auth_service.create_session_for_user(user)

        target_url = f"{frontend_url}/?auth_success=1"
        response = RedirectResponse(url=target_url, status_code=status.HTTP_302_FOUND)
        set_session_cookie(response, token)
        return response
    except Exception as e:
        logger.error(f"LinkedIn OAuth callback processing error: {e}", exc_info=True)
        return RedirectResponse(url=f"{frontend_url}/login?error=linkedin_failed", status_code=status.HTTP_302_FOUND)


@app.post("/auth/signup", response_model=AuthResponse, tags=["Authentication"])
async def signup(req: SignupRequest, response: Response):
    """Register a new user account with email and password."""
    name = req.name.strip()
    email = req.email.strip().lower()
    if len(name) < 1:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Full Name is required."}},
        )
    if "@" not in email or "." not in email:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Please enter a valid email address."}},
        )
    if len(req.password) < 8:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Password must be at least 8 characters."}},
        )
    if req.confirm_password is not None and req.password != req.confirm_password:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "PASSWORD_MISMATCH", "message": "Passwords do not match."}},
        )

    existing = db.get_user_by_email(email)
    if existing:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "EMAIL_EXISTS", "message": "An account with this email already exists."}},
        )

    p_hash = auth_service.hash_password(req.password)
    user = db.create_user(
        name=name,
        email=email,
        password_hash=p_hash,
        auth_provider="email",
    )
    token, _ = auth_service.create_session_for_user(user)
    set_session_cookie(response, token)

    return AuthResponse(
        user=UserResponse(**user),
        token=token,
        message="Account created successfully",
    )


@app.post("/auth/login", response_model=AuthResponse, tags=["Authentication"])
async def login(req: LoginRequest, response: Response):
    """Authenticate existing user with email and password."""
    email = req.email.strip().lower()
    user = db.get_user_by_email(email)
    if not user:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}},
        )

    if not user.get("password_hash"):
        providers = [p.get("provider", "").title() for p in user.get("linked_providers", [])]
        provider_name = ", ".join(providers) if providers else (user.get("auth_provider") or "social login").title()
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "SOCIAL_ACCOUNT_ONLY",
                    "message": f"This account was registered with {provider_name}. Please sign in with that provider.",
                }
            },
        )

    if not auth_service.verify_password(req.password, user["password_hash"]):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}},
        )

    token, _ = auth_service.create_session_for_user(user)
    set_session_cookie(response, token)

    return AuthResponse(
        user=UserResponse(**user),
        token=token,
        message="Logged in successfully",
    )


@app.post("/auth/logout", tags=["Authentication"])
async def logout(request: Request, response: Response):
    """Sign out user, revoke session, and clear cookies."""
    auth_header = request.headers.get("authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        auth_service.revoke_session(token)

    clear_session_cookie(response)
    return {"message": "Logged out successfully"}


@app.get("/auth/me", response_model=SessionStatusResponse, tags=["Authentication"])
async def get_current_user_profile(request: Request):
    """Return currently authenticated user profile."""
    user = get_current_user_optional(request)
    if not user:
        return SessionStatusResponse(authenticated=False, user=None)
    return SessionStatusResponse(authenticated=True, user=UserResponse(**user))


# ==========================================
# CHAT ENDPOINT (CONVERSATIONAL INTENT LAYER)
# ==========================================

def _resolve_model(model_name: Optional[str]) -> str:
    raw_model = (model_name or "auto").strip().lower()
    if raw_model == "auto":
        return "auto"
    return llm_router.resolve_model_id(raw_model)


def _execute_research_workflow(
    topic: str,
    document_ids: Optional[List[str]],
    resolved_model_id: str,
    user_id: Optional[str],
) -> AnalyzeResponse:
    intent_res = intent_service.detect_intent(topic)

    if intent_res.intent == IntentType.COMPANY_ANALYSIS:
        company_name = intent_res.company_name or topic
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        logger.info(
            f"Processing company intelligence session [{session_id}] company='{company_name}' topic='{topic}'"
        )
        research_result, analysis_result, company_result = company_agent.run(
            company_name=company_name,
            topic=topic,
            document_ids=document_ids or [],
            model_id=resolved_model_id,
        )
        last_exec = getattr(company_agent, "last_execution", {}) or {}
        provider_used = last_exec.get("provider")
        fallback_used = bool(last_exec.get("fallback_used", False))
        fallback_reason = last_exec.get("fallback_reason")
        effective_model = last_exec.get("model") or resolved_model_id

        db.save_analysis_session(
            session_id=session_id,
            topic=topic,
            research=research_result,
            analysis=analysis_result,
            opportunities=[],
            sources=research_result.sources,
            model_used=effective_model,
            user_id=user_id,
            company_analysis=company_result,
            intent=IntentType.COMPANY_ANALYSIS,
        )

        retrieved_at = research_result.retrieved_at or datetime.now(timezone.utc).isoformat()
        disclaimer = f"Based on live and historical web sources retrieved on {retrieved_at}."
        if document_ids:
            disclaimer += f" Includes {len(document_ids)} attached research document(s)."

        return AnalyzeResponse(
            id=session_id,
            session_id=session_id,
            topic=topic,
            intent=IntentType.COMPANY_ANALYSIS,
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
            opportunities=[],
            sources=research_result.sources,
            company_analysis=company_result,
        )

    else:
        # Market Research or Startup Opportunity Research
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        logger.info(
            f"Processing research session [{session_id}] topic='{topic}' model_id='{resolved_model_id}'"
        )
        research_result, analysis_result = research_agent.run(
            topic=topic,
            document_ids=document_ids or [],
            model_id=resolved_model_id,
        )
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

        db.save_analysis_session(
            session_id=session_id,
            topic=topic,
            research=research_result,
            analysis=analysis_result,
            opportunities=opportunities,
            sources=research_result.sources,
            model_used=effective_model,
            user_id=user_id,
            intent=intent_res.intent,
        )

        retrieved_at = research_result.retrieved_at or datetime.now(timezone.utc).isoformat()
        disclaimer = f"Based on web sources retrieved on {retrieved_at}."
        if document_ids:
            disclaimer += f" Includes {len(document_ids)} attached research document(s)."

        return AnalyzeResponse(
            id=session_id,
            session_id=session_id,
            topic=topic,
            intent=intent_res.intent,
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


def _handle_research_exception(e: Exception, topic: str) -> JSONResponse:
    if isinstance(e, TavilyServiceError):
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
    if isinstance(e, (LLMQuotaExhaustedError, GeminiQuotaExhaustedError)):
        logger.warning(f"LLM quota exhausted for topic='{topic}': {e}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "AI_QUOTA_EXHAUSTED",
                    "message": "The AI service quota has been exhausted. Please try again after the quota resets.",
                }
            },
        )
    if isinstance(e, (LLMRateLimitError, GeminiRateLimitError)):
        logger.warning(f"LLM rate limit exceeded for topic='{topic}': {e}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "AI_RATE_LIMITED",
                    "message": str(e) or "AI service rate limit reached. Please try again shortly.",
                }
            },
        )
    if isinstance(e, (LLMServiceUnavailableError, GeminiServiceUnavailableError)):
        logger.error(f"LLM service unavailable for topic='{topic}': {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "AI_SERVICE_UNAVAILABLE",
                    "message": str(e) or "The AI service is temporarily unavailable. Please try again shortly.",
                }
            },
        )
    if isinstance(e, (LLMAuthError, GeminiAuthError)):
        logger.error(f"LLM authentication failed for topic='{topic}': {e}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "code": "AI_AUTH_ERROR",
                    "message": str(e) or "AI authentication failed. Please verify your API key.",
                }
            },
        )
    if isinstance(e, LLMInvalidRequestError):
        logger.error(f"LLM invalid request for topic='{topic}': {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "AI_INVALID_REQUEST",
                    "message": "Invalid request sent to AI service.",
                }
            },
        )
    if isinstance(e, (LLMError, GeminiServiceError)):
        logger.error(f"LLM provider failure for topic='{topic}': {e}")
        error_msg = str(e)
        if "400" in error_msg or "invalid" in error_msg.lower():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "AI_INVALID_REQUEST",
                        "message": "The topic or parameters were rejected by the AI model.",
                    }
                },
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "PIPELINE_ERROR",
                    "message": "The AI reasoning pipeline encountered an unexpected failure.",
                }
            },
        )
    logger.error(f"Unexpected pipeline failure for topic='{topic}': {e}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during research analysis.",
            }
        },
    )


@app.post("/chat", response_model=ChatResponse, tags=["Research"])
async def chat_research(raw_req: Request):
    """
    Conversational intent layer for StartupLens AI.
    - Casual greetings/pleasantries: responds naturally without calling Tavily, /analyze, or DB sessions.
    - Company analysis: triggers 19-aspect evidence-grounded company case study.
    - Market / Opportunity research: triggers research pipeline.
    """
    user = get_current_user_optional(raw_req)
    try:
        body = await raw_req.json()
    except Exception:
        body = {}

    message = str(body.get("message", "")).strip()
    if not message:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "INVALID_MESSAGE", "message": "Message is required."}},
        )

    intent_res = intent_service.detect_intent(message)

    # 1. CASUAL_CHAT: Instant response, no Tavily, no /analyze, no DB persistence
    if intent_res.intent == IntentType.CASUAL_CHAT:
        return ChatResponse(
            intent=IntentType.CASUAL_CHAT,
            reply=intent_service.generate_casual_reply(message),
            session_id=None,
            data=None,
        )

    # 2. Substantive research requests
    raw_model = body.get("model")
    try:
        resolved_model_id = _resolve_model(raw_model)
    except ValueError as ve:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "INVALID_MODEL", "message": str(ve)}},
        )

    document_ids = body.get("document_ids") or []
    user_id = user["id"] if user else None

    try:
        result = _execute_research_workflow(
            topic=message,
            document_ids=document_ids,
            resolved_model_id=resolved_model_id,
            user_id=user_id,
        )

        if intent_res.intent == IntentType.COMPANY_ANALYSIS:
            reply_text = f"Completed company intelligence analysis for {intent_res.company_name or message}."
        elif intent_res.intent == IntentType.STARTUP_OPPORTUNITY_RESEARCH:
            reply_text = f"Generated startup opportunity hypotheses for {message}."
        else:
            reply_text = f"Completed market research for {message}."

        return ChatResponse(
            intent=intent_res.intent,
            reply=reply_text,
            session_id=result.session_id,
            data=result,
        )
    except Exception as e:
        return _handle_research_exception(e, message)


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
async def analyze_topic(request: AnalyzeRequest, raw_req: Request):
    """
    Run the research → opportunity pipeline for a topic.
    Includes attached documents and requested Gemini model.
    """
    user = get_current_user_optional(raw_req)
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

    try:
        resolved_model_id = _resolve_model(request.model)
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

    user_id = user["id"] if user else None
    try:
        return _execute_research_workflow(
            topic=topic,
            document_ids=request.document_ids or [],
            resolved_model_id=resolved_model_id,
            user_id=user_id,
        )
    except Exception as e:
        return _handle_research_exception(e, topic)


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
async def list_research_sessions(request: Request, limit: int = 50, offset: int = 0):
    """Return recent saved research sessions."""
    user = get_current_user(request)
    try:
        sessions = db.get_sessions(limit=limit, offset=offset, user_id=user["id"] if user else None)
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
async def get_research_session(session_id: str, request: Request):
    """Return the complete saved research session."""
    user = get_current_user(request)
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
        # Check user ownership if session belongs to another user
        if user and session_data.get("user_id") and session_data["user_id"] != user["id"]:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "You do not have permission to access this research session.",
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
async def delete_research_session(session_id: str, request: Request):
    """Delete the session and its related data safely."""
    user = get_current_user(request)
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
        # Check user ownership
        if user and session_data.get("user_id") and session_data["user_id"] != user["id"]:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "You do not have permission to delete this research session.",
                    }
                },
            )
        deleted = db.delete_session(session_id=session_id)
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
async def save_idea(req: SaveIdeaRequest, request: Request):
    """Save an opportunity hypothesis to SQLite."""
    user = get_current_user(request)
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
        user_id=user["id"] if user else None,
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
async def list_saved_ideas(request: Request):
    """Retrieve all saved opportunity ideas."""
    user = get_current_user(request)
    ideas = db.get_saved_ideas(user_id=user["id"] if user else None)
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
async def delete_saved_idea(idea_id: str, request: Request):
    """Remove a saved opportunity idea."""
    user = get_current_user(request)
    saved_idea = db.get_saved_idea(idea_id)
    if not saved_idea:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": f"Saved idea '{idea_id}' not found."}},
        )
    # Check user ownership
    if user and saved_idea.get("user_id") and saved_idea["user_id"] != user["id"]:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": {"code": "FORBIDDEN", "message": "You do not have permission to delete this saved idea."}},
        )
    deleted = db.delete_saved_idea(idea_id_or_title=idea_id)
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
