"""Small wrapper around the Claude API that asks for JSON and parses it."""

import json
import re

from . import config


class ClaudeClient:
    def __init__(self, api_key=None, model=None):
        import anthropic

        key = api_key or config.ANTHROPIC_API_KEY
        if not key:
            raise RuntimeError(
                "No ANTHROPIC_API_KEY found. Add it to your .env file (see .env.example)."
            )
        self.client = anthropic.Anthropic(api_key=key)
        self.model = model or config.MODEL

    def ask_json(self, system, prompt, max_tokens=4000):
        """Send a prompt and return the JSON object Claude replies with."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return parse_json(text)


def parse_json(text):
    """Pull the first JSON object or list out of a model reply."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
        if start == -1:
            raise ValueError(f"No JSON found in model reply: {text[:200]}")
        end = max(text.rfind("}"), text.rfind("]"))
        return json.loads(text[start : end + 1])
