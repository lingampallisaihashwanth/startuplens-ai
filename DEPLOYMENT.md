# StartupLens AI — Deployment Guide

This guide details how to deploy StartupLens AI publicly with:
- **Frontend** hosted on **Vercel**
- **Backend** hosted on **Render**
- Real HTTPS URLs, zero mock data, and full multi-agent model router support (Gemini, Groq, Mistral, Tavily, SQLite).

---

## Architecture Overview

```
User (Browser)
      │
      ▼
Vercel Frontend (Next.js 16 / React 19)
      │  HTTPS (NEXT_PUBLIC_API_URL)
      ▼
Render Backend (FastAPI / Uvicorn)
      │
      ├──> Tavily Search API (Live Market Evidence)
      ├──> Model Router (Gemini 2.5 Flash / Groq / Mistral)
      ├──> Multi-Agent Intelligence Pipeline (Research, Analysis, Opportunity, Scoring)
      └──> SQLite Database (Session persistence)
```

---

## 1. GitHub Preparation

1. **Verify `.gitignore`:**
   Ensure secrets, virtual environments, build artifacts, and databases are ignored:
   - `.env`, `.env.local`
   - `.venv/`
   - `startuplens.db`, `*.db`
   - `node_modules/`, `.next/`
   - `__pycache__/`, `*.pyc`

2. **Commit and Push to GitHub:**
   ```bash
   git add .
   git commit -m "feat: prepare StartupLens AI for Render and Vercel production deployment"
   git branch -M main
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPOSITORY_NAME>.git
   git push -u origin main
   ```

---

## 2. Render Backend Deployment

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Select your GitHub repository (`<YOUR_REPOSITORY_NAME>`).
4. Configure the service settings:
   - **Name:** `startuplens-api` (or your chosen name)
   - **Region:** Any close region (e.g., Frankfurt or Oregon)
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free (or Starter)

---

## 3. Render Environment Variables

In Render **Environment** tab, configure the following variables (do not commit these to git):

| Variable Name | Required | Example / Description |
|---|---|---|
| `GEMINI_API_KEY` | Recommended | Google AI Gemini API Key |
| `GEMINI_MODEL` | Optional | `gemini-2.5-flash` (default) |
| `GROQ_API_KEY` | Optional | Groq API Key |
| `GROQ_MODEL_FAST` | Optional | `openai/gpt-oss-20b` (default) |
| `GROQ_MODEL_REASONING` | Optional | `openai/gpt-oss-120b` (default) |
| `MISTRAL_API_KEY` | Optional | Mistral API Key |
| `MISTRAL_MODEL` | Optional | `mistral-small-latest` (default) |
| `TAVILY_API_KEY` | Required | Tavily Search API Key for web research |
| `DATABASE_URL` | Optional | `sqlite:///./startuplens.db` (default) |
| `DEFAULT_MODEL` | Optional | `auto` (default) |
| `FRONTEND_URL` | Required | `https://<YOUR-APP>.vercel.app` (set after creating Vercel app) |

> **Note:** StartupLens AI requires at least one LLM key (`GEMINI_API_KEY`, `GROQ_API_KEY`, or `MISTRAL_API_KEY`) and `TAVILY_API_KEY` to perform research.

---

## 4. Vercel Frontend Deployment

1. Log in to [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository.
4. Configure the project:
   - **Framework Preset:** Next.js
   - **Root Directory:** Edit and select `frontend`
   - **Build Command:** `npm run build` (auto-detected)
   - **Output Directory:** `.next` (auto-detected)
   - **Install Command:** `npm install` (auto-detected)

---

## 5. Vercel Environment Variables

In the Vercel **Environment Variables** section:

| Variable Name | Environment | Value |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Production, Preview, Development | `https://<YOUR-RENDER-API>.onrender.com` |

5. Click **Deploy**. Vercel will build and assign a public URL (e.g. `https://startuplens-ai.vercel.app`).

---

## 6. CORS Configuration

FastAPI handles CORS dynamically in `backend/main.py`:
- Allowed origins include `http://localhost:3000`, `http://127.0.0.1:3000`, and whatever is specified in `FRONTEND_URL`.
- An origin regex pattern (`^https://.*\.vercel\.app$`) is active by default to accept requests from all Vercel production and preview URLs.
- After obtaining your Vercel URL, set `FRONTEND_URL=https://<YOUR-APP>.vercel.app` in Render and trigger a redeploy to lock down production CORS origins.

---

## 7. API URL Configuration

The frontend in `frontend/src/lib/api.ts` references:
```typescript
const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8003"
).replace(/\/$/, "");
```
All API interactions (`/analyze`, `/research`, `/models`, `/config/status`, documents, exports, trackers) route through this base URL.

---

## 8. Verification: Health Check

Verify the backend is live:
```bash
curl -s https://<YOUR-RENDER-API>.onrender.com/health
```
**Expected response:**
```json
{
  "status": "ok",
  "service": "StartupLens AI API",
  "message": "StartupLens AI API is running"
}
```

---

## 9. Verification: Models & Config Status

Verify configured models:
```bash
curl -s https://<YOUR-RENDER-API>.onrender.com/models
```
**Expected response:**
```json
{
  "default": "auto",
  "models": [
    { "id": "auto", "display_name": "Auto (Smart Routing)", "provider": "system" },
    { "id": "gemini-balanced", "display_name": "Gemini 2.5 Flash", "provider": "google" }
  ]
}
```

Verify provider configuration status (never leaks keys):
```bash
curl -s https://<YOUR-RENDER-API>.onrender.com/config/status
```

---

## 10. Verification: Analyze Endpoint Test

Run an end-to-end research query on the production backend:
```bash
curl -X POST https://<YOUR-RENDER-API>.onrender.com/analyze \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI Robotics", "model": "auto"}'
```
**Expected response:**
A full JSON payload containing:
- `session_id`
- `topic`: `"AI Robotics"`
- `research`: `{ "trends": [...], "problems": [...], "sources": [...] }`
- `analysis`: `{ "market_signals": [...], "market_gaps": [...] }`
- `opportunities`: array of scored opportunity hypotheses (`score.overall_score`, `score.confidence_label`)

---

## 11. SQLite Ephemeral Hosting Limitation

- Render Free / Starter instances use an **ephemeral disk**.
- When the Render service restarts, scales, or redeploys, the local `startuplens.db` file may reset to the initial state.
- For permanent session history in a production enterprise setup:
  - Attach a **Render Persistent Disk** mounted at `/data` and set `DATABASE_URL=sqlite:////data/startuplens.db`, OR
  - Configure a cloud PostgreSQL database URL (e.g., Supabase / Neon / Render PostgreSQL) in `DATABASE_URL`.
- The current implementation retains 100% SQLite compatibility as requested.

---

## 12. Troubleshooting

| Symptom | Cause | Solution |
|---|---|---|
| `502 Bad Gateway` on Render cold start | Free instance spun down due to inactivity | Allow 30–60 seconds for Render container to spin up. |
| `CORS error` in browser console | Origin not permitted | Check `FRONTEND_URL` in Render and verify it matches the Vercel domain without trailing slash. |
| `503 Service Unavailable` on `/analyze` | Tavily API or LLM quota exhausted | Verify `TAVILY_API_KEY` and LLM keys are valid in Render Environment tab. Check `/config/status`. |
| `400 Invalid Topic` | Topic < 2 characters | Provide a valid research topic string. |
| Render build fails with `ModuleNotFoundError` | Root directory not set | Ensure **Root Directory** is set to `backend` and `requirements.txt` is present. |
