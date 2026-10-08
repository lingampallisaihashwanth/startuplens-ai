import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.db import DatabaseManager, db
from backend.schemas.research import ResearchOutput, ResearchSource
from backend.schemas.analysis import MarketAnalysisOutput
from backend.schemas.opportunity import Opportunity
from backend.services.gemini_service import GeminiService, GeminiServiceError
from backend.services.tavily_service import TavilyService, TavilyServiceError

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """
    Ensure each test runs with a fresh isolated SQLite database.
    Patches backend.main.db and backend.database.db.db.
    """
    temp_db_file = str(tmp_path / "test_startuplens.db")
    test_db = DatabaseManager(db_path=temp_db_file)
    test_db.init_db()

    with patch("backend.main.db", test_db), \
         patch("backend.database.db.db", test_db):
        yield test_db


# ---------------------------------------------------------------------------
# Test 1: Database initialization
# ---------------------------------------------------------------------------
def test_database_initialization(isolated_db):
    """Verify tables and indices are created with correct columns."""
    conn = isolated_db.get_connection()
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row["name"] for row in cursor.fetchall()}
    assert "sessions" in tables
    assert "sources" in tables
    assert "reports" in tables
    assert "opportunities" in tables

    # Check sessions table columns
    cursor = conn.execute("PRAGMA table_info(sessions);")
    cols = {row["name"] for row in cursor.fetchall()}
    assert {"id", "topic", "created_at", "updated_at"}.issubset(cols)

    # Check sources table columns
    cursor = conn.execute("PRAGMA table_info(sources);")
    cols = {row["name"] for row in cursor.fetchall()}
    assert {"id", "session_id", "title", "url", "published_at", "source_type"}.issubset(cols)

    # Check reports table columns
    cursor = conn.execute("PRAGMA table_info(reports);")
    cols = {row["name"] for row in cursor.fetchall()}
    assert {"id", "session_id", "report_json"}.issubset(cols)

    # Check opportunities table columns
    cursor = conn.execute("PRAGMA table_info(opportunities);")
    cols = {row["name"] for row in cursor.fetchall()}
    assert {"id", "session_id", "title", "problem", "customer", "solution", "mvp_json"}.issubset(cols)


# ---------------------------------------------------------------------------
# Test 2: Save session
# ---------------------------------------------------------------------------
def test_save_session(isolated_db):
    """Verify session row is saved correctly."""
    session_id = "test_session_001"
    topic = "AI Agriculture"

    isolated_db.save_analysis_session(
        session_id=session_id,
        topic=topic,
        research=ResearchOutput(topic=topic, trends=["Smart sensors"], startups=["AgriTech Inc"]),
        analysis=MarketAnalysisOutput(customer_segments=["Farmers"], market_gaps=["High cost"]),
        opportunities=[
            Opportunity(
                title="SensorBot",
                problem="High crop loss",
                customer="Commercial farmers",
                solution="Drone scouting",
                why_now="Cheaper cameras",
            )
        ],
        sources=[
            ResearchSource(
                title="Agri Trends",
                url="https://example.com/agri",
                source_type="web",
            )
        ],
    )

    conn = isolated_db.get_connection()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    assert row is not None
    assert row["id"] == session_id
    assert row["topic"] == topic
    assert row["created_at"] is not None
    assert row["updated_at"] is not None


# ---------------------------------------------------------------------------
# Test 3: Save sources
# ---------------------------------------------------------------------------
def test_save_sources(isolated_db):
    """Verify source records are persisted and linked via session_id."""
    session_id = "test_session_002"
    sources = [
        ResearchSource(title="Robotics Market Report", url="https://example.com/robotics", published_at="2026-01-01"),
        ResearchSource(title="AI Factory News", url="https://example.com/factory", published_at="2026-02-01"),
    ]

    isolated_db.save_analysis_session(
        session_id=session_id,
        topic="AI Robotics",
        research=ResearchOutput(topic="AI Robotics", sources=sources),
        analysis=MarketAnalysisOutput(),
        opportunities=[],
        sources=sources,
    )

    conn = isolated_db.get_connection()
    rows = conn.execute("SELECT * FROM sources WHERE session_id = ? ORDER BY rowid ASC", (session_id,)).fetchall()
    assert len(rows) == 2
    assert rows[0]["title"] == "Robotics Market Report"
    assert rows[0]["url"] == "https://example.com/robotics"
    assert rows[0]["session_id"] == session_id
    assert rows[1]["title"] == "AI Factory News"


# ---------------------------------------------------------------------------
# Test 4: Save report
# ---------------------------------------------------------------------------
def test_save_report(isolated_db):
    """Verify research and analysis structured report is stored as valid JSON."""
    session_id = "test_session_003"
    research = ResearchOutput(topic="AI Health", trends=["Wearable ECG", "AI Diagnostics"], problems=["Data privacy"])
    analysis = MarketAnalysisOutput(customer_segments=["Hospitals", "Clinics"], market_gaps=["Interoperability"])

    isolated_db.save_analysis_session(
        session_id=session_id,
        topic="AI Health",
        research=research,
        analysis=analysis,
        opportunities=[],
    )

    conn = isolated_db.get_connection()
    row = conn.execute("SELECT * FROM reports WHERE session_id = ?", (session_id,)).fetchone()
    assert row is not None
    report_dict = json.loads(row["report_json"])
    assert "research" in report_dict
    assert "analysis" in report_dict
    assert "Wearable ECG" in report_dict["research"]["trends"]
    assert "Hospitals" in report_dict["analysis"]["customer_segments"]


# ---------------------------------------------------------------------------
# Test 5: Save opportunities
# ---------------------------------------------------------------------------
def test_save_opportunities(isolated_db):
    """Verify opportunity hypotheses with mvp_json metadata are saved."""
    session_id = "test_session_004"
    opps = [
        Opportunity(
            title="TeleHealth AI",
            problem="Doctor shortages in rural clinics",
            customer="Rural health networks",
            solution="Autonomous triaging assistant",
            why_now="5G expansion and relaxed telemedicine regulations",
            competitors=["Teladoc", "Amwell"],
            mvp_features=["Audio transcription", "Symptom checker", "EHR sync"],
            risks=["Regulatory compliance", "Misdiagnosis liability"],
            evidence=["High patient wait times", "Rural clinic closures"],
        )
    ]

    isolated_db.save_analysis_session(
        session_id=session_id,
        topic="Telehealth",
        research=ResearchOutput(topic="Telehealth"),
        analysis=MarketAnalysisOutput(),
        opportunities=opps,
    )

    conn = isolated_db.get_connection()
    row = conn.execute("SELECT * FROM opportunities WHERE session_id = ?", (session_id,)).fetchone()
    assert row is not None
    assert row["title"] == "TeleHealth AI"
    assert row["problem"] == "Doctor shortages in rural clinics"
    assert row["customer"] == "Rural health networks"
    assert row["solution"] == "Autonomous triaging assistant"

    mvp_meta = json.loads(row["mvp_json"])
    assert "Audio transcription" in mvp_meta["mvp_features"]
    assert "Teladoc" in mvp_meta["competitors"]
    assert mvp_meta["why_now"] == "5G expansion and relaxed telemedicine regulations"


# ---------------------------------------------------------------------------
# Test 6: POST /analyze persists data
# ---------------------------------------------------------------------------
def test_post_analyze_persists_data(isolated_db):
    """Verify successful POST /analyze triggers automatic persistence into SQLite."""
    mock_research_data = {
        "topic": "AI Fintech",
        "trends": ["Autonomous underwriting", "Fraud graph AI"],
        "startups": ["RiskShield", "FraudFlow"],
        "problems": ["High chargeback rates"],
        "market_signals": ["$200M VC funding in Q1"],
        "sources": [{"title": "Fintech Report", "url": "https://example.com/fintech", "source_type": "web"}],
    }
    mock_analysis_data = {
        "customer_segments": ["Mid-market banks"],
        "competitors": ["Legacy rule engines"],
        "market_gaps": ["Real-time transaction scoring"],
        "why_now": ["Instant payments adoption"],
        "market_signals": ["$200M VC funding in Q1"],
        "trends": ["Autonomous underwriting"],
        "problems": ["High chargeback rates"],
    }
    mock_opp_data = {
        "opportunities": [
            {
                "title": "RiskEngine AI",
                "problem": "Chargebacks",
                "customer": "Banks",
                "solution": "Graph ML scoring",
                "why_now": "Instant ACH",
                "competitors": ["Feedzai"],
                "mvp_features": ["Webhook ingestion", "Rule engine"],
                "risks": ["False positives"],
                "evidence": ["Chargebacks up 30%"],
            }
        ]
    }

    call_count = [0]
    def mock_gemini(prompt, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"research": mock_research_data, "analysis": mock_analysis_data}
        return mock_opp_data

    mock_sources = [
        {"title": "Fintech Report", "url": "https://example.com/fintech", "snippet": "Fintech trends", "source_type": "web"}
    ]

    with patch.object(GeminiService, "is_configured", return_value=True), \
         patch.object(GeminiService, "generate_json", side_effect=mock_gemini), \
         patch.object(TavilyService, "is_configured", return_value=True), \
         patch.object(TavilyService, "search", return_value=mock_sources):
        response = client.post("/analyze", json={"topic": "AI Fintech"})

    assert response.status_code == 200
    res_data = response.json()
    session_id = res_data["session_id"]

    # Verify session exists in DB
    session_in_db = isolated_db.get_session(session_id)
    assert session_in_db is not None
    assert session_in_db["topic"] == "AI Fintech"
    assert len(session_in_db["opportunities"]) == 1
    assert session_in_db["opportunities"][0]["title"] == "RiskEngine AI"
    assert len(session_in_db["sources"]) >= 1


# ---------------------------------------------------------------------------
# Test 7: GET /research
# ---------------------------------------------------------------------------
def test_get_research(isolated_db):
    """Verify GET /research returns list of recent sessions with counts."""
    # Seed two sessions
    for topic in ["AI Robotics", "AI Logistics"]:
        isolated_db.save_analysis_session(
            session_id=f"sess_{topic.replace(' ', '_')}",
            topic=topic,
            research=ResearchOutput(topic=topic, trends=["Trend 1"]),
            analysis=MarketAnalysisOutput(),
            opportunities=[
                Opportunity(title=f"Opp for {topic}", problem="P", customer="C", solution="S", why_now="W")
            ],
            sources=[ResearchSource(title=f"Source {topic}", url=f"https://example.com/{topic}")],
        )

    response = client.get("/research")
    assert response.status_code == 200
    sessions = response.json()
    assert isinstance(sessions, list)
    assert len(sessions) == 2

    first = sessions[0]
    assert "id" in first
    assert "topic" in first
    assert "created_at" in first
    assert "sources_count" in first
    assert "opportunities_count" in first
    assert first["opportunities_count"] == 1
    assert first["sources_count"] == 1


# ---------------------------------------------------------------------------
# Test 8: GET /research/{id}
# ---------------------------------------------------------------------------
def test_get_research_by_id(isolated_db):
    """Verify GET /research/{session_id} returns complete saved session matching AnalyzeResponse."""
    session_id = "session_lookup_001"
    topic = "AI Cybersecurity"

    isolated_db.save_analysis_session(
        session_id=session_id,
        topic=topic,
        research=ResearchOutput(
            topic=topic,
            trends=["Zero Trust AI"],
            startups=["CyberShield"],
            problems=["Ransomware dwell time"],
            sources=[ResearchSource(title="Cyber Report", url="https://example.com/cyber")],
        ),
        analysis=MarketAnalysisOutput(
            customer_segments=["Enterprise CISOs"],
            market_gaps=["Autonomous containment"],
            why_now=["Proliferation of AI-generated malware"],
        ),
        opportunities=[
            Opportunity(
                title="AutoContain AI",
                problem="Ransomware lateral movement",
                customer="Enterprise IT",
                solution="Real-time network micro-segmentation",
                why_now="API maturity in cloud firewalls",
                competitors=["Illumio", "CrowdStrike"],
                mvp_features=["eBPF packet tap", "Policy engine"],
                risks=["Network disruption"],
                evidence=["Breach reports show 48h dwell time"],
            )
        ],
    )

    # Valid session lookup
    response = client.get(f"/research/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["session_id"] == session_id
    assert data["topic"] == topic
    assert data["research"]["trends"] == ["Zero Trust AI"]
    assert data["analysis"]["market_gaps"] == ["Autonomous containment"]
    assert len(data["opportunities"]) == 1
    assert data["opportunities"][0]["title"] == "AutoContain AI"
    assert data["opportunities"][0]["competitors"] == ["Illumio", "CrowdStrike"]

    # Non-existent session lookup
    response_404 = client.get("/research/non_existent_id")
    assert response_404.status_code == 404
    assert response_404.json()["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# Test 9: DELETE /research/{id}
# ---------------------------------------------------------------------------
def test_delete_research_by_id(isolated_db):
    """Verify DELETE /research/{session_id} safely removes session and cascaded rows."""
    session_id = "session_to_delete_001"
    isolated_db.save_analysis_session(
        session_id=session_id,
        topic="AI Education",
        research=ResearchOutput(topic="AI Education"),
        analysis=MarketAnalysisOutput(),
        opportunities=[
            Opportunity(title="TutorBot", problem="P", customer="C", solution="S", why_now="W")
        ],
        sources=[ResearchSource(title="Edu Trends", url="https://example.com/edu")],
    )

    # Ensure it exists
    assert isolated_db.session_exists(session_id) is True

    # Delete session
    response = client.delete(f"/research/{session_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Session deleted successfully"

    # Confirm it is gone
    assert isolated_db.session_exists(session_id) is False
    conn = isolated_db.get_connection()
    assert conn.execute("SELECT COUNT(*) as c FROM sources WHERE session_id = ?", (session_id,)).fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) as c FROM reports WHERE session_id = ?", (session_id,)).fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) as c FROM opportunities WHERE session_id = ?", (session_id,)).fetchone()["c"] == 0

    # GET should now return 404
    get_res = client.get(f"/research/{session_id}")
    assert get_res.status_code == 404

    # Second DELETE on already deleted session returns 404
    delete_again = client.delete(f"/research/{session_id}")
    assert delete_again.status_code == 404


# ---------------------------------------------------------------------------
# Test 10: Failed AI request is not persisted
# ---------------------------------------------------------------------------
def test_failed_ai_request_not_persisted(isolated_db):
    """Verify that when AI service fails during /analyze, no session is saved to SQLite."""
    with patch.object(GeminiService, "is_configured", return_value=True), \
         patch.object(GeminiService, "generate_json", side_effect=GeminiServiceError("API quota exhausted")), \
         patch.object(TavilyService, "is_configured", return_value=True), \
         patch.object(TavilyService, "search", return_value=[{"title": "T", "url": "https://t.com"}]):
        response = client.post("/analyze", json={"topic": "Failed AI Test"})

    assert response.status_code == 500

    # Ensure database remains completely empty (no partial or fake sessions)
    conn = isolated_db.get_connection()
    assert conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) as c FROM reports").fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) as c FROM sources").fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) as c FROM opportunities").fetchone()["c"] == 0
