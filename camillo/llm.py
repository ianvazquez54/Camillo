"""Small wrapper around the Claude API that returns structured JSON.

It asks Claude to answer through a "tool", which makes the API hand back
already-parsed JSON instead of free text. If a reply still can't be used,
it retries once and then returns an empty result so one bad batch never
crashes the whole run.
"""

import json
import re

from . import config

RESPOND_TOOL = {
    "name": "respond",
    "description": "Return your answer as a JSON object in the exact shape the user asked for.",
    "input_schema": {"type": "object", "additionalProperties": True},
}


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

    def _ask_once(self, system, prompt, max_tokens):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=[RESPOND_TOOL],
            tool_choice={"type": "tool", "name": "respond"},
        )
        for block in response.content:
            if block.type == "tool_use" and isinstance(block.input, dict):
                return clean(block.input)
        # Fall back to reading any plain text reply
        text = "".join(getattr(b, "text", "") for b in response.content)
        return clean(parse_json(text))

    def ask_json(self, system, prompt, max_tokens=8000):
        """Send a prompt and return Claude's answer as a dict ({} if it fails twice)."""
        last_error = None
        for _ in range(2):
            try:
                result = self._ask_once(system, prompt, max_tokens)
                if isinstance(result, dict):
                    return result
                last_error = ValueError("reply was not a JSON object")
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = exc
        print(f"  warning: skipped one batch, Claude's reply could not be read ({last_error})")
        return {}


def clean(result):
    """Tidy up a reply so every agent gets lists of dicts.

    Sometimes Claude packs a list inside a string, like
    {"mentions": "[{\"brand\": \"HOKA\"}]"}. This unpacks those strings
    and drops any list items that aren't objects.
    """
    if not isinstance(result, dict):
        return result
    tidy = {}
    for key, value in result.items():
        if isinstance(value, str) and value.strip()[:1] in ("[", "{"):
            try:
                value = parse_json(value)
            except ValueError:
                pass
        if isinstance(value, dict) and key in ("mentions", "companies", "signals"):
            value = [value]
        if isinstance(value, list):
            value = [item for item in value if isinstance(item, dict)]
        tidy[key] = value
    return tidy


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
