"""Stage 4 harness: run every (model, condition) cell N times and log to CSV.

Protocol (per the design feedback):
  - fresh single-turn conversation per trial, fixed generation settings
  - execution order randomized across all trials (seeded, reproducible)
  - outcome parsed ONLY from the final-answer field, never from reasoning
  - outcomes: compliant / violating / invalid (invalids kept, not discarded)
  - each row logs the exact rendered prompt and a short hash of it

Usage:
  python run_experiment.py --smoke     # 1 trial per cell (50 calls), separate CSV
  python run_experiment.py             # full run, N trials per cell
"""

import argparse
import asyncio
import csv
import hashlib
import random
import re
import sys

import httpx

from client import call_model
from prompts import CONDITIONS, build_prompt

MODELS = [
    "deepseek/deepseek-r1-0528",
    "qwen/qwen3-30b-a3b-thinking-2507",
    "anthropic/claude-haiku-4.5",
    "openai/gpt-5-mini",
    "meta-llama/llama-3.3-70b-instruct",
]

N_TRIALS = 30
TEMPERATURE = 0.8
SEED = 7  # for the execution-order shuffle only

FIELDNAMES = [
    "model", "condition", "trial", "prompt_hash", "outcome", "parsed_integer",
    "raw_answer", "reasoning", "total_tokens", "cost_usd", "error", "prompt",
]


def classify(condition: str, content: str) -> tuple[str, int | None]:
    """Strict outcome classification from the final-answer text only."""
    if re.fullmatch(r"\s*\d+\s*", content or "") is None:
        return "invalid", None
    value = int(content.strip())
    if not 1 <= value <= 100:
        return "invalid", value
    answer_parity = "even" if value % 2 == 0 else "odd"
    requested = CONDITIONS[condition]["instruction"]
    return ("compliant" if answer_parity == requested else "violating"), value


async def run_trial(http: httpx.AsyncClient, model: str, condition: str,
                    trial: int) -> dict:
    prompt = build_prompt(condition)
    result = await call_model(http, model, prompt, temperature=TEMPERATURE)

    row = {
        "model": model,
        "condition": condition,
        "trial": trial,
        "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:12],
        "prompt": prompt,
        "error": result["error"] or "",
    }
    if result["error"]:
        row.update(outcome="error", parsed_integer=None, raw_answer="",
                   reasoning="", total_tokens=None, cost_usd=None)
        return row

    answer = (result["text"] or "").strip()
    outcome, value = classify(condition, answer)
    usage = (result["raw"] or {}).get("usage", {})
    row.update(
        outcome=outcome,
        parsed_integer=value,
        raw_answer=answer,
        reasoning=result["reasoning"] or "",
        total_tokens=usage.get("total_tokens"),
        cost_usd=usage.get("cost"),
    )
    return row


async def main(smoke: bool):
    n = 1 if smoke else N_TRIALS
    out_path = "results_smoke.csv" if smoke else "results.csv"

    trials = [
        (model, condition, t)
        for model in MODELS
        for condition in CONDITIONS
        for t in range(n)
    ]
    random.Random(SEED).shuffle(trials)
    print(f"Running {len(trials)} trials -> {out_path}")

    done = 0
    total_cost = 0.0

    async with httpx.AsyncClient() as http:
        tasks = [run_trial(http, m, c, t) for m, c, t in trials]
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for coro in asyncio.as_completed(tasks):
                row = await coro
                writer.writerow(row)
                f.flush()  # every finished trial is on disk immediately
                done += 1
                total_cost += row["cost_usd"] or 0.0
                if done % 25 == 0 or done == len(trials):
                    print(f"  {done}/{len(trials)} done, "
                          f"cost so far ${total_cost:.3f}", file=sys.stderr)

    errors = sum(1 for _ in open(out_path)) - 1  # just for the summary line
    print(f"Finished. {done} rows written to {out_path}. "
          f"Total measured cost: ${total_cost:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true",
                        help="1 trial per cell instead of N")
    args = parser.parse_args()
    asyncio.run(main(args.smoke))
