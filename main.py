"""
Hantavirus Medical Fact-Checker

Takes a health claim, searches only trusted public-health sources (CDC and WHO)
with the Tavily API, and asks GPT-4o-mini to return a verdict, explanation,
and sources based on that evidence.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

TRUSTED_DOMAINS = ["cdc.gov", "who.int"]
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are a medical fact checker specializing in hantavirus. "
    "Use ONLY the search results provided to evaluate the claim. "
    "Respond with: "
    "1) VERDICT: TRUE / FALSE / MISLEADING "
    "2) EXPLANATION: why, based on the evidence "
    "3) SOURCES: cite the CDC or WHO sources from the search results that support your answer. "
    "If the search results do not contain enough information, say so instead of guessing."
)


def search_trusted_sources(tavily: TavilyClient, claim: str) -> str:
    """Search CDC and WHO for the claim and return the combined result text."""
    results = tavily.search(
        query=claim,
        search_depth="advanced",
        include_domains=TRUSTED_DOMAINS,
    )
    return "\n".join(r["content"] for r in results["results"])


def fact_check(client: OpenAI, claim: str, context: str) -> str:
    """Ask the model to evaluate the claim using only the retrieved context."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Claim: {claim}\n\nSearch results from CDC/WHO:\n{context}",
            },
        ],
    )
    return response.choices[0].message.content


def main() -> None:
    load_dotenv()  # loads OPENAI_API_KEY and TAVILY_API_KEY from .env
    client = OpenAI()
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    claim = input("Enter your claim: ")
    context = search_trusted_sources(tavily, claim)
    print(fact_check(client, claim, context))


if __name__ == "__main__":
    main()
