# UI Specification — StartupLens AI

This document defines the user experience, layout hierarchy, and interface design system for the StartupLens AI chat-first frontend.

---

## 1. Design Philosophy

StartupLens AI offers an intentional, **chat-first research experience**. It combines the conversational flow of a modern AI assistant with structured, card-based intelligence artifacts.

- **Research-Focused:** Avoids cluttered multi-widget analytics dashboards. The primary focus remains on the synthesis of market evidence and opportunity hypotheses.
- **Original & Professional:** Built with custom design tokens, distinct typographic hierarchy, and tailored components. It avoids copying third-party assistant logos, branding, or layouts.
- **Hypothesis-Oriented:** Visual styling clearly distinguishes verified factual observations (blue/green signal indicators) from speculative opportunity hypotheses (amber/purple opportunity cards).
- **Responsive & Accessible:** Fully operable across desktop, tablet, and mobile with keyboard shortcuts, high-contrast states, and WCAG 2.2 AA compliance.

---

## 2. Layout Structure

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  Sidebar                │  Main Conversation Workspace                                 │
├─────────────────────────┼──────────────────────────────────────────────────────────────┤
│  StartupLens AI         │  Conversation Header                                         │
│                         │  [ Topic: AI Robotics ]   [ Model: Gemini Flash ]  [Theme]   │
│  + New Research (Ctrl+K)│──────────────────────────────────────────────────────────────│
│                         │                                                              │
│  Navigation             │  User Query Bubble:                                          │
│  • Chat                 │  "Research AI Robotics opportunities"                        │
│  • Research History     │                                                              │
│  • Saved Ideas          │  Agent Activity Progress:                                    │
│  • Settings             │  ✓ Searching live web sources with Tavily                   │
│                         │  ✓ Extracting market signals & customer pain points         │
│  Recent Research        │  ● Analyzing competitor gaps & market timing                │
│  • AI Robotics (3 opps) │  ○ Synthesizing evidence-backed opportunity hypotheses       │
│  • Autonomous Freight   │                                                              │
│  • Synthetic Biology    │  Assistant Structured Intelligence Report:                   │
│                         │  ┌────────────────────────────────────────────────────────┐  │
│  User Profile           │  │ Executive Findings • Trends • Market Signals • Gaps    │  │
│                         │  └────────────────────────────────────────────────────────┘  │
│                         │  ┌────────────────────────────────────────────────────────┐  │
│                         │  │ Startup Opportunity Hypotheses (3 Cards)               │  │
│                         │  │ • FleetSynapse [MVP Details] [Risks] [Evidence] [Save] │  │
│                         │  └────────────────────────────────────────────────────────┘  │
│                         │  ┌────────────────────────────────────────────────────────┐  │
│                         │  │ Verifiable Sources & Evidence Links (6 Citations)      │  │
│                         │  └────────────────────────────────────────────────────────┘  │
│                         │                                                              │
│                         │──────────────────────────────────────────────────────────────│
│                         │  Research Composer                                           │
│                         │  ┌────────────────────────────────────────────────────────┐  │
│                         │  │ Enter an industry or technology topic...            [↑]│  │
│                         │  └────────────────────────────────────────────────────────┘  │
│                         │  [AI Robotics]  [Vertical SaaS]  [BioTech Tools]             │
└─────────────────────────┴──────────────────────────────────────────────────────────────┘
```

---

## 3. Core Component Specifications

### 3.1 Sidebar Navigation (`Sidebar.tsx`)
- **Header:** Displays the StartupLens AI brand mark and application title.
- **Action Button:** `+ New Research` button with `Cmd+K` / `Ctrl+K` keyboard shortcut badge.
- **Navigation Links:**
  - **Chat:** Returns to the active conversation workspace.
  - **Research History:** Opens the historical sessions manager.
  - **Saved Ideas:** Displays favorited opportunity hypotheses (with badge counter).
  - **Settings:** Triggers the configuration modal.
- **Recent Research List:** Displays recently saved sessions chronologically, with relative timestamps ("2h ago", "Yesterday"), source counts, and delete actions.
- **User Footer:** Clean user profile indicator with persistent state.

### 3.2 Conversation Header
- **Topic & Model Context:** Displays the current active research topic and an active Gemini model indicator.
- **Utility Actions:** Theme toggle (dark/light), session export, and mobile sidebar toggle.

### 3.3 Model Selector (Planned UI Feature)
- Contextual dropdown allowing users to select execution profiles:
  - `FAST_MODEL` (Gemini Flash — speed-optimized)
  - `BALANCED_MODEL` (Default — comprehensive synthesis)
  - `DEEP_MODEL` (Gemini Pro — in-depth scoring)

### 3.4 User Message Bubble
- Right-aligned clean card presenting the user's research topic query with a timestamp.

### 3.5 Agent Pipeline Progress Indicator (`AgentStatus.tsx`)
- Appears during in-flight analysis requests.
- Shows step-by-step milestone execution without leaking raw reasoning tokens:
  1. `Searching live web sources with Tavily` (Web Research)
  2. `Extracting market signals & customer pain points` (Market & Customer Insights)
  3. `Analyzing competitor gaps & market timing` (Competitive Intelligence)
  4. `Synthesizing evidence-backed opportunity hypotheses` (Opportunity Generation & Validation)
- Includes animated pulse indicators and completed step checkmarks.

### 3.6 Structured Findings & Market Analysis (`ResearchReport.tsx`)
- **Executive Findings Tab:** Concise overview of emerging trends, market signals, and customer pain points.
- **Market Dynamics Tab:** Incumbent competitors, underserved market gaps, and "Why Now" macroeconomic drivers.

### 3.7 Opportunity Hypotheses (`OpportunityCard.tsx`)
- Card-based layout for each generated hypothesis (3–5 cards):
  - **Header:** Opportunity Title, Target Customer badge, and Bookmark/Save button.
  - **Problem & Solution:** Clean two-column or stacked statement of the customer friction point and proposed solution.
  - **Why Now:** Timing catalyst highlighting current technological or economic shifts.
  - **Competitors:** Mention of 2–3 active market alternatives.
  - **Collapsible MVP Features:** Concrete 4-week scope bullet points.
  - **Risk Assessment:** Candid market and technological risks.
  - **Corroborating Evidence:** Direct links to research citations.

### 3.8 Verifiable Evidence Drawer (`Sources.tsx`)
- Grid or list of external citations acquired by Tavily:
  - Source Title, publisher domain, and publication date.
  - External link icon opening the real URL in a secure new tab (`rel="noopener noreferrer"`).
  - Snippet preview on hover or expand.

### 3.9 Research Composer (`Composer.tsx`)
- Multi-line accessible textarea with auto-grow behavior.
- Instant submission via `Enter` (with `Shift+Enter` for linebreaks).
- Quick suggestion chips (e.g., *"AI Robotics"*, *"Enterprise Security"*, *"ClimateTech Logistics"*).

### 3.10 Research History View (`HistoryView.tsx`)
- Full-page searchable data table of historical sessions.
- Allows filtering by topic, sorting by date, inspecting previous reports, and deleting records.

### 3.11 Saved Ideas View (`SavedIdeasView.tsx`)
- Dedicated gallery displaying opportunities saved by the user.
- Export to JSON/Markdown options for external review.

### 3.12 Automation & Monitoring UI (Planned)
- Future watchlist drawer allowing users to click **"Track Topic"** to schedule weekly change detection and brief generation.

---

## 4. Visual Foundation & Design Tokens

StartupLens AI uses custom CSS tokens defined in `frontend/src/app/globals.css`:

| Token | Dark Theme (Default) | Light Theme | Usage |
|---|---|---|---|
| `--background` | `#20201f` | `#fbfbf9` | Primary page canvas |
| `--surface` | `#282827` | `#ffffff` | Cards, sidebar, modal background |
| `--surface-raised` | `#2f2f2d` | `#f5f4f0` | Elevated containers, cards hover |
| `--foreground` | `#f0efec` | `#1c1b18` | Primary text |
| `--muted` | `#898781` | `#797771` | Secondary text, placeholders |
| `--accent` | `#6da7ec` | `#2563eb` | Primary interactive color, focus rings |
| `--border` | `#323230` | `#e4e2dc` | Card and component borders |
| `--success` | `#4ade80` | `#16a34a` | Completed steps, high-conviction indicators |
| `--warning` | `#fbbf24` | `#d97706` | Opportunity risk indicators |
| `--danger` | `#f87171` | `#dc2626` | Error alerts, delete actions |

---

## 5. Required Interface States

1. **Empty State:** Clean welcome hero illustrating the research flow with pre-populated suggested topic chips.
2. **Active / Loading State:** Composer disabled; pulsating agent progress card highlighting each stage.
3. **Success State:** Seamless presentation of the research report, opportunity cards, and evidence links.
4. **Error State:** Clear, non-technical explanation of issues (e.g., `AI_RATE_LIMITED` advising a 60-second cooldown, or `INVALID_TOPIC` prompting for elaboration). Includes a one-click Retry action.
5. **Interactive States:** Distinct `:hover`, `:focus-visible`, and `:active` styling on all buttons and inputs.
