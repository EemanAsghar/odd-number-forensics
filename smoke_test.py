"""One tiny real API call to prove the key and client work.

Run:  python smoke_test.py
Cost: a fraction of a cent.
"""

import asyncio

import httpx

from client import call_model

# A cheap thinking model - also lets us check reasoning text comes through.
TEST_MODEL = "deepseek/deepseek-r1-distill-llama-70b"


async def main():
    async with httpx.AsyncClient() as http:
        result = await call_model(http, TEST_MODEL, "What is 7 + 5? Answer with just the number.")

    if result["error"]:
        print("FAILED:", result["error"])
        return

    print("Answer:", result["text"].strip())
    if result["reasoning"]:
        print("\nThinking text (first 300 chars):")
        print(result["reasoning"][:300])
    else:
        print("\nNo thinking text returned by this model.")


if __name__ == "__main__":
    asyncio.run(main())
