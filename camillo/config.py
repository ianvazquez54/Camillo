"""Settings for Camillo. Secrets come from the .env file, never from code."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Folders where Camillo keeps its history and reports
DATA_DIR = ROOT / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
COMPANY_CACHE = DATA_DIR / "company_cache.json"
REPORT_DIR = ROOT / "reports"

# Subreddits where people talk about what they buy and use
DEFAULT_SUBREDDITS = [
    "BuyItForLife",
    "SkincareAddiction",
    "Sneakers",
    "HydroHomies",
    "EatCheapAndHealthy",
    "fitness",
    "gadgets",
    "Coffee",
    "MakeupAddiction",
    "Frugal",
]

POSTS_PER_SUBREDDIT = 50

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("CAMILLO_MODEL", "claude-sonnet-5")

# Reddit asks every script to identify itself with a descriptive User-Agent
USER_AGENT = os.getenv(
    "CAMILLO_USER_AGENT",
    "python:camillo-trend-research:v0.1 (personal research project)",
)
