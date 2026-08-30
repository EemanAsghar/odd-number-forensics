"""Async OpenRouter client for the reward-hacking experiment.

Reads the API key from the OPENROUTER_API_KEY environment variable.
Never hardcode or print the key.
"""

import asyncio
import os

import httpx

API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Knobs you may want to change later:
MAX_CONCURRENT = 8      # how many requests run at the same time
MAX_TOKENS = 8000       # hard cap on each answer (thinking included). Set high:
                        # truncating long deliberation censors exactly the
                        # conflicted (likely-violating) trials, biasing rates down.
MAX_RETRIES = 4         # how many times to retry a failed request
TIMEOUT_SECONDS = 120   # thinking models can be slow, so be patient

_semaphore = asyncio.Semaphore(MAX_CONCURRENT)


def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        # Fall back to a .env file sitting next to this script.
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("OPENROUTER_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip("'\"")
    if not key or key == "paste-your-key-here":
        raise RuntimeError(
            "No API key found. Open the .env file in this folder and replace\n"
            "'paste-your-key-here' with your real OpenRouter key, then run again."
        )
    return key


async def call_model(
    client: httpx.AsyncClient,
    model: str,
    prompt: str,
    temperature: float = 0.8,
) -> dict:
    """Send one prompt to one model. Returns a dict with:
    text       - the model's final answer
    reasoning  - its thinking text, or None if the model doesn't share it
    raw        - the full JSON response, so we never lose information
    error      - an error message if all retries failed, else None
    """
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": MAX_TOKENS,
        "reasoning": {"enabled": True},  # ask for thinking text where supported
        "usage": {"include": True},      # report token counts and cost per call
    }
    headers = {"Authorization": f"Bearer {get_api_key()}"}

    async with _semaphore:  # wait here if 8 requests are already running
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.post(
                    API_URL, json=payload, headers=headers, timeout=TIMEOUT_SECONDS
                )
                if resp.status_code in (429, 500, 502, 503):
                    # Temporary problem: wait longer each time (2s, 4s, 8s...) and retry
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                message = data["choices"][0]["message"]
                return {
                    "text": message.get("content") or "",
                    "reasoning": message.get("reasoning"),
                    "raw": data,
                    "error": None,
                }
            except httpx.HTTPError as exc:
                if attempt == MAX_RETRIES - 1:
                    return {"text": "", "reasoning": None, "raw": None,
                            "error": f"{type(exc).__name__}: {exc}"}
                await asyncio.sleep(2 ** (attempt + 1))

    return {"text": "", "reasoning": None, "raw": None,
            "error": "All retries failed (rate limit or server trouble)."}
