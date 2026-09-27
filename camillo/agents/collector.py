"""Collector agent: pulls recent posts from Reddit.

Reddit blocked its free public .json pages in May 2026, so Camillo reads
posts from Arctic Shift, a free public archive of Reddit data used by
researchers (https://github.com/ArthurHeitmann/arctic_shift). No key needed.

The archive fills in scores and comment counts about 36 hours after a post
goes up, so by default the collector looks at posts from 2 to 4 days ago.
That makes the data about two days behind, which is fine for spotting
trends that build over weeks.
"""

import json
import time
from datetime import date

import requests

from .. import config

API_URL = "https://arctic-shift.photon-reddit.com/api/posts/search"
REQUEST_DELAY_SECONDS = 2
WINDOW_START = "4d"  # posts created after 4 days ago...
WINDOW_END = "2d"    # ...and before 2 days ago


def _get(session, params):
    headers = {"User-Agent": config.USER_AGENT}
    resp = session.get(API_URL, params=params, headers=headers, timeout=30)
    if resp.status_code == 429:
        # Rate limited: wait and try once more
        time.sleep(30)
        resp = session.get(API_URL, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if isinstance(body, dict):
        if body.get("error"):
            raise RuntimeError(body["error"])
        return body.get("data") or []
    return body or []


def fetch_subreddit(subreddit, limit=config.POSTS_PER_SUBREDDIT, session=None,
                    after=WINDOW_START, before=WINDOW_END):
    """Return the most upvoted posts from one subreddit in the time window."""
    session = session or requests.Session()
    raw = _get(session, {
        "subreddit": subreddit,
        "after": after,
        "before": before,
        "limit": 100,
        "sort": "desc",
    })

    posts = []
    for p in raw:
        if p.get("stickied") or p.get("over_18"):
            continue
        text = p.get("selftext") or ""
        if text in ("[removed]", "[deleted]"):
            text = ""
        sub = p.get("subreddit", subreddit)
        permalink = p.get("permalink") or f"/r/{sub}/comments/{p.get('id')}/"
        posts.append(
            {
                "id": p.get("id"),
                "subreddit": sub,
                "title": p.get("title", ""),
                "text": text[:1500],
                "score": p.get("score") or 0,
                "num_comments": p.get("num_comments") or 0,
                "created_utc": p.get("created_utc"),
                "url": "https://www.reddit.com" + permalink,
            }
        )
    # Keep the posts people engaged with most
    posts.sort(key=lambda p: p["score"] + 2 * p["num_comments"], reverse=True)
    return posts[:limit]


def collect(subreddits=None, limit=config.POSTS_PER_SUBREDDIT, fetch=fetch_subreddit, delay=REQUEST_DELAY_SECONDS):
    """Collect posts from every subreddit."""
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
