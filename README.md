# Camillo

Camillo is an AI research tool I'm building to spot consumer trends early. It scans Reddit for products and brands people are starting to talk about, then connects those trends to the public companies behind them, ideally before the rest of the market notices.

## How it works

Camillo uses multiple AI agents, each with its own job:

- **Collector:** pulls posts and comments from Reddit
- **Trend analyst:** uses the Claude API to find products and brands getting more buzz over time
- **Company matcher:** links each trend to its public parent company and stock ticker
- **Reporter:** summarizes the strongest signals into a short daily report

Each run saves a snapshot, so the trend analyst can compare today's mentions with the previous week and flag brands that are growing or showing up for the first time.

## Built with

- Python
- Claude API (Anthropic)
- Reddit data (public JSON pages)

## Run it

```
pip install -r requirements.txt
cp .env.example .env        # then add your Anthropic API key to .env
python -m camillo
```

Scan specific subreddits:

```
python -m camillo --subreddits Sneakers SkincareAddiction --limit 25
```

The report is saved to `reports/<date>.md`. Run it once a day to build up history for the growth numbers.

## Tests

```
pip install pytest
python -m pytest
```

The tests run the whole pipeline offline with sample posts and a stand-in for the Claude API.

## Status

In progress. All four agents are built and tested end to end with sample data. Next up: daily runs on live Reddit data and tracking whether early signals line up with later company results.

## Why I built it

I'm a finance student at UNCG and I invest on my own. I wanted to learn how AI agents actually work by building something I'd use myself.

_Research only, not investment advice._
