"""Stage 3 probe: one D1 call per candidate model.

For each model, reports:
  - whether the final answer parses as a single integer
  - whether reasoning text came back, and how long it is
  - token usage and the measured cost (OpenRouter's usage accounting)

Run:  python probe_models.py
"""

import asyncio

import httpx

from client import call_model
from prompts import build_prompt

CANDIDATES = [
    "deepseek/deepseek-r1-0528",
    "qwen/qwen3-30b-a3b-thinking-2507",
    "anthropic/claude-haiku-4.5",
    "openai/gpt-5-mini",
    "meta-llama/llama-3.3-70b-instruct",
]

PROMPT = build_prompt("D1_reward_conflict")


async def probe(client: httpx.AsyncClient, model: str) -> dict:
    result = await call_model(client, model, PROMPT)
    row = {"model": model}
    if result["error"]:
        row["status"] = f"ERROR: {result['error']}"
        return row

    text = (result["text"] or "").strip()
    reasoning = result["reasoning"]
    usage = (result["raw"] or {}).get("usage", {})

    row["status"] = "ok"
    row["answer"] = text[:60]
    row["parses_as_int"] = text.isdigit()
    row["reasoning_chars"] = len(reasoning) if reasoning else 0
    row["total_tokens"] = usage.get("total_tokens")
    row["cost_usd"] = usage.get("cost")  # needs usage accounting enabled
    return row


async def main():
    async with httpx.AsyncClient() as http:
        rows = await asyncio.gather(*(probe(http, m) for m in CANDIDATES))

    for row in rows:
        print("-" * 70)
        for key, value in row.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
