"""Trend analyst agent: finds the products and brands people are talking about,
then compares today's buzz with earlier days to see what is growing."""

import json
from datetime import date

from .. import config

SYSTEM = (
    "You are a consumer trend analyst. You read Reddit posts and pull out specific, "
    "named consumer products and brands that people are recommending, buying, or "
    "excited about. Ignore generic categories (like 'running shoes'), retailers "
    "mentioned only as places to shop, and anything you are unsure is a real brand. "
    "Reply with JSON only."
)

PROMPT = """Here are Reddit posts as JSON. For each distinct brand or product, return:
- "brand": the brand name, spelled the way the company spells it
- "product": the specific product if one is named, else null
- "post_ids": ids of the posts that mention it
- "sentiment": "positive", "mixed", or "negative"
- "why": one short sentence on why people are talking about it

Return {{"mentions": [ ... ]}}.

Posts:
{posts}"""

BATCH_SIZE = 40


def extract_mentions(posts, llm):
    """Ask Claude to find brand mentions, a batch of posts at a time."""
    mentions = []
    for start in range(0, len(posts), BATCH_SIZE):
        batch = posts[start : start + BATCH_SIZE]
        slim = [{"id": p["id"], "title": p["title"], "text": p["text"][:600]} for p in batch]
        result = llm.ask_json(SYSTEM, PROMPT.format(posts=json.dumps(slim)))
        mentions.extend(result.get("mentions", []))
    return mentions


def summarize(mentions, posts):
    """Combine mentions by brand and add up how much engagement they got."""
    by_id = {p["id"]: p for p in posts}
    brands = {}
    for m in mentions:
        name = (m.get("brand") or "").strip()
        if not name:
            continue
        key = name.lower()
        b = brands.setdefault(
            key,
            {"brand": name, "products": set(), "post_ids": set(), "sentiment": [], "why": [], "subreddits": set()},
        )
        if m.get("product"):
            b["products"].add(m["product"])
        for pid in m.get("post_ids", []):
            if pid in by_id:
                b["post_ids"].add(pid)
                b["subreddits"].add(by_id[pid]["subreddit"])
        b["sentiment"].append(m.get("sentiment", "mixed"))
        if m.get("why"):
            b["why"].append(m["why"])

    summary = []
    for b in brands.values():
        if not b["post_ids"]:
            continue
        engagement = sum(by_id[i]["score"] + 2 * by_id[i]["num_comments"] for i in b["post_ids"])
        positive = b["sentiment"].count("positive") / max(len(b["sentiment"]), 1)
        summary.append(
            {
                "brand": b["brand"],
                "products": sorted(b["products"]),
                "mentions": len(b["post_ids"]),
                "engagement": engagement,
                "positive_share": round(positive, 2),
                "subreddits": sorted(b["subreddits"]),
                "why": b["why"][0] if b["why"] else "",
                "example_posts": [by_id[i]["url"] for i in list(b["post_ids"])[:3]],
            }
        )
    return summary


def load_history(before_day, days=7):
    """Load brand summaries saved on earlier days."""
    history = {}
    if not config.SNAPSHOT_DIR.exists():
        return history
    files = sorted(config.SNAPSHOT_DIR.glob("*-brands.json"))
    earlier = [f for f in files if f.name[:10] < before_day][-days:]
    for f in earlier:
        for b in json.loads(f.read_text()):
            history.setdefault(b["brand"].lower(), []).append(b["mentions"])
    return history


def score_trends(summary, history):
    """Growth = today's mentions vs the average of earlier days.
    Brands never seen before count as new."""
    for b in summary:
        past = history.get(b["brand"].lower(), [])
        baseline = sum(past) / len(past) if past else 0
        b["baseline_mentions"] = round(baseline, 2)
        b["is_new"] = not past
        b["growth"] = round(b["mentions"] / baseline, 2) if baseline else None
        growth_factor = b["growth"] if b["growth"] else 2.0  # new brands get a boost
        b["trend_score"] = round(
            b["mentions"] * growth_factor * (0.5 + b["positive_share"]) * (1 + b["engagement"] / 1000), 2
        )
    return sorted(summary, key=lambda b: b["trend_score"], reverse=True)


def analyze(posts, llm, day=None):
    day = day or date.today().isoformat()
    mentions = extract_mentions(posts, llm)
    summary = summarize(mentions, posts)
    config.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    (config.SNAPSHOT_DIR / f"{day}-brands.json").write_text(json.dumps(summary, indent=2))
    return score_trends(summary, load_history(day))
