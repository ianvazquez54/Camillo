"""Company matcher agent: links each brand to the public company that owns it."""

import json

from .. import config

SYSTEM = (
    "You are an equity research assistant. For each consumer brand, identify the "
    "company that owns it and whether that company (or its ultimate parent) is "
    "publicly traded. Be careful: if you are not confident, say so. Reply with JSON only."
)

PROMPT = """For each brand below, return:
- "brand": the brand name exactly as given
- "owner": the company that owns the brand
- "public_parent": the publicly traded company at the top of the ownership chain, or null if privately held
- "ticker": the main stock ticker for the public parent, or null
- "exchange": e.g. "NYSE", "NASDAQ", "TSE", or null
- "confidence": "high", "medium", or "low"
- "note": one short sentence (e.g. "Owned by X since 2021" or "Private, backed by VC")

Return {{"companies": [ ... ]}}.

Brands: {brands}"""


def _load_cache():
    if config.COMPANY_CACHE.exists():
        return json.loads(config.COMPANY_CACHE.read_text())
    return {}


def _save_cache(cache):
    config.COMPANY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    config.COMPANY_CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))


def match(trends, llm, top_n=25):
    """Add ownership and ticker info to the top trends. Results are cached
    so the same brand is only looked up once."""
    cache = _load_cache()
    top = trends[:top_n]
    unknown = [t["brand"] for t in top if t["brand"].lower() not in cache]
    if unknown:
        result = llm.ask_json(SYSTEM, PROMPT.format(brands=json.dumps(unknown)))
        for c in result.get("companies", []):
            if c.get("brand"):
                cache[c["brand"].lower()] = c
        _save_cache(cache)

    for t in top:
        info = cache.get(t["brand"].lower(), {})
        t["owner"] = info.get("owner")
        t["public_parent"] = info.get("public_parent")
        t["ticker"] = info.get("ticker")
        t["exchange"] = info.get("exchange")
        t["match_confidence"] = info.get("confidence", "low")
        t["ownership_note"] = info.get("note", "")
    return top
