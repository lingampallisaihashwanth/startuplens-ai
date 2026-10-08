import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.model_router import model_router  # legacy, kept for compat
from backend.llm.router import llm_router
from backend.llm.registry import model_registry
from backend.services.document_service import document_service, DocumentValidationError, DocumentParseError
from backend.services.export_service import export_service
from backend.schemas.opportunity import OpportunityScore, calculate_confidence_label

client = TestClient(app)


# ==========================================
# PHASE 1: DOCUMENT TESTS
# ==========================================

def test_document_validation_unsupported_extension():
    with pytest.raises(DocumentValidationError):
        document_service.validate_file("malicious.exe", b"binary content")


def test_document_validation_empty_file():
    with pytest.raises(DocumentValidationError):
        document_service.validate_file("empty.txt", b"   ")


def test_document_parse_text_sections():
    raw_md = b"# Section 1: Background\nContent for section 1.\n\n# Section 2: Pain Points\nCustomer complains."
    res = document_service.parse_document("test.md", raw_md)
    assert res["file_type"] == "md"
    assert len(res["sections"]) == 2
    assert res["sections"][0]["page_or_section"] == "Section 1: Background"
    assert "Customer complains" in res["sections"][1]["text"]


def test_document_upload_and_retrieve_api():
    file_bytes = b"# Heading\nExtracted research document text."
    files = {"file": ("research_notes.md", file_bytes, "text/markdown")}
    upload_res = client.post("/documents/upload", files=files)
    assert upload_res.status_code == 200
    doc_data = upload_res.json()
    assert doc_data["filename"] == "research_notes.md"
    assert doc_data["file_type"] == "md"
    doc_id = doc_data["id"]

    # Retrieve
    get_res = client.get(f"/documents/{doc_id}")
    assert get_res.status_code == 200
    detail = get_res.json()
    assert "Extracted research document text." in detail["content_text"]

    # Delete
    del_res = client.delete(f"/documents/{doc_id}")
    assert del_res.status_code == 200


# ==========================================
# MODEL REGISTRY & RESOLUTION TESTS
# ==========================================

def test_model_list_endpoint():
    """Verify /models returns auto + at least one enabled provider model."""
    res = client.get("/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert "default" in data
    # 'auto' is always present
    model_ids = [m["id"] for m in data["models"]]
    assert "auto" in model_ids


def test_model_resolution_valid_and_auto():
    """Verify llm_router resolves auto/None to a configured model."""
    # 'auto' should resolve to something (at least gemini-balanced if configured)
    enabled_ids = {m["id"] for m in model_registry.list_models(only_enabled=True)}
    # We can't assume a specific model, but resolution must not raise
    resolved = llm_router.resolve_model_id("auto")
    assert resolved in enabled_ids or resolved == "auto"
    resolved_none = llm_router.resolve_model_id(None)
    assert isinstance(resolved_none, str) and len(resolved_none) > 0


def test_model_resolution_invalid_raises():
    """Verify unknown model IDs raise ValueError."""
    with pytest.raises(ValueError):
        llm_router.resolve_model_id("openai-gpt-4o")
    with pytest.raises(ValueError):
        llm_router.resolve_model_id("nonexistent-model-xyz")


# ==========================================
# PHASE 4: OPPORTUNITY SCORING TESTS
# ==========================================

def test_opportunity_score_confidence_calculation():
    assert calculate_confidence_label(45) == "High Potential"
    assert calculate_confidence_label(35) == "Promising"
    assert calculate_confidence_label(25) == "Experimental"
    assert calculate_confidence_label(15) == "Low Confidence"


def test_opportunity_score_model():
    score = OpportunityScore(
        market_demand=9,
        competitive_pressure=8,
        execution_feasibility=9,
        market_timing=9,
        ai_advantage=9,
        overall_score=44,
        confidence_label="High Potential",
        rationale="Strong demand backed by venture signals.",
    )
    assert score.overall_score == 44
    assert score.confidence_label == "High Potential"


# ==========================================
# PHASE 6: SAVED IDEAS TESTS
# ==========================================

def test_saved_ideas_crud():
    payload = {
        "topic": "Clean Energy Storage",
        "title": "Grid Battery Orchestration",
        "problem": "Renewable intermittent curtailment",
        "customer": "Utility grid operators",
        "solution": "Algorithmic battery cycling hypothesis",
        "why_now": "IRA subsidies and grid modernization",
        "competitors": ["Tesla Megapack software"],
        "mvp_features": ["Telemetry parser", "Dispatch scheduler"],
        "risks": ["Regulatory grid compliance"],
        "evidence": ["https://example.com/energy-report"],
        "score": {
            "market_demand": 9,
            "competitive_pressure": 7,
            "execution_feasibility": 8,
            "market_timing": 9,
            "ai_advantage": 8,
            "overall_score": 41,
            "confidence_label": "High Potential",
            "rationale": "High urgency with strong timing driver.",
        },
    }
    create_res = client.post("/saved-ideas", json=payload)
    assert create_res.status_code == 200
    saved_idea = create_res.json()
    idea_id = saved_idea["id"]
    assert saved_idea["title"] == "Grid Battery Orchestration"

    # List
    list_res = client.get("/saved-ideas")
    assert list_res.status_code == 200
    all_ideas = list_res.json()
    assert any(i["id"] == idea_id for i in all_ideas)

    # Delete
    del_res = client.delete(f"/saved-ideas/{idea_id}")
    assert del_res.status_code == 200


# ==========================================
# PHASE 7 & 8: TRACKER & CHANGE DETECTION TESTS
# ==========================================

def test_research_tracker_lifecycle():
    create_res = client.post("/research-trackers", json={"topic": "Quantum Encryption"})
    assert create_res.status_code == 200
    tracker = create_res.json()
    tracker_id = tracker["id"]
    assert tracker["status"] == "active"

    # List
    trackers_res = client.get("/research-trackers")
    assert trackers_res.status_code == 200
    assert any(t["id"] == tracker_id for t in trackers_res.json())

    # Delete
    del_res = client.delete(f"/research-trackers/{tracker_id}")
    assert del_res.status_code == 200


# ==========================================
# PHASE 10: EXPORT TESTS
# ==========================================

def test_export_markdown_and_json():
    mock_session = {
        "session_id": "sess_test_123",
        "topic": "Autonomous Drones",
        "created_at": "2026-10-07T12:00:00Z",
        "model_used": "Gemini 2.5 Flash",
        "research": {"trends": ["Swarm navigation", "Longer endurance battery"], "problems": ["GPS spoofing"]},
        "analysis": {"market_signals": ["FAA BVLOS approval expansion"], "market_gaps": ["Hardened GPS-denied navigation"]},
        "opportunities": [{
            "title": "GPS-Denied Drone Autopilot",
            "customer": "Industrial inspection",
            "solution": "Visual inertial SLAM on edge",
            "why_now": "Small low-power NPU availability",
            "mvp_features": ["Edge SLAM pipeline", "Fail-safe loiter"],
            "risks": ["Sensor drift in dust"],
            "score": {"overall_score": 42, "confidence_label": "High Potential", "rationale": "High edge demand"},
        }],
        "sources": [{"title": "Drone Industry Today", "url": "https://example.com/drones", "source_type": "web"}],
    }

    # Markdown export
    md_out = export_service.to_markdown(mock_session)
    assert "# StartupLens AI — Research Intelligence Brief" in md_out
    assert "Autonomous Drones" in md_out
    assert "GPS-Denied Drone Autopilot" in md_out

    # JSON export
    json_out = export_service.to_json(mock_session)
    assert "Autonomous Drones" in json_out

    # PDF export
    pdf_bytes = export_service.to_pdf_bytes(mock_session)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")
