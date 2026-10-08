import io
import json
import logging
from typing import Any, Dict, List
from datetime import datetime, timezone

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
except ImportError:
    letter = None

logger = logging.getLogger(__name__)


class ExportService:
    """Exports research sessions to Markdown, JSON, and PDF formats."""

    def to_json(self, session_data: Dict[str, Any]) -> str:
        """Export session data cleanly to JSON string."""
        return json.dumps(session_data, indent=2, ensure_ascii=False)

    def to_markdown(self, session_data: Dict[str, Any]) -> str:
        """Export session data to formatted GitHub-flavored Markdown."""
        topic = session_data.get("topic", "Research Topic")
        created = session_data.get("created_at", "")
        model_used = session_data.get("model_used") or "Default"
        research = session_data.get("research", {})
        analysis = session_data.get("analysis", {})
        opportunities = session_data.get("opportunities", [])
        sources = session_data.get("sources", [])

        lines = [
            f"# StartupLens AI — Research Intelligence Brief",
            f"**Topic:** {topic}  ",
            f"**Generated:** {created}  ",
            f"**Model:** {model_used}  \n",
            "---\n",
            "## 1. Executive Summary & Market Trends\n",
        ]

        trends = research.get("trends", [])
        if trends:
            lines.append("### Key Trends")
            for t in trends:
                lines.append(f"- {t}")
            lines.append("")

        problems = research.get("problems", [])
        if problems:
            lines.append("### Customer Pain Points")
            for p in problems:
                lines.append(f"- {p}")
            lines.append("")

        signals = analysis.get("market_signals", []) or research.get("market_signals", [])
        if signals:
            lines.append("### Market Signals & Catalysts")
            for s in signals:
                lines.append(f"- {s}")
            lines.append("")

        gaps = analysis.get("market_gaps", [])
        if gaps:
            lines.append("### Underserved Market Gaps")
            for g in gaps:
                lines.append(f"- {g}")
            lines.append("")

        lines.append("## 2. Startup Opportunity Hypotheses\n")
        for i, opp in enumerate(opportunities, 1):
            score_txt = ""
            score_data = opp.get("score")
            if score_data:
                score_txt = f" *(Score: {score_data.get('overall_score', 0)}/50 · {score_data.get('confidence_label', '')})*"

            lines.append(f"### {i}. {opp.get('title', 'Opportunity')}{score_txt}")
            lines.append(f"**Target Customer:** {opp.get('customer', '')}\n")
            lines.append(f"**Core Problem:** {opp.get('problem', '')}\n")
            lines.append(f"**Proposed Solution:** {opp.get('solution', '')}\n")
            lines.append(f"**Why Now:** {opp.get('why_now', '')}\n")

            features = opp.get("mvp_features", [])
            if features:
                lines.append("**MVP Features:**")
                for f in features:
                    lines.append(f"- {f}")
                lines.append("")

            risks = opp.get("risks", [])
            if risks:
                lines.append("**Risks & Considerations:**")
                for r in risks:
                    lines.append(f"- {r}")
                lines.append("")

            if score_data and score_data.get("rationale"):
                lines.append(f"**Validation Rationale:** {score_data.get('rationale')}\n")

            lines.append("---\n")

        lines.append("## 3. Verified Sources & Citations\n")
        for i, s in enumerate(sources, 1):
            stype = (s.get("source_type") or "web").upper()
            ref = s.get("page_or_section")
            ref_str = f" · {ref}" if ref else ""
            lines.append(f"{i}. [{s.get('title', 'Source')}]({s.get('url', '#')}) ({stype}{ref_str})")
            if s.get("snippet"):
                lines.append(f"   > {s.get('snippet')[:200]}...")

        return "\n".join(lines)

    def to_pdf_bytes(self, session_data: Dict[str, Any]) -> bytes:
        """Export session data to PDF bytes using reportlab."""
        if letter is None:
            raise RuntimeError("ReportLab is not installed or available.")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=14,
        )
        h2_style = ParagraphStyle(
            "Heading2Custom",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "BodyCustom",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceAfter=4,
        )
        bold_label = ParagraphStyle(
            "BoldLabel",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=2,
        )

        elements = []
        topic = session_data.get("topic", "Research Topic")
        elements.append(Paragraph(f"StartupLens AI — {topic}", title_style))
        created = session_data.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        elements.append(Paragraph(f"Generated: {created} | Platform: StartupLens AI", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=12))

        # Trends
        trends = session_data.get("research", {}).get("trends", [])
        if trends:
            elements.append(Paragraph("Market Trends", h2_style))
            for t in trends[:5]:
                elements.append(Paragraph(f"• {t}", body_style))
            elements.append(Spacer(1, 8))

        # Opportunities
        opps = session_data.get("opportunities", [])
        if opps:
            elements.append(Paragraph("Startup Opportunities & Validation", h2_style))
            for i, opp in enumerate(opps[:4], 1):
                score_str = ""
                score_data = opp.get("score")
                if score_data:
                    score_str = f" [Score: {score_data.get('overall_score', 0)}/50 - {score_data.get('confidence_label', '')}]"

                elements.append(Paragraph(f"<b>{i}. {opp.get('title', 'Hypothesis')}{score_str}</b>", bold_label))
                elements.append(Paragraph(f"<b>Target:</b> {opp.get('customer', '')}", body_style))
                elements.append(Paragraph(f"<b>Solution:</b> {opp.get('solution', '')}", body_style))
                elements.append(Paragraph(f"<b>Why Now:</b> {opp.get('why_now', '')}", body_style))
                elements.append(Spacer(1, 6))

        # Sources
        sources = session_data.get("sources", [])
        if sources:
            elements.append(Paragraph("Verified Sources", h2_style))
            for s in sources[:6]:
                src_title = s.get("title") or s.get("url")
                stype = (s.get("source_type") or "WEB").upper()
                elements.append(Paragraph(f"• [{stype}] {src_title}", body_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


export_service = ExportService()
