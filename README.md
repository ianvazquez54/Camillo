# Camillo

Camillo is an AI research tool I'm building to spot consumer trends early. It scans Reddit for products and brands people are starting to talk about, then connects those trends to the public companies behind them, ideally before the rest of the market notices.

## How it works

Camillo uses multiple AI agents, each with its own job:

- **Collector:** pulls posts and comments from Reddit
- **Trend analyst:** uses the Claude API to find products and brands getting more buzz over time
- **Company matcher:** links each trend to its public parent company and stock ticker
- **Reporter:** summarizes the strongest signals into a short daily report

## Built with

- Python
- Claude API (Anthropic)
- Reddit API

## Status

In progress. The core pipeline is set up, and I'm currently connecting the Reddit data source and wiring the agents together end to end.

## Why I built it

I'm a finance student at UNCG and I invest on my own. I wanted to learn how AI agents actually work by building something I'd use myself.


