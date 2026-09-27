"""Collector agent: pulls recent posts from Reddit.

Uses Reddit's public .json pages (add .json to any subreddit URL), so no
Reddit API registration is needed. Reddit rate limits these, so the
collector waits between requests.
"""

import json
import time
from datetime import date

import requests

from .. import config

REQUEST_DELAY_SECONDS = 3


def fetch_subreddit(subreddit, limit=config.POSTS_PER_SUBREDDIT, sort="top", period="day", session=None):
    """Return a list of simplified posts from one subreddit."""
    session = session or requests.Session()
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    params = {"limit": min(limit, 100), "t": period}
    resp = session.get(url, params=params, headers={"User-Agent": config.USER_AGENT}, timeout=20)
    if resp.status_code == 429:
        # Too many requests: wait and try once more
        time.sleep(30)
        resp = session.get(url, params=params, headers={"User-Agent": config.USER_AGENT}, timeout=20)
    resp.raise_for_status()

    posts = []
    for child in resp.json().get("data", {}).get("children", []):
        p = child.get("data", {})
        if p.get("stickied") or p.get("over_18"):
            continue
        posts.append(
            {
                "id": p.get("id"),
                "subreddit": p.get("subreddit", subreddit),
                "title": p.get("title", ""),
                "text": (p.get("selftext") or "")[:1500],
                "score": p.get("score", 0),
                "num_comments": p.get("num_comments", 0),
                "created_utc": p.get("created_utc"),
                "url": "https://www.reddit.com" + p.get("permalink", ""),
            }
        )
    return posts


def collect(subreddits=None, limit=config.POSTS_PER_SUBREDDIT, fetch=fetch_subreddit, delay=REQUEST_DELAY_SECONDS):
    """Collect posts from every subreddit and save today's snapshot."""
    subreddits = subreddits or config.DEFAULT_SUBREDDITS
    all_posts = []
    for i, sub in enumerate(subreddits):
        try:
            posts = fetch(sub, limit=limit)
            all_posts.extend(posts)
            print(f"  collected {len(posts):>3} posts from r/{sub}")
        except Exception as exc:  # keep going if one subreddit fails
            print(f"  skipped r/{sub}: {exc}")
        if delay and i < len(subreddits) - 1:
            time.sleep(delay)
    return all_posts


def save_snapshot(posts, day=None):
    day = day or date.today().isoformat()
    config.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.SNAPSHOT_DIR / f"{day}-posts.json"
    path.write_text(json.dumps(posts, indent=2))
    return path
