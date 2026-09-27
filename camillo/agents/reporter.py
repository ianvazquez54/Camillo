"""Reporter agent: turns the scored, matched trends into a short daily report."""

import json
from datetime import date

from .. import config

SYSTEM = (
    "You write short, plain-English research notes for an individual investor. "
    "Be specific and skeptical: Reddit buzz is an early signal, not proof. "
    "Never give buy or sell advice. Reply with JSON only."
)

PROMPT = """Here are today's top consumer trends from Reddit, already matched to their owners.
Pick the 3 most interesting signals for someone looking for public companies
whose brands are gaining attention. Prefer brands with a public parent and
high match confidence. Also point out any brand that is private (no ticker).

Return {{"headline": "one sentence summary of today",
        "signals": [{{"brand": "...", "ticker": "... or null", "take": "2 sentences on why it matters and what would confirm it"}}]}}

Trends:
{trends}"""


def _fmt_growth(t):
    if t.get("is_new"):
        return "new"
    if t.get("growth"):
        return f"{t['growth']}x"
    return "-"


def build_markdown(trends, notes, day):
    lines = [f"# Camillo daily report: {day}", ""]
    if notes.get("headline"):
        lines += [notes["headline"], ""]

    if notes.get("signals"):
        lines += ["## Signals worth a closer look", ""]
        for s in notes["signals"]:
            ticker = f" ({s['ticker']})" if s.get("ticker") else " (private)"
            lines.append(f"- **{s['brand']}{ticker}:** {s.get('take', '')}")
        lines.append("")

    lines += [
        "## Top trends",
        "",
        "| # | Brand | Mentions | Growth | Positive | Public parent | Ticker | Confidence |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, t in enumerate(trends, 1):
        lines.append(
            f"| {i} | {t['brand']} | {t['mentions']} | {_fmt_growth(t)} | "
            f"{int(t['positive_share'] * 100)}% | {t.get('public_parent') or 'Private'} | "
            f"{t.get('ticker') or '-'} | {t.get('match_confidence', '-')} |"
        )
    lines += [
        "",
        "_Growth compares today's mentions with the average of the previous 7 runs. "
        "\"new\" means Camillo had not seen the brand before. "
        "This is research, not investment advice._",
    ]
    return "\n".join(lines) + "\n"


def report(trends, llm, day=None, top_n=15):
    day = day or date.today().isoformat()
    top = trends[:top_n]
    slim = [
        {k: t.get(k) for k in ("brand", "mentions", "growth", "is_new", "positive_share",
                               "public_parent", "ticker", "match_confidence", "why", "ownership_note")}
        for t in top
    ]
    try:
        notes = llm.ask_json(SYSTEM, PROMPT.format(trends=json.dumps(slim)))
    except Exception as exc:
        print(f"  reporter could not write notes: {exc}")
        notes = {}
    md = build_markdown(top, notes, day)
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.REPORT_DIR / f"{day}.md"
    path.write_text(md)
    return path
