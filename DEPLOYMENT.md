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
| `JWT_SECRET` | Required | Secure random secret for signing JWT sessions (min 32 chars) |
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth 2.0 Client ID (`*.apps.googleusercontent.com`) |
| `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth 2.0 Client Secret (Render backend only) |
| `GOOGLE_REDIRECT_URI` | Optional | `https://<YOUR-RENDER-API>.onrender.com/auth/google/callback` |
| `GITHUB_CLIENT_ID` | Optional | GitHub OAuth App Client ID |
| `GITHUB_CLIENT_SECRET` | Optional | GitHub OAuth App Client Secret (Render backend only) |
| `GITHUB_REDIRECT_URI` | Optional | `https://<YOUR-RENDER-API>.onrender.com/auth/github/callback` |
| `LINKEDIN_CLIENT_ID` | Optional | LinkedIn Developer App Client ID |
| `LINKEDIN_CLIENT_SECRET` | Optional | LinkedIn Developer App Client Secret (Render backend only) |
| `LINKEDIN_REDIRECT_URI` | Optional | `https://<YOUR-RENDER-API>.onrender.com/auth/linkedin/callback` |

> **Security Reminder:** Never place OAuth client secrets (`GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_SECRET`, `LINKEDIN_CLIENT_SECRET`, or `JWT_SECRET`) in Vercel or `NEXT_PUBLIC_*` variables. All token exchanges and credentials stay securely isolated on Render.

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

## 6. Social OAuth Provider Configuration

StartupLens AI supports secure server-side social authentication via **Google**, **GitHub**, and **LinkedIn**.
All authorization callbacks route strictly through the **Render Backend API**, which exchanges credentials server-side and issues an encrypted HttpOnly session cookie before redirecting the user back to the Vercel frontend workspace.

### A. Google OAuth 2.0 / OIDC Setup
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Navigate to **APIs & Services** → **Credentials**.
3. Click **Create Credentials** → **OAuth client ID**.
4. Application type: **Web application**.
5. Set **Authorized redirect URIs**:
   - Production: `https://<YOUR-RENDER-API>.onrender.com/auth/google/callback`
   - Local development (optional): `http://127.0.0.1:8003/auth/google/callback`
6. Copy the **Client ID** and **Client Secret**.
7. In the Render Dashboard under **Environment**, set:
   - `GOOGLE_CLIENT_ID=<your-google-client-id>.apps.googleusercontent.com`
   - `GOOGLE_CLIENT_SECRET=<your-google-client-secret>`
   - `GOOGLE_REDIRECT_URI=https://<YOUR-RENDER-API>.onrender.com/auth/google/callback`

### B. GitHub OAuth Setup
1. Go to [GitHub Developer Settings](https://github.com/settings/developers).
2. Click **New OAuth App**.
3. Enter Application Details:
   - **Application name:** `StartupLens AI`
   - **Homepage URL:** `https://<YOUR-APP>.vercel.app`
   - **Authorization callback URL:** `https://<YOUR-RENDER-API>.onrender.com/auth/github/callback`
4. Register application and click **Generate a new client secret**.
5. In the Render Dashboard under **Environment**, set:
   - `GITHUB_CLIENT_ID=<your-github-client-id>`
   - `GITHUB_CLIENT_SECRET=<your-github-client-secret>`
   - `GITHUB_REDIRECT_URI=https://<YOUR-RENDER-API>.onrender.com/auth/github/callback`
6. *Note on Permissions:* StartupLens requests only minimum read-only profile & email scopes (`read:user user:email`). It does NOT request repository write access.

### C. LinkedIn OAuth 2.0 / OpenID Connect Setup
1. Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/).
2. Click **Create App** and associate it with your company/project page.
3. In the **Products** tab, request access to **Sign In with LinkedIn using OpenID Connect**.
4. In the **Auth** tab:
   - Set **Authorized redirect URLs for your app**:
     - Production: `https://<YOUR-RENDER-API>.onrender.com/auth/linkedin/callback`
     - Local development (optional): `http://127.0.0.1:8003/auth/linkedin/callback`
5. Note the **Client ID** and generate the **Primary Client Secret**.
6. In the Render Dashboard under **Environment**, set:
   - `LINKEDIN_CLIENT_ID=<your-linkedin-client-id>`
   - `LINKEDIN_CLIENT_SECRET=<your-linkedin-client-secret>`
   - `LINKEDIN_REDIRECT_URI=https://<YOUR-RENDER-API>.onrender.com/auth/linkedin/callback`
7. *Note on Scopes:* StartupLens uses the standard LinkedIn OIDC scopes (`openid profile email`) without requesting extraneous organization permissions.

---

## 7. CORS Configuration

FastAPI handles CORS dynamically in `backend/main.py`:
- Allowed origins include `http://localhost:3000`, `http://127.0.0.1:3000`, and whatever is specified in `FRONTEND_URL`.
- An origin regex pattern (`^https://.*\.vercel\.app$`) is active by default to accept requests from all Vercel production and preview URLs.
- After obtaining your Vercel URL, set `FRONTEND_URL=https://<YOUR-APP>.vercel.app` in Render and trigger a redeploy to lock down production CORS origins.

---

## 8. API URL Configuration

The frontend in `frontend/src/lib/api.ts` references:
```typescript
const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8003"
).replace(/\/$/, "");
```
All API interactions (`/analyze`, `/research`, `/models`, `/config/status`, documents, exports, trackers) route through this base URL.

---

## 9. Verification: Health Check

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

## 10. Verification: Models & Config Status

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

## 11. Verification: Analyze Endpoint Test

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

## 12. SQLite Ephemeral Hosting Limitation

- Render Free / Starter instances use an **ephemeral disk**.
- When the Render service restarts, scales, or redeploys, the local `startuplens.db` file may reset to the initial state.
- For permanent session history in a production enterprise setup:
  - Attach a **Render Persistent Disk** mounted at `/data` and set `DATABASE_URL=sqlite:////data/startuplens.db`, OR
  - Configure a cloud PostgreSQL database URL (e.g., Supabase / Neon / Render PostgreSQL) in `DATABASE_URL`.
- The current implementation retains 100% SQLite compatibility as requested.

---

## 13. Troubleshooting

| Symptom | Cause | Solution |
|---|---|---|
| `502 Bad Gateway` on Render cold start | Free instance spun down due to inactivity | Allow 30–60 seconds for Render container to spin up. |
| `CORS error` in browser console | Origin not permitted | Check `FRONTEND_URL` in Render and verify it matches the Vercel domain without trailing slash. |
| `503 Service Unavailable` on `/analyze` | Tavily API or LLM quota exhausted | Verify `TAVILY_API_KEY` and LLM keys are valid in Render Environment tab. Check `/config/status`. |
| `400 Invalid Topic` | Topic < 2 characters | Provide a valid research topic string. |
| Render build fails with `ModuleNotFoundError` | Root directory not set | Ensure **Root Directory** is set to `backend` and `requirements.txt` is present. |
