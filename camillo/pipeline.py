"""Runs the four agents in order: collect, analyze, match, report."""

import argparse
from datetime import date

from . import config
from .agents import collector, company_matcher, reporter, trend_analyst
from .llm import ClaudeClient


def run(subreddits=None, limit=config.POSTS_PER_SUBREDDIT, llm=None, fetch=None, delay=None, day=None):
    day = day or date.today().isoformat()
    llm = llm or ClaudeClient()

    print("1/4 Collector: pulling posts from Reddit")
    kwargs = {"subreddits": subreddits, "limit": limit}
    if fetch:
        kwargs["fetch"] = fetch
    if delay is not None:
        kwargs["delay"] = delay
    posts = collector.collect(**kwargs)
    if not posts:
        raise SystemExit("No posts collected. Check your internet connection and try again.")
    collector.save_snapshot(posts, day)

    print(f"2/4 Trend analyst: reading {len(posts)} posts")
    trends = trend_analyst.analyze(posts, llm, day)
    print(f"  found {len(trends)} brands")

    print("3/4 Company matcher: finding public parents and tickers")
    matched = company_matcher.match(trends, llm)

    print("4/4 Reporter: writing today's report")
    path = reporter.report(matched, llm, day)
    print(f"\nDone. Report saved to {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="Camillo: spot consumer trends on Reddit early.")
    parser.add_argument("--subreddits", nargs="+", help="subreddits to scan (default: built-in list)")
    parser.add_argument("--limit", type=int, default=config.POSTS_PER_SUBREDDIT, help="posts per subreddit")
    args = parser.parse_args()
    run(subreddits=args.subreddits, limit=args.limit)


if __name__ == "__main__":
    main()
