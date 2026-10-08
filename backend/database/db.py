import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.config import settings
from backend.schemas.research import ResearchOutput, ResearchSource
from backend.schemas.analysis import MarketAnalysisOutput
from backend.schemas.opportunity import Opportunity

logger = logging.getLogger(__name__)


def resolve_db_path(database_url: Optional[str] = None) -> str:
    """Resolve sqlite URL to absolute or relative file path."""
    url = database_url or settings.DATABASE_URL
    if not url:
        url = "sqlite:///./startuplens.db"

    if url.startswith("sqlite:///"):
        path_str = url[10:]
    elif url.startswith("sqlite://"):
        path_str = url[9:]
    else:
        path_str = url

    if path_str == ":memory:":
        return ":memory:"

    p = Path(path_str)
    if not p.is_absolute():
        # Anchor relative paths to the workspace root
        base_dir = Path(__file__).resolve().parent.parent.parent
        p = base_dir / path_str

    # Ensure parent directory exists
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


class DatabaseManager:
    """
    SQLite persistence layer for StartupLens AI.
    Implements tables defined in DATABASE.md:
      - sessions
      - sources
      - reports
      - opportunities
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path if db_path is not None else resolve_db_path()
        self._is_memory = (self.db_path == ":memory:")
        self._memory_conn: Optional[sqlite3.Connection] = None
        logger.info(f"DatabaseManager initialized with path: {self.db_path}")

    def get_connection(self) -> sqlite3.Connection:
        """
        Create a connection to the SQLite database.
        For :memory: databases, keep a persistent connection to retain data across calls.
        """
        if self._is_memory:
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_conn.row_factory = sqlite3.Row
                self._memory_conn.execute("PRAGMA foreign_keys = ON;")
            return self._memory_conn

        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
        except Exception:
            pass
        return conn

    def init_db(self) -> None:
        """Create tables and indices if they do not exist."""
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        topic TEXT NOT NULL,
                        model_used TEXT DEFAULT 'gemini-3.8-flash',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS sources (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        url TEXT NOT NULL,
                        published_at TEXT,
                        source_type TEXT DEFAULT 'web',
                        retrieved_at TEXT,
                        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS reports (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        report_json TEXT NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS opportunities (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        problem TEXT NOT NULL,
                        customer TEXT NOT NULL,
                        solution TEXT NOT NULL,
                        mvp_json TEXT NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        content_text TEXT NOT NULL,
                        sections_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS saved_ideas (
                        id TEXT PRIMARY KEY,
                        opportunity_title TEXT NOT NULL,
                        session_id TEXT,
                        topic TEXT,
                        opportunity_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS research_trackers (
                        id TEXT PRIMARY KEY,
                        topic TEXT NOT NULL UNIQUE,
                        status TEXT NOT NULL DEFAULT 'active',
                        last_updated TEXT NOT NULL,
                        next_update TEXT NOT NULL,
                        session_id TEXT,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS market_signals (
                        id TEXT PRIMARY KEY,
                        tracker_id TEXT,
                        topic TEXT NOT NULL,
                        title TEXT NOT NULL,
                        what_changed TEXT NOT NULL,
                        evidence TEXT NOT NULL,
                        detected_at TEXT NOT NULL,
                        FOREIGN KEY (tracker_id) REFERENCES research_trackers(id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS opportunity_scores (
                        id TEXT PRIMARY KEY,
                        opportunity_id TEXT,
                        title TEXT NOT NULL,
                        market_demand INTEGER NOT NULL,
                        competitive_pressure INTEGER NOT NULL,
                        execution_feasibility INTEGER NOT NULL,
                        market_timing INTEGER NOT NULL,
                        ai_advantage INTEGER NOT NULL,
                        overall_score INTEGER NOT NULL,
                        confidence_label TEXT NOT NULL,
                        rationale TEXT,
                        scored_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS weekly_reports (
                        id TEXT PRIMARY KEY,
                        week_start TEXT NOT NULL,
                        week_end TEXT NOT NULL,
                        title TEXT NOT NULL,
                        report_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_sources_session ON sources(session_id);
                    CREATE INDEX IF NOT EXISTS idx_reports_session ON reports(session_id);
                    CREATE INDEX IF NOT EXISTS idx_opps_session ON opportunities(session_id);
                    CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at);
                    CREATE INDEX IF NOT EXISTS idx_saved_ideas_created ON saved_ideas(created_at);
                    CREATE INDEX IF NOT EXISTS idx_trackers_topic ON research_trackers(topic);
                    CREATE INDEX IF NOT EXISTS idx_signals_tracker ON market_signals(tracker_id);
                    """
                )
                try:
                    conn.execute("ALTER TABLE sources ADD COLUMN retrieved_at TEXT;")
                except Exception:
                    pass
                try:
                    conn.execute("ALTER TABLE sessions ADD COLUMN model_used TEXT DEFAULT 'gemini-3.8-flash';")
                except Exception:
                    pass
            logger.info("Database schema initialized successfully.")
        finally:
            if not self._is_memory:
                conn.close()

    def save_analysis_session(
        self,
        session_id: str,
        topic: str,
        research: Union[ResearchOutput, Dict[str, Any]],
        analysis: Union[MarketAnalysisOutput, Dict[str, Any]],
        opportunities: List[Union[Opportunity, Dict[str, Any]]],
        sources: Optional[List[Union[ResearchSource, Dict[str, Any]]]] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        model_used: Optional[str] = None,
    ) -> str:
        """
        Persist a complete research and opportunity analysis session atomically.
        """
        now = datetime.now(timezone.utc).isoformat()
        c_at = created_at or now
        u_at = updated_at or now

        # Convert schemas to dicts/json
        research_dict = research.model_dump() if hasattr(research, "model_dump") else dict(research)
        analysis_dict = analysis.model_dump() if hasattr(analysis, "model_dump") else dict(analysis)

        # Sources list
        raw_sources = sources if sources is not None else research_dict.get("sources", [])
        norm_sources: List[Dict[str, Any]] = []
        for s in raw_sources:
            if hasattr(s, "model_dump"):
                norm_sources.append(s.model_dump())
            elif isinstance(s, dict):
                norm_sources.append(s)

        # Report JSON combining research and analysis
        report_data = {
            "research": research_dict,
            "analysis": analysis_dict,
        }
        report_json = json.dumps(report_data, ensure_ascii=False)

        conn = self.get_connection()
        try:
            with conn:
                # 1. Insert session
                conn.execute(
                    """
                    INSERT INTO sessions (id, topic, model_used, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, topic, model_used or settings.GEMINI_MODEL, c_at, u_at),
                )

                # 2. Insert sources
                for s in norm_sources:
                    src_id = f"src_{uuid.uuid4().hex[:12]}"
                    conn.execute(
                        """
                        INSERT INTO sources (id, session_id, title, url, published_at, source_type, retrieved_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            src_id,
                            session_id,
                            s.get("title", ""),
                            s.get("url", ""),
                            s.get("published_at"),
                            s.get("source_type", "web"),
                            s.get("retrieved_at") or now,
                        ),
                    )

                # 3. Insert report
                report_id = f"rep_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO reports (id, session_id, report_json)
                    VALUES (?, ?, ?)
                    """,
                    (report_id, session_id, report_json),
                )

                # 4. Insert opportunities
                for opp in opportunities:
                    opp_dict = opp.model_dump() if hasattr(opp, "model_dump") else dict(opp)
                    opp_id = f"opp_{uuid.uuid4().hex[:12]}"

                    mvp_payload = {
                        "why_now": opp_dict.get("why_now", ""),
                        "competitors": opp_dict.get("competitors", []),
                        "mvp_features": opp_dict.get("mvp_features", []),
                        "risks": opp_dict.get("risks", []),
                        "evidence": opp_dict.get("evidence", []),
                    }

                    conn.execute(
                        """
                        INSERT INTO opportunities (
                            id, session_id, title, problem, customer, solution, mvp_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            opp_id,
                            session_id,
                            opp_dict.get("title", ""),
                            opp_dict.get("problem", ""),
                            opp_dict.get("customer", ""),
                            opp_dict.get("solution", ""),
                            json.dumps(mvp_payload, ensure_ascii=False),
                        ),
                    )

            logger.info(f"Persisted session [{session_id}] for topic '{topic}' to SQLite.")
            return session_id
        finally:
            if not self._is_memory:
                conn.close()

    def get_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Return list of recent sessions with counts.
        """
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT 
                    s.id,
                    s.topic,
                    s.created_at,
                    s.updated_at,
                    COUNT(DISTINCT src.id) as sources_count,
                    COUNT(DISTINCT o.id) as opportunities_count
                FROM sessions s
                LEFT JOIN sources src ON s.id = src.session_id
                LEFT JOIN opportunities o ON s.id = o.session_id
                GROUP BY s.id
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append(
                    {
                        "id": row["id"],
                        "session_id": row["id"],
                        "topic": row["topic"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "sources_count": row["sources_count"],
                        "opportunities_count": row["opportunities_count"],
                    }
                )
            return results
        finally:
            if not self._is_memory:
                conn.close()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete saved research session matching AnalyzeResponse schema.
        """
        conn = self.get_connection()
        try:
            # 1. Fetch session
            cur = conn.execute(
                "SELECT id, topic, created_at, updated_at FROM sessions WHERE id = ?",
                (session_id,),
            )
            session_row = cur.fetchone()
            if not session_row:
                return None

            # 2. Fetch report
            cur = conn.execute(
                "SELECT report_json FROM reports WHERE session_id = ? LIMIT 1",
                (session_id,),
            )
            report_row = cur.fetchone()
            report_data: Dict[str, Any] = {}
            if report_row and report_row["report_json"]:
                try:
                    report_data = json.loads(report_row["report_json"])
                except Exception as e:
                    logger.warning(f"Failed to parse report_json for session {session_id}: {e}")

            # 3. Fetch sources
            cur = conn.execute(
                """
                SELECT id, title, url, published_at, source_type, retrieved_at
                FROM sources
                WHERE session_id = ?
                ORDER BY rowid ASC
                """,
                (session_id,),
            )
            source_rows = cur.fetchall()
            sources_list: List[Dict[str, Any]] = []
            for r in source_rows:
                sources_list.append(
                    {
                        "title": r["title"],
                        "url": r["url"],
                        "published_at": r["published_at"],
                        "source_type": r["source_type"] or "web",
                        "retrieved_at": r["retrieved_at"] if "retrieved_at" in r.keys() else None,
                        "snippet": None,
                    }
                )

            # 4. Fetch opportunities
            cur = conn.execute(
                """
                SELECT id, title, problem, customer, solution, mvp_json
                FROM opportunities
                WHERE session_id = ?
                ORDER BY rowid ASC
                """,
                (session_id,),
            )
            opp_rows = cur.fetchall()
            opps_list: List[Dict[str, Any]] = []
            for r in opp_rows:
                mvp_meta: Dict[str, Any] = {}
                if r["mvp_json"]:
                    try:
                        mvp_meta = json.loads(r["mvp_json"])
                    except Exception:
                        pass

                opps_list.append(
                    {
                        "title": r["title"],
                        "problem": r["problem"],
                        "customer": r["customer"],
                        "solution": r["solution"],
                        "why_now": mvp_meta.get("why_now", ""),
                        "competitors": mvp_meta.get("competitors", []),
                        "mvp_features": mvp_meta.get("mvp_features", []),
                        "risks": mvp_meta.get("risks", []),
                        "evidence": mvp_meta.get("evidence", []),
                    }
                )

            # Extract research and analysis
            research_part = report_data.get("research", {})
            if not research_part.get("sources") and sources_list:
                research_part["sources"] = sources_list
            research_part["topic"] = session_row["topic"]

            analysis_part = report_data.get("analysis", {})

            retrieved_at = (
                research_part.get("retrieved_at")
                or (sources_list[0].get("retrieved_at") if sources_list else None)
                or session_row["created_at"]
            )
            disclaimer = f"Based on web sources retrieved on {retrieved_at}." if retrieved_at else None

            return {
                "id": session_row["id"],
                "session_id": session_row["id"],
                "topic": session_row["topic"],
                "created_at": session_row["created_at"],
                "updated_at": session_row["updated_at"],
                "retrieved_at": retrieved_at,
                "research_disclaimer": disclaimer,
                "research": research_part,
                "analysis": analysis_part,
                "opportunities": opps_list,
                "sources": sources_list,
            }
        finally:
            if not self._is_memory:
                conn.close()

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its associated data (sources, reports, opportunities).
        Returns True if deleted, False if session does not exist.
        """
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
                if not cur.fetchone():
                    return False

                # Cascading delete
                conn.execute("DELETE FROM sources WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM reports WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM opportunities WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

            logger.info(f"Deleted session [{session_id}] and related data from database.")
            return True
        finally:
            if not self._is_memory:
                conn.close()

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists by ID."""
        conn = self.get_connection()
        try:
            cur = conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,))
            return cur.fetchone() is not None
        finally:
            if not self._is_memory:
                conn.close()

    # ── Documents ─────────────────────────────────────────────────────────────
    def save_document(self, doc: Dict[str, Any]) -> str:
        """Persist a parsed document with sections."""
        conn = self.get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO documents (id, filename, file_type, file_size, content_text, sections_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc["id"],
                        doc["filename"],
                        doc["file_type"],
                        doc["file_size"],
                        doc["content_text"],
                        json.dumps(doc.get("sections", []), ensure_ascii=False),
                        doc["created_at"],
                    ),
                )
            return doc["id"]
        finally:
            if not self._is_memory:
                conn.close()

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        conn = self.get_connection()
        try:
            cur = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "filename": row["filename"],
                "file_type": row["file_type"],
                "file_size": row["file_size"],
                "content_text": row["content_text"],
                "sections": json.loads(row["sections_json"]),
                "created_at": row["created_at"],
            }
        finally:
            if not self._is_memory:
                conn.close()

    def get_documents(self, doc_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Retrieve documents by list of IDs or all documents."""
        conn = self.get_connection()
        try:
            if doc_ids:
                placeholders = ",".join("?" for _ in doc_ids)
                cur = conn.execute(f"SELECT * FROM documents WHERE id IN ({placeholders})", tuple(doc_ids))
            else:
                cur = conn.execute("SELECT * FROM documents ORDER BY created_at DESC")
            docs = []
            for row in cur.fetchall():
                docs.append(
                    {
                        "id": row["id"],
                        "filename": row["filename"],
                        "file_type": row["file_type"],
                        "file_size": row["file_size"],
                        "content_text": row["content_text"],
                        "sections": json.loads(row["sections_json"]),
                        "created_at": row["created_at"],
                    }
                )
            return docs
        finally:
            if not self._is_memory:
                conn.close()

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                return cur.rowcount > 0
        finally:
            if not self._is_memory:
                conn.close()

    # ── Saved Ideas ───────────────────────────────────────────────────────────
    def save_idea(
        self,
        opportunity: Dict[str, Any],
        session_id: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save an opportunity idea to SQLite."""
        title = opportunity.get("title", "Untitled Opportunity")
        now_iso = datetime.now(timezone.utc).isoformat()
        idea_id = f"idea_{uuid.uuid4().hex[:12]}"

        conn = self.get_connection()
        try:
            with conn:
                # Check if already saved by title
                cur = conn.execute("SELECT id FROM saved_ideas WHERE opportunity_title = ?", (title,))
                existing = cur.fetchone()
                if existing:
                    idea_id = existing["id"]
                    conn.execute(
                        """
                        UPDATE saved_ideas
                        SET opportunity_json = ?, session_id = ?, topic = ?
                        WHERE id = ?
                        """,
                        (json.dumps(opportunity, ensure_ascii=False), session_id, topic, idea_id),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO saved_ideas (id, opportunity_title, session_id, topic, opportunity_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (idea_id, title, session_id, topic, json.dumps(opportunity, ensure_ascii=False), now_iso),
                    )
            return {
                "id": idea_id,
                "opportunity_title": title,
                "session_id": session_id,
                "topic": topic,
                "opportunity": opportunity,
                "created_at": now_iso,
            }
        finally:
            if not self._is_memory:
                conn.close()

    def get_saved_ideas(self) -> List[Dict[str, Any]]:
        """Retrieve all saved opportunity ideas."""
        conn = self.get_connection()
        try:
            cur = conn.execute("SELECT * FROM saved_ideas ORDER BY created_at DESC")
            ideas = []
            for row in cur.fetchall():
                ideas.append(
                    {
                        "id": row["id"],
                        "opportunity_title": row["opportunity_title"],
                        "session_id": row["session_id"],
                        "topic": row["topic"],
                        "opportunity": json.loads(row["opportunity_json"]),
                        "created_at": row["created_at"],
                    }
                )
            return ideas
        finally:
            if not self._is_memory:
                conn.close()

    def delete_saved_idea(self, idea_id_or_title: str) -> bool:
        """Delete a saved opportunity idea by ID or title."""
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.execute(
                    "DELETE FROM saved_ideas WHERE id = ? OR opportunity_title = ?",
                    (idea_id_or_title, idea_id_or_title),
                )
                return cur.rowcount > 0
        finally:
            if not self._is_memory:
                conn.close()

    # ── Research Trackers ─────────────────────────────────────────────────────
    def save_tracker(
        self,
        topic: str,
        session_id: Optional[str] = None,
        status: str = "active",
    ) -> Dict[str, Any]:
        """Create or update a tracked research topic."""
        now_iso = datetime.now(timezone.utc).isoformat()
        # Next update is tomorrow
        next_iso = datetime.now(timezone.utc).strftime("%d %b %Y · Next update: Tomorrow")
        last_iso = datetime.now(timezone.utc).strftime("%d %b %Y")
        tracker_id = f"trk_{uuid.uuid4().hex[:12]}"

        conn = self.get_connection()
        try:
            with conn:
                cur = conn.execute("SELECT * FROM research_trackers WHERE topic = ?", (topic.strip(),))
                existing = cur.fetchone()
                if existing:
                    tracker_id = existing["id"]
                    conn.execute(
                        """
                        UPDATE research_trackers
                        SET status = ?, last_updated = ?, next_update = ?, session_id = ?
                        WHERE id = ?
                        """,
                        (status, last_iso, next_iso, session_id or existing["session_id"], tracker_id),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO research_trackers (id, topic, status, last_updated, next_update, session_id, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (tracker_id, topic.strip(), status, last_iso, next_iso, session_id, now_iso),
                    )
            return {
                "id": tracker_id,
                "topic": topic.strip(),
                "status": status,
                "last_updated": last_iso,
                "next_update": next_iso,
                "session_id": session_id,
                "created_at": now_iso,
            }
        finally:
            if not self._is_memory:
                conn.close()

    def get_trackers(self) -> List[Dict[str, Any]]:
        """List all research trackers."""
        conn = self.get_connection()
        try:
            cur = conn.execute("SELECT * FROM research_trackers ORDER BY created_at DESC")
            trackers = []
            for row in cur.fetchall():
                trackers.append(
                    {
                        "id": row["id"],
                        "topic": row["topic"],
                        "status": row["status"],
                        "last_updated": row["last_updated"],
                        "next_update": row["next_update"],
                        "session_id": row["session_id"],
                        "created_at": row["created_at"],
                    }
                )
            return trackers
        finally:
            if not self._is_memory:
                conn.close()

    def get_tracker_by_id(self, tracker_id: str) -> Optional[Dict[str, Any]]:
        """Get a single tracker by ID."""
        conn = self.get_connection()
        try:
            cur = conn.execute("SELECT * FROM research_trackers WHERE id = ?", (tracker_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "topic": row["topic"],
                "status": row["status"],
                "last_updated": row["last_updated"],
                "next_update": row["next_update"],
                "session_id": row["session_id"],
                "created_at": row["created_at"],
            }
        finally:
            if not self._is_memory:
                conn.close()

    def get_tracker_by_topic(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get a single tracker by topic name."""
        conn = self.get_connection()
        try:
            cur = conn.execute("SELECT * FROM research_trackers WHERE topic = ?", (topic.strip(),))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "topic": row["topic"],
                "status": row["status"],
                "last_updated": row["last_updated"],
                "next_update": row["next_update"],
                "session_id": row["session_id"],
                "created_at": row["created_at"],
            }
        finally:
            if not self._is_memory:
                conn.close()

    def delete_tracker(self, tracker_id: str) -> bool:
        """Delete a research tracker and its signals."""
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM market_signals WHERE tracker_id = ?", (tracker_id,))
                cur = conn.execute("DELETE FROM research_trackers WHERE id = ?", (tracker_id,))
                return cur.rowcount > 0
        finally:
            if not self._is_memory:
                conn.close()

    # ── Market Signals ────────────────────────────────────────────────────────
    def save_market_signal(
        self,
        topic: str,
        title: str,
        what_changed: str,
        evidence: str,
        tracker_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save a detected market change signal."""
        sig_id = f"sig_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO market_signals (id, tracker_id, topic, title, what_changed, evidence, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (sig_id, tracker_id, topic, title, what_changed, evidence, now_iso),
                )
            return {
                "id": sig_id,
                "tracker_id": tracker_id,
                "topic": topic,
                "title": title,
                "what_changed": what_changed,
                "evidence": evidence,
                "detected_at": now_iso,
            }
        finally:
            if not self._is_memory:
                conn.close()

    def get_market_signals(
        self,
        tracker_id: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve market signals optionally filtered by tracker or topic."""
        conn = self.get_connection()
        try:
            if tracker_id:
                cur = conn.execute(
                    "SELECT * FROM market_signals WHERE tracker_id = ? ORDER BY detected_at DESC LIMIT ?",
                    (tracker_id, limit),
                )
            elif topic:
                cur = conn.execute(
                    "SELECT * FROM market_signals WHERE topic = ? ORDER BY detected_at DESC LIMIT ?",
                    (topic, limit),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM market_signals ORDER BY detected_at DESC LIMIT ?",
                    (limit,),
                )
            signals = []
            for row in cur.fetchall():
                signals.append(
                    {
                        "id": row["id"],
                        "tracker_id": row["tracker_id"],
                        "topic": row["topic"],
                        "title": row["title"],
                        "what_changed": row["what_changed"],
                        "evidence": row["evidence"],
                        "detected_at": row["detected_at"],
                    }
                )
            return signals
        finally:
            if not self._is_memory:
                conn.close()

    # ── Opportunity Scores ────────────────────────────────────────────────────
    def save_opportunity_score(
        self,
        title: str,
        market_demand: int,
        competitive_pressure: int,
        execution_feasibility: int,
        market_timing: int,
        ai_advantage: int,
        overall_score: int,
        confidence_label: str,
        rationale: str = "",
        opportunity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist validation scoring for an opportunity."""
        score_id = f"score_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO opportunity_scores (
                        id, opportunity_id, title, market_demand, competitive_pressure,
                        execution_feasibility, market_timing, ai_advantage, overall_score,
                        confidence_label, rationale, scored_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        score_id,
                        opportunity_id,
                        title,
                        market_demand,
                        competitive_pressure,
                        execution_feasibility,
                        market_timing,
                        ai_advantage,
                        overall_score,
                        confidence_label,
                        rationale,
                        now_iso,
                    ),
                )
            return {
                "id": score_id,
                "opportunity_id": opportunity_id,
                "title": title,
                "market_demand": market_demand,
                "competitive_pressure": competitive_pressure,
                "execution_feasibility": execution_feasibility,
                "market_timing": market_timing,
                "ai_advantage": ai_advantage,
                "overall_score": overall_score,
                "confidence_label": confidence_label,
                "rationale": rationale,
                "scored_at": now_iso,
            }
        finally:
            if not self._is_memory:
                conn.close()

    def get_opportunity_score_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Retrieve most recent opportunity score by opportunity title."""
        conn = self.get_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM opportunity_scores WHERE title = ? ORDER BY scored_at DESC LIMIT 1",
                (title,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "opportunity_id": row["opportunity_id"],
                "title": row["title"],
                "market_demand": row["market_demand"],
                "competitive_pressure": row["competitive_pressure"],
                "execution_feasibility": row["execution_feasibility"],
                "market_timing": row["market_timing"],
                "ai_advantage": row["ai_advantage"],
                "overall_score": row["overall_score"],
                "confidence_label": row["confidence_label"],
                "rationale": row["rationale"],
                "scored_at": row["scored_at"],
            }
        finally:
            if not self._is_memory:
                conn.close()

    # ── Weekly Reports ────────────────────────────────────────────────────────
    def save_weekly_report(
        self,
        title: str,
        week_start: str,
        week_end: str,
        report_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Persist a weekly intelligence report."""
        rep_id = f"wrep_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO weekly_reports (id, week_start, week_end, title, report_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (rep_id, week_start, week_end, title, json.dumps(report_data, ensure_ascii=False), now_iso),
                )
            return {
                "id": rep_id,
                "week_start": week_start,
                "week_end": week_end,
                "title": title,
                "report": report_data,
                "created_at": now_iso,
            }
        finally:
            if not self._is_memory:
                conn.close()

    def get_weekly_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent weekly intelligence reports."""
        conn = self.get_connection()
        try:
            cur = conn.execute("SELECT * FROM weekly_reports ORDER BY created_at DESC LIMIT ?", (limit,))
            reports = []
            for row in cur.fetchall():
                reports.append(
                    {
                        "id": row["id"],
                        "week_start": row["week_start"],
                        "week_end": row["week_end"],
                        "title": row["title"],
                        "report": json.loads(row["report_json"]),
                        "created_at": row["created_at"],
                    }
                )
            return reports
        finally:
            if not self._is_memory:
                conn.close()


# Default singleton instance
db = DatabaseManager()
