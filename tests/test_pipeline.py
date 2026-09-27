"""Runs the full pipeline offline with sample posts and a fake Claude client."""

import json

import pytest

from camillo import config, pipeline
from camillo.agents import collector, company_matcher, trend_analyst
from camillo.llm import parse_json

SAMPLE_POSTS = {
    "BuyItForLife": [
        {"id": "a1", "subreddit": "BuyItForLife", "title": "My Stanley Quencher survived 3 years",
         "text": "Still going strong", "score": 900, "num_comments": 120, "created_utc": 0, "url": "https://reddit.com/a1"},
        {"id": "a2", "subreddit": "BuyItForLife", "title": "Owala FreeSip vs Stanley?",
         "text": "Owala doesn't leak", "score": 400, "num_comments": 80, "created_utc": 0, "url": "https://reddit.com/a2"},
    ],
    "Sneakers": [
        {"id": "b1", "subreddit": "Sneakers", "title": "Hoka Clifton 10 is everywhere now",
         "text": "Everyone at my gym has them", "score": 1500, "num_comments": 300, "created_utc": 0, "url": "https://reddit.com/b1"},
        {"id": "b2", "subreddit": "Sneakers", "title": "On Cloud restock", "text": "",
         "score": 200, "num_comments": 40, "created_utc": 0, "url": "https://reddit.com/b2"},
    ],
}


class FakeLLM:
    """Answers like Claude would, based on which agent is asking."""

    def __init__(self):
        self.calls = []

    def ask_json(self, system, prompt, max_tokens=4000):
        self.calls.append(system[:30])
        if "trend analyst" in system:
            ids = {p["id"] for p in json.loads(prompt.split("Posts:\n", 1)[1])}
            m = []
            if "a1" in ids:
                m.append({"brand": "Stanley", "product": "Quencher", "post_ids": ["a1", "a2"], "sentiment": "positive", "why": "Durable"})
            if "a2" in ids:
                m.append({"brand": "Owala", "product": "FreeSip", "post_ids": ["a2"], "sentiment": "positive", "why": "No leaks"})
            if "b1" in ids:
                m.append({"brand": "HOKA", "product": "Clifton 10", "post_ids": ["b1"], "sentiment": "positive", "why": "Gym favorite"})
            if "b2" in ids:
                m.append({"brand": "On", "product": "Cloud", "post_ids": ["b2"], "sentiment": "mixed", "why": "Restock"})
            return {"mentions": m}
        if "equity research" in system:
            table = {
                "Stanley": ("Pacific Market International", None, None, "Private"),
                "Owala": ("Trove Brands", None, None, "Private"),
                "HOKA": ("Deckers Outdoor", "Deckers Outdoor", "DECK", "Owned since 2013"),
                "On": ("On Holding", "On Holding", "ONON", "Public since 2021"),
            }
            brands = json.loads(prompt.split("Brands: ", 1)[1])
            return {"companies": [
                {"brand": b, "owner": table[b][0], "public_parent": table[b][1], "ticker": table[b][2],
                 "exchange": "NYSE" if table[b][2] else None, "confidence": "high", "note": table[b][3]}
                for b in brands]}
        return {"headline": "Running shoes lead today.",
                "signals": [{"brand": "HOKA", "ticker": "DECK", "take": "Strong buzz. Watch next earnings."}]}


@pytest.fixture
def tmp_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SNAPSHOT_DIR", tmp_path / "data" / "snapshots")
    monkeypatch.setattr(config, "COMPANY_CACHE", tmp_path / "data" / "company_cache.json")
    monkeypatch.setattr(config, "REPORT_DIR", tmp_path / "reports")
    return tmp_path


def fake_fetch(sub, limit=50):
    return SAMPLE_POSTS.get(sub, [])


def test_full_run_writes_report(tmp_paths):
    llm = FakeLLM()
    path = pipeline.run(subreddits=list(SAMPLE_POSTS), llm=llm, fetch=fake_fetch, delay=0, day="2026-09-25")
    text = path.read_text()
    assert "HOKA" in text and "DECK" in text
    assert "Stanley" in text and "Private" in text
    assert "Running shoes lead today." in text


def test_growth_compares_with_earlier_days(tmp_paths):
    llm = FakeLLM()
    # Day 1: only BuyItForLife. Day 2: everything.
    pipeline.run(subreddits=["BuyItForLife"], llm=llm, fetch=fake_fetch, delay=0, day="2026-09-24")
    pipeline.run(subreddits=list(SAMPLE_POSTS), llm=llm, fetch=fake_fetch, delay=0, day="2026-09-25")
    brands = json.loads((config.SNAPSHOT_DIR / "2026-09-25-brands.json").read_text())
    history = trend_analyst.load_history("2026-09-25")
    scored = {b["brand"]: b for b in trend_analyst.score_trends(brands, history)}
    assert scored["Stanley"]["is_new"] is False and scored["Stanley"]["growth"] == 1.0
    assert scored["HOKA"]["is_new"] is True


def test_company_lookups_are_cached(tmp_paths):
    llm = FakeLLM()
    trends = [{"brand": "HOKA"}, {"brand": "On"}]
    company_matcher.match(trends, llm)
    company_matcher.match([{"brand": "HOKA"}], llm)
    assert llm.calls.count(llm.calls[0]) == 1  # second run used the cache


def test_collector_skips_failed_subreddit(tmp_paths):
    def flaky(sub, limit=50):
        if sub == "bad":
            raise RuntimeError("503")
        return SAMPLE_POSTS["Sneakers"]
    posts = collector.collect(["bad", "Sneakers"], fetch=flaky, delay=0)
    assert len(posts) == 2


def test_parse_json_handles_code_fences():
    assert parse_json('Here you go:\n```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Sure! {"a": [1, 2]} hope that helps') == {"a": [1, 2]}
