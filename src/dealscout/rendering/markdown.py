"""InvestmentMemo -> Markdown. Dumb, straight-through (Decision 5).

One field -> one block. No conditionals on content quality; if the memo
validated, this renders it.
"""
from __future__ import annotations

from dealscout.domain.memo import InvestmentMemo


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items)


def render_markdown(memo: InvestmentMemo) -> str:
    m = memo
    lines: list[str] = [
        f"# {m.company_name}",
        f"*{m.one_liner}*",
        "",
        "## At a glance",
        f"- **Founded:** {m.founded}",
        f"- **Stage:** {m.stage}",
        f"- **Founders:** {m.founders_summary}",
        f"- **Investors:** {m.investors}",
        f"- **Segment:** {m.segment}",
        f"- **Team size:** {m.team_size}",
        "",
        f"## Recommendation: {m.recommendation}",
        m.recommendation_rationale,
        "",
        "## Executive summary",
        m.executive_summary,
        "",
        "## Strengths",
        _bullets(m.strengths),
        "",
        "## Concerns",
        _bullets(m.concerns),
        "",
        "## Open questions",
        _bullets(m.open_questions),
        "",
        "## Product",
        m.product,
        "",
        "## Customers",
        m.customers,
        "",
        "## Traction signals",
        _bullets(m.traction_signals),
        "",
        "## Market segment",
        m.market_segment,
        "",
        "## Competitive landscape",
        m.competitive_landscape,
        "",
        "## Why now",
        m.why_now,
        "",
        "## Founders",
    ]
    for f in m.founders_detail:
        lines += [f"### {f.name} — {f.role}", f.background, ""]
    lines += [
        "## Founder–market fit",
        m.founder_market_fit,
        "",
        "## Recent news",
        (
            _bullets([f"{n.date_or_quarter}: {n.description}" for n in m.recent_news])
            if m.recent_news
            else "_None reported._"
        ),
        "",
        "## Investment thesis",
        f"**Bull case.** {m.bull_case}",
        "",
        f"**Bear case.** {m.bear_case}",
        "",
        f"**What would change our mind.** {m.mind_changers}",
        "",
        "## References",
        _bullets([f"[{r.index}] {r.description}" for r in m.references]),
    ]
    footer = []
    if m.cost_usd_estimate is not None:
        footer.append(f"est. cost ${m.cost_usd_estimate:.2f}")
    if m.latency_seconds is not None:
        footer.append(f"latency {m.latency_seconds:.0f}s")
    if footer:
        lines += ["", "---", f"_DealScout — {' · '.join(footer)}_"]
    return "\n".join(lines)
