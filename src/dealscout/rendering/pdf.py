"""InvestmentMemo -> PDF (ReportLab). Built from scratch (no sample skeleton
exists in this repo). Dumb, straight-through (Decision 5): one field -> one
flowable, deterministic, no content conditionals beyond empty recent_news.
"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from dealscout.domain.memo import InvestmentMemo

# Palette
_INK = colors.HexColor("#1a2233")
_MUTED = colors.HexColor("#5b6472")
_ACCENT = colors.HexColor("#2f6fed")
_RULE = colors.HexColor("#d9dee7")
_REC_COLOR = {
    "MEET": colors.HexColor("#1f9d55"),
    "TRACK": colors.HexColor("#d99a00"),
    "PASS": colors.HexColor("#c0392b"),
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], textColor=_INK, fontSize=22,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], textColor=_MUTED, fontSize=11,
            italic=True, spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], textColor=_ACCENT, fontSize=13,
            spaceBefore=14, spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "h3", parent=base["Heading3"], textColor=_INK, fontSize=11,
            spaceBefore=6, spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], textColor=_INK, fontSize=9.5,
            leading=14, spaceAfter=4,
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"], textColor=_INK, fontSize=9,
            leading=12,
        ),
        "rec": ParagraphStyle(
            "rec", parent=base["Normal"], textColor=colors.white, fontSize=15,
            alignment=TA_CENTER, leading=20,
        ),
    }


def _page_chrome(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(_RULE)
    canvas.line(0.75 * inch, 0.7 * inch, 7.75 * inch, 0.7 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(_MUTED)
    canvas.drawString(
        0.75 * inch, 0.55 * inch,
        "DealScout — automated research memo. Not investment advice.",
    )
    canvas.drawRightString(7.75 * inch, 0.55 * inch, f"Page {doc.page}")
    canvas.restoreState()


def render_pdf(memo: InvestmentMemo, output_path: str) -> str:
    """Render an InvestmentMemo to PDF at output_path. Returns the path."""
    m = memo
    s = _styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=LETTER,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.9 * inch,
        title=f"{m.company_name} — Investment Memo",
    )
    story: list = []

    def para(t: str, st: str = "body") -> Paragraph:
        return Paragraph(t, s[st])

    def section(title: str, text: str) -> None:
        story.append(para(title, "h2"))
        story.append(para(text))

    def bullets(title: str, items: list[str]) -> None:
        story.append(para(title, "h2"))
        story.append(
            ListFlowable(
                [ListItem(para(x), leftIndent=10) for x in items],
                bulletType="bullet", start="•",
            )
        )

    # Title
    story.append(para(m.company_name, "title"))
    story.append(para(m.one_liner, "subtitle"))
    story.append(HRFlowable(width="100%", color=_RULE, spaceAfter=8))

    # At-a-glance grid (4x2)
    g = [
        ["Founded", m.founded, "Stage", m.stage],
        ["Founders", m.founders_summary, "Investors", m.investors],
        ["Segment", m.segment, "Team size", m.team_size],
    ]
    rows = [[para(f"<b>{a}</b>", "cell"), para(b, "cell"),
             para(f"<b>{c}</b>", "cell"), para(d, "cell")] for a, b, c, d in g]
    t = Table(rows, colWidths=[1.0 * inch, 2.4 * inch, 1.0 * inch, 2.4 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f7fb")),
        ("BOX", (0, 0), (-1, -1), 0.5, _RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Recommendation banner
    rec_tbl = Table(
        [[Paragraph(f"RECOMMENDATION: {m.recommendation}", s["rec"])]],
        colWidths=[6.8 * inch],
    )
    rec_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1),
         _REC_COLOR.get(m.recommendation, _ACCENT)),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(rec_tbl)
    story.append(Spacer(1, 4))
    story.append(para(m.recommendation_rationale))

    section("Executive summary", m.executive_summary)
    bullets("Strengths", m.strengths)
    bullets("Concerns", m.concerns)
    bullets("Open questions", m.open_questions)
    section("Product", m.product)
    section("Customers", m.customers)
    bullets("Traction signals", m.traction_signals)
    section("Market segment", m.market_segment)
    section("Competitive landscape", m.competitive_landscape)
    section("Why now", m.why_now)

    story.append(para("Founders", "h2"))
    for f in m.founders_detail:
        story.append(para(f"{f.name} — {f.role}", "h3"))
        story.append(para(f.background))
    section("Founder–market fit", m.founder_market_fit)

    story.append(para("Recent news", "h2"))
    if m.recent_news:
        story.append(ListFlowable(
            [ListItem(para(f"<b>{n.date_or_quarter}</b> — {n.description}"),
                      leftIndent=10) for n in m.recent_news],
            bulletType="bullet", start="•",
        ))
    else:
        story.append(para("None reported."))

    story.append(para("Investment thesis", "h2"))
    story.append(para(f"<b>Bull case.</b> {m.bull_case}"))
    story.append(para(f"<b>Bear case.</b> {m.bear_case}"))
    story.append(para(f"<b>What would change our mind.</b> {m.mind_changers}"))

    story.append(para("References", "h2"))
    story.append(ListFlowable(
        [ListItem(para(f"[{r.index}] {r.description}"), leftIndent=10)
         for r in m.references],
        bulletType="bullet", start="–",
    ))

    foot = []
    if m.cost_usd_estimate is not None:
        foot.append(f"est. cost ${m.cost_usd_estimate:.2f}")
    if m.latency_seconds is not None:
        foot.append(f"latency {m.latency_seconds:.0f}s")
    if foot:
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", color=_RULE, spaceAfter=4))
        story.append(para(" · ".join(foot), "subtitle"))

    doc.build(story, onFirstPage=_page_chrome, onLaterPages=_page_chrome)
    return output_path
