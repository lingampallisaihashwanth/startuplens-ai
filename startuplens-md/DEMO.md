# Live Demonstration Script — StartupLens AI

This guide provides a structured, professional demonstration workflow for presenting StartupLens AI in academic, hackathon, and technical review settings.

---

## 1. Current MVP Demonstration Workflow (Implemented)

### Demonstration Topic
**Recommended Topic:** `AI Robotics` *(Alternative: `Autonomous Logistics` or `Synthetic Biology`)*

### Step-by-Step Walkthrough

1. **Launch & Interface Overview (30 Seconds)**
   - Open StartupLens AI at `http://localhost:3000`.
   - Point out the clean, chat-first research workspace, the persistent navigation sidebar, and the pre-loaded suggestion chips.
   - Mention the underlying stack: **FastAPI backend (port 8003)**, **Google Gemini**, **Tavily live search**, and **SQLite persistence**.

2. **Submit Research Topic**
   - Click the `AI Robotics` chip or type `AI Robotics` into the research composer and press **Enter**.
   - Note the immediate transition to the active analysis state.

3. **Highlight Real-Time Agent Progression**
   - Point out the `AgentStatus` milestone tracker:
     - `Searching live web sources with Tavily`
     - `Extracting market signals & customer pain points`
     - `Analyzing competitor gaps & market timing`
     - `Synthesizing evidence-backed opportunity hypotheses`
   - Emphasize that the system communicates high-level task state without leaking raw chain-of-thought tokens.

4. **Review Market & Competitive Findings**
   - Navigate the **Research Report** tabs:
     - *Trends & Signals:* Show emerging market movements (e.g., vision-language-action foundation models, funding rounds).
     - *Competitors & Gaps:* Highlight incumbent players and identify potential market gaps (e.g., cross-hardware teleoperation tools).

5. **Examine Startup Opportunity Hypotheses**
   - Walk through one generated opportunity card (e.g., *FleetSynapse*):
     - Review the identified customer pain point and target buyer persona.
     - Inspect the "Why Now" catalyst.
     - Expand the **MVP Features** drawer to reveal the concrete 4-week scope.
     - Discuss the candid **Risks & Obstacles** identified by the agent.
     - Demonstrate bookmarking the opportunity via the **Save Idea** action.

6. **Verify Evidence & Sources**
   - Scroll to the **Sources & Citations** section.
   - Click an external citation to demonstrate that all evidence traces back to genuine, current web sources retrieved via Tavily.

7. **Demonstrate Session History & Persistence**
   - Open the **Research History** view from the sidebar.
   - Show how the completed session was persisted atomically to SQLite with source and opportunity counts.
   - Demonstrate switching between past sessions and deleting a test session.

---

## 2. Professional Presentation Language

To maintain scientific integrity and credibility, use disciplined vocabulary during the presentation:

| Recommended Terminology | Disallowed Exaggerations |
|---|---|
| *"Evidence-backed analysis"* | *"Guaranteed successful startup"* |
| *"Opportunity hypothesis"* | *"Proven billion-dollar company idea"* |
| *"Potential market gap"* | *"Uncontested monopoly space"* |
| *"Possible MVP scope"* | *"Complete enterprise solution"* |
| *"Reported market signal"* | *"Flawless market prediction"* |

---

## 3. Future Capabilities Demonstration (Planned Roadmap)

After demonstrating the working Phase 1 MVP, present the forward-looking roadmap:

### 3.1 Dynamic Model Selection (Phase 3)
- **Concept:** Toggle between `FAST_MODEL` (for rapid scanning) and `DEEP_MODEL` (for intensive cross-validation) directly within the conversation header.

### 3.2 Granular Opportunity Validation (Phase 2)
- **Concept:** Expanded multi-agent scorecards grading market demand, competitive pressure, execution feasibility, market timing, and AI advantage with evidence rationales.

### 3.3 Research Tracker & Continuous Monitoring (Phase 4)
- **Concept:** Enrolling a topic in the **Research Tracker** to receive automated change-detection alerts and weekly startup briefs without heavy queue infrastructure.
