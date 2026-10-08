# Database Specification — StartupLens AI

StartupLens AI uses **SQLite** for zero-configuration, robust relational persistence. This document describes the currently implemented database schema alongside planned schema extensions for future multi-agent and automation phases.

- **Engine:** SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode = WAL;`)
- **Integrity:** Enforced foreign key constraints (`PRAGMA foreign_keys = ON;`)
- **Default Database Location:** `./startuplens.db` (configurable via `DATABASE_URL` in `.env`)

---

## 1. Implemented Database Schema (Current MVP)

The current implementation utilizes 4 normalized tables with cascading referential integrity, managed via `backend/database/db.py`:

```text
               ┌───────────────────────┐
               │       sessions        │
               │  id (PK)              │
               │  topic                │
               │  created_at           │
               │  updated_at           │
               └──────────┬────────────┘
                          │ 1
                          │
          ┌───────────────┼───────────────┐
          │ *             │ *             │ *
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │   sources   │ │   reports   │ │opportunities│
   │ id (PK)     │ │ id (PK)     │ │ id (PK)     │
   │ session_id  │ │ session_id  │ │ session_id  │
   │ title, url  │ │ report_json │ │ title, mvp..│
   └─────────────┘ └─────────────┘ └─────────────┘
```

### 1.1 `sessions` Table
Stores high-level metadata for each research run.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `TEXT` | `PRIMARY KEY` | Unique session identifier (e.g., `session_a1b2c3d4e5f6`) |
| `topic` | `TEXT` | `NOT NULL` | The user query or industry analyzed |
| `created_at` | `TEXT` | `NOT NULL` | ISO 8601 UTC creation timestamp |
| `updated_at` | `TEXT` | `NOT NULL` | ISO 8601 UTC last-modified timestamp |

---

### 1.2 `sources` Table
Maintains verifiable web citations discovered by the research agent.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `TEXT` | `PRIMARY KEY` | Unique source record ID (e.g., `src_...`) |
| `session_id` | `TEXT` | `NOT NULL, FK` | References `sessions(id)` with `ON DELETE CASCADE` |
| `title` | `TEXT` | `NOT NULL` | Page or article title returned by Tavily |
| `url` | `TEXT` | `NOT NULL` | Target web URL |
| `published_at`| `TEXT` | `NULLABLE` | Source publication date if available |
| `source_type` | `TEXT` | `DEFAULT 'web'` | Classification (e.g., `'web'`, `'news'`, `'official_company'`) |
| `retrieved_at`| `TEXT` | `NULLABLE` | ISO 8601 UTC timestamp when source was collected |

---

### 1.3 `reports` Table
Stores the complete consolidated research and market intelligence payload.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `TEXT` | `PRIMARY KEY` | Unique report record ID (e.g., `rep_...`) |
| `session_id` | `TEXT` | `NOT NULL, FK` | References `sessions(id)` with `ON DELETE CASCADE` |
| `report_json` | `TEXT` | `NOT NULL` | JSON blob containing research extraction and market analysis |

---

### 1.4 `opportunities` Table
Stores individual venture opportunity hypotheses linked to the session.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `TEXT` | `PRIMARY KEY` | Unique opportunity ID (e.g., `opp_...`) |
| `session_id` | `TEXT` | `NOT NULL, FK` | References `sessions(id)` with `ON DELETE CASCADE` |
| `title` | `TEXT` | `NOT NULL` | Opportunity concept title |
| `problem` | `TEXT` | `NOT NULL` | Specific customer pain point |
| `customer` | `TEXT` | `NOT NULL` | Target buyer / customer segment |
| `solution` | `TEXT` | `NOT NULL` | Proposed solution hypothesis |
| `mvp_json` | `TEXT` | `NOT NULL` | JSON blob storing `why_now`, `competitors`, `mvp_features`, `risks`, and `evidence` |

---

### 1.5 Active Indexes
- `CREATE INDEX IF NOT EXISTS idx_sources_session ON sources(session_id);`
- `CREATE INDEX IF NOT EXISTS idx_reports_session ON reports(session_id);`
- `CREATE INDEX IF NOT EXISTS idx_opps_session ON opportunities(session_id);`
- `CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at);`

---

## 2. Planned Schema Extensions (Future Phases)

The following tables are planned for future multi-model, validation, and automation features. **They are not yet created in the running SQLite database.**

### 2.1 `agent_runs` (Planned)
Tracks granular performance and token metrics across modular agent stages.
```sql
CREATE TABLE agent_runs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,          -- e.g., 'Market Intelligence Agent'
    model_identifier TEXT NOT NULL,    -- e.g., 'gemini-3.5-flash'
    duration_ms INTEGER NOT NULL,
    status TEXT NOT NULL,              -- 'success' | 'failure'
    error_message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
```

### 2.2 `opportunity_scores` (Planned)
Stores multi-dimensional validation scores computed by the Opportunity Validation Agent.
```sql
CREATE TABLE opportunity_scores (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    market_demand INTEGER NOT NULL,
    competitive_pressure INTEGER NOT NULL,
    execution_feasibility INTEGER NOT NULL,
    market_timing INTEGER NOT NULL,
    ai_advantage INTEGER NOT NULL,
    overall_confidence TEXT NOT NULL,
    rationale_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
);
```

### 2.3 `watchlists` (Planned)
Stores topics enrolled in scheduled research tracking.
```sql
CREATE TABLE watchlists (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL UNIQUE,
    frequency TEXT NOT NULL,           -- 'daily' | 'weekly'
    last_run_at TEXT,
    next_run_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);
```

### 2.4 `signals` (Planned)
Records detected changes and new signals over time for tracked topics.
```sql
CREATE TABLE signals (
    id TEXT PRIMARY KEY,
    watchlist_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    signal_type TEXT NOT NULL,         -- 'new_competitor' | 'regulatory_shift' | 'funding'
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
```

### 2.5 `automation_jobs` (Planned)
Maintains audit logs for scheduled automation runs.
```sql
CREATE TABLE automation_jobs (
    id TEXT PRIMARY KEY,
    watchlist_id TEXT NOT NULL,
    job_type TEXT NOT NULL,            -- 'scheduled_refresh' | 'weekly_brief'
    status TEXT NOT NULL,              -- 'completed' | 'failed' | 'skipped_no_change'
    summary_text TEXT,
    executed_at TEXT NOT NULL,
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
);
```
