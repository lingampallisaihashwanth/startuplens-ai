# API Specification — StartupLens AI

This document specifies the REST API endpoints of the StartupLens AI backend.

- **Development Base URL:** `http://127.0.0.1:8003`
- **Interactive OpenAPI Documentation:** `http://127.0.0.1:8003/docs`
- **OpenAPI JSON Specification:** `http://127.0.0.1:8003/openapi.json`
- **Default Port:** `8003` (to avoid collision with local web proxies)

---

## 1. Implemented Endpoints

### 1.1 Root Health Check
- **Method:** `GET`
- **Path:** `/`
- **Description:** Basic service availability confirmation.
- **Status:** **IMPLEMENTED**
- **Response (200 OK):**
```json
{
  "message": "StartupLens AI API is running"
}
```

---

### 1.2 System Health Check
- **Method:** `GET`
- **Path:** `/health`
- **Description:** Structured service health status check.
- **Status:** **IMPLEMENTED**
- **Response (200 OK):**
```json
{
  "status": "ok",
  "service": "StartupLens AI API",
  "message": "StartupLens AI API is running"
}
```

---

### 1.3 Configuration & Key Status
- **Method:** `GET`
- **Path:** `/config/status`
- **Description:** Verifies that external service credentials (Gemini, Tavily) are loaded without leaking secret keys.
- **Status:** **IMPLEMENTED**
- **Response (200 OK):**
```json
{
  "status": "ready",
  "keys": {
    "gemini_configured": true,
    "tavily_configured": true
  },
  "llm_provider": "Google Gemini",
  "model": "gemini-3.5-flash",
  "search_provider": "Tavily"
}
```

---

### 1.4 Execute Research Pipeline
- **Method:** `POST`
- **Path:** `/analyze`
- **Description:** Triggers the end-to-end research, market analysis, and startup opportunity generation pipeline.
- **Status:** **IMPLEMENTED**
- **Request Body:**
```json
{
  "topic": "AI Robotics"
}
```
*Validation:* `topic` must contain at least 2 non-whitespace characters.

- **Response (200 OK):**
```json
{
  "id": "session_a1b2c3d4e5f6",
  "session_id": "session_a1b2c3d4e5f6",
  "topic": "AI Robotics",
  "created_at": "2026-10-06T12:00:00Z",
  "updated_at": "2026-10-06T12:00:00Z",
  "retrieved_at": "2026-10-06T12:00:00Z",
  "research_disclaimer": "Based on web sources retrieved on 2026-10-06T12:00:00Z.",
  "research": {
    "topic": "AI Robotics",
    "trends": [
      "Humanoid robot dexterity powered by foundation models",
      "Low-cost tactile sensing arrays"
    ],
    "startups": [
      "Figure AI",
      "Apptronik"
    ],
    "problems": [
      "High hardware maintenance and calibration overhead",
      "Generalization failure in unstructured physical environments"
    ],
    "market_signals": [
      "$675M Series B funding in humanoid robotics",
      "Automotive manufacturing pilot deployments"
    ],
    "sources": [
      {
        "title": "State of Humanoid Robotics 2026",
        "url": "https://example.com/robotics-2026",
        "published_at": "2026-03-15",
        "snippet": "Venture funding in physical AI and robotics surged...",
        "source_type": "industry_publication",
        "retrieved_at": "2026-10-06T12:00:00Z",
        "freshness_label": "6 months ago",
        "is_historical": false
      }
    ]
  },
  "analysis": {
    "market_signals": [
      "Rapid decline in sensor and compute costs",
      "Industrial labor shortages driving automation demand"
    ],
    "customer_segments": [
      "Automotive OEMs",
      "3PL warehouse logistics operators"
    ],
    "competitors": [
      "Figure AI",
      "Boston Dynamics"
    ],
    "market_gaps": [
      "Plug-and-play visual teleoperation software for mixed fleets"
    ],
    "why_now": [
      "Convergence of vision-language-action (VLA) models and commoditized actuators"
    ]
  },
  "opportunities": [
    {
      "title": "FleetSynapse — Cross-Platform Robotics Teleoperation",
      "problem": "Robotics operators lack unified remote-intervention tools for diverse hardware.",
      "customer": "Warehouse automation engineering teams",
      "solution": "Web-based low-latency teleoperation and policy rollout platform.",
      "why_now": "Standardized WebRTC and WebGPU make low-latency robotic streaming viable in-browser.",
      "competitors": ["Formant", "InOrbit"],
      "mvp_features": [
        "WebRTC low-latency video feed integration",
        "Gamepad & keyboard control mapper",
        "ROS2 bridge connector",
        "Session event logging"
      ],
      "risks": [
        "Network latency edge cases causing physical safety stops",
        "Incumbent robot OEMs building proprietary portals"
      ],
      "evidence": [
        "Reported 40% downtime due to manual recovery interventions (Source: Robotics Today)"
      ]
    }
  ],
  "sources": [
    {
      "title": "State of Humanoid Robotics 2026",
      "url": "https://example.com/robotics-2026",
      "published_at": "2026-03-15",
      "snippet": "Venture funding in physical AI and robotics surged..."
    }
  ]
}
```

---

### 1.5 List Saved Research Sessions
- **Method:** `GET`
- **Path:** `/research`
- **Description:** Retrieves recent saved sessions with counts of sources and opportunities.
- **Status:** **IMPLEMENTED**
- **Query Parameters:**
  - `limit` *(int, default: 50)*
  - `offset` *(int, default: 0)*
- **Response (200 OK):**
```json
[
  {
    "id": "session_a1b2c3d4e5f6",
    "session_id": "session_a1b2c3d4e5f6",
    "topic": "AI Robotics",
    "created_at": "2026-10-06T12:00:00Z",
    "updated_at": "2026-10-06T12:00:00Z",
    "sources_count": 6,
    "opportunities_count": 3
  }
]
```
*(Note: `/sessions` is maintained as a backward-compatibility alias).*

---

### 1.6 Get Research Session by ID
- **Method:** `GET`
- **Path:** `/research/{session_id}`
- **Description:** Retrieves the complete session payload for an existing session ID.
- **Status:** **IMPLEMENTED**
- **Response (200 OK):** Same schema as `/analyze` response.
- **Error (404 Not Found):**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Research session 'session_invalid' not found."
  }
}
```
*(Note: `/sessions/{session_id}` is maintained as a backward-compatibility alias).*

---

### 1.7 Delete Research Session
- **Method:** `DELETE`
- **Path:** `/research/{session_id}`
- **Description:** Cascades deletion across the session, reports, sources, and opportunities in SQLite.
- **Status:** **IMPLEMENTED**
- **Response (200 OK):**
```json
{
  "message": "Session deleted successfully",
  "session_id": "session_a1b2c3d4e5f6"
}
```

---

## 2. Standard Error Response Contract

All errors return a structured JSON response:
```json
{
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human-readable error description"
  }
}
```

### Documented Error Codes & HTTP Statuses
| HTTP Status | Error Code | Description / Scenario |
|---|---|---|
| `400 Bad Request` | `INVALID_TOPIC` | Topic string is empty or contains fewer than 2 characters |
| `400 Bad Request` | `VALIDATION_ERROR` | Request payload fails Pydantic schema validation |
| `404 Not Found` | `NOT_FOUND` | Requested research session ID does not exist |
| `429 Too Many Requests` | `AI_RATE_LIMITED` | Google Gemini free-tier rate limit or quota exceeded |
| `503 Service Unavailable` | `WEB_RESEARCH_FAILED` | Current web research could not be completed via Tavily; halts rather than hallucinating from LLM memory |
| `500 Internal Error` | `PERSISTENCE_ERROR` | Analysis succeeded but SQLite write transaction failed |
| `500 Internal Error` | `PIPELINE_ERROR` | Research or opportunity agent failed to process topic |
| `500 Internal Error` | `DATABASE_ERROR` | Error reading or deleting from SQLite |
| `500 Internal Error` | `INTERNAL_SERVER_ERROR` | Unhandled runtime exception |

---

## 3. Planned Endpoints (Not Yet Implemented)

The following endpoints are architected for future phases:

### 3.1 Model Registry & Selection
- **Status:** **PLANNED**
- `GET /models` — Return list of available configured Gemini models and metadata:
```json
{
  "default_model": "BALANCED_MODEL",
  "models": [
    { "id": "FAST_MODEL", "name": "Gemini Fast", "tier": "fast", "description": "Rapid extraction" },
    { "id": "BALANCED_MODEL", "name": "Gemini Balanced", "tier": "balanced", "description": "Default multi-agent synthesis" },
    { "id": "DEEP_MODEL", "name": "Gemini Deep Analysis", "tier": "deep", "description": "Deep validation and scoring" }
  ]
}
```

### 3.2 Follow-Up Conversational Exploration
- **Status:** **PLANNED**
- `POST /research/{session_id}/chat` — Multi-turn conversation against saved session context:
```json
// Request
{
  "message": "Which opportunity has the lowest regulatory risk?"
}
```

### 3.3 Research Watchlists & Tracking
- **Status:** **PLANNED**
- `POST /watchlists` — Register an industry topic for automated monitoring.
- `GET /watchlists` — List active monitored topics and update schedules.

### 3.4 Signals & Change Detection
- **Status:** **PLANNED**
- `GET /signals` — Retrieve newly detected market signals and opportunity delta re-scores.

### 3.5 Automation Trigger
- **Status:** **PLANNED**
- `POST /automation/run` — Manually trigger an immediate update run for tracked topics.
