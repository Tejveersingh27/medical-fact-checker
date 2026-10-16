"""
Hantavirus Medical Fact-Checker

Takes a health claim, searches only trusted public-health sources (CDC and WHO)
with the Tavily API, and asks GPT-4o-mini to return a verdict and explanation
based on that evidence. Sources are taken from the search results themselves,
so every cited link is a page that was actually retrieved.
"""

import json
import os
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

TRUSTED_DOMAINS = ["cdc.gov", "who.int"]
MODEL = "gpt-4o-mini"
VERDICTS = ["TRUE", "FALSE", "MISLEADING", "INSUFFICIENT_EVIDENCE"]

SYSTEM_PROMPT = (
    "You are a medical fact checker specializing in hantavirus. "
    "You will be given a claim and numbered search results from the CDC and WHO. "
    "Use ONLY those search results to evaluate the claim. "
    "Reply with a JSON object with these keys:\n"
    '  "verdict": one of "TRUE", "FALSE", "MISLEADING", "INSUFFICIENT_EVIDENCE"\n'
    '  "explanation": 2-4 sentences explaining why, based on the evidence\n'
    '  "source_ids": list of the numbers of the search results that support your explanation\n'
    "Use MISLEADING when the claim is partly true but leaves out important context. "
    "Use INSUFFICIENT_EVIDENCE if the search results do not cover the claim "
    "or the claim is not about hantavirus. Never guess."
)


def search_trusted_sources(tavily: TavilyClient, claim: str) -> List[Dict]:
    """Search CDC and WHO for the claim and return the results (title, url, content)."""
    results = tavily.search(
        query=claim,
        search_depth="advanced",
        include_domains=TRUSTED_DOMAINS,
    )
    return [
        {"title": r.get("title", ""), "url": r["url"], "content": r["content"]}
        for r in results["results"]
    ]


def format_context(sources: List[Dict]) -> str:
    """Number each search result so the model can refer to it by id."""
    return "\n\n".join(
        f"[{i}] {s['title']} ({s['url']})\n{s['content']}"
        for i, s in enumerate(sources, start=1)
    )


def fact_check(client: OpenAI, claim: str, sources: List[Dict]) -> Dict:
    """Ask the model to evaluate the claim using only the retrieved sources."""
    if not sources:
        return {
            "verdict": "INSUFFICIENT_EVIDENCE",
            "explanation": "No CDC or WHO pages were found for this claim.",
            "sources": [],
        }

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Claim: {claim}\n\nSearch results:\n{format_context(sources)}",
            },
        ],
    )
    result = json.loads(response.choices[0].message.content)

    verdict = str(result.get("verdict", "")).upper()
    if verdict not in VERDICTS:
        verdict = "INSUFFICIENT_EVIDENCE"

    # Map the model's ids back to the real results; ignore any id that doesn't exist.
    cited = []
    for i in result.get("source_ids", []):
        if isinstance(i, int) and 1 <= i <= len(sources) and sources[i - 1] not in cited:
            cited.append(sources[i - 1])

    return {
        "verdict": verdict,
        "explanation": result.get("explanation", ""),
        "sources": [{"title": s["title"], "url": s["url"]} for s in cited],
    }


def check_claim(client: OpenAI, tavily: TavilyClient, claim: str) -> Dict:
    """Run the full pipeline: search trusted sources, then fact-check."""
    return fact_check(client, claim, search_trusted_sources(tavily, claim))


def print_result(result: Dict) -> None:
    print(f"\nVERDICT: {result['verdict']}")
    print(f"\nEXPLANATION: {result['explanation']}")
    print("\nSOURCES:")
    if not result["sources"]:
        print("  (none)")
    for s in result["sources"]:
        print(f"  - {s['title']}\n    {s['url']}")


def main() -> None:
    load_dotenv()  # loads OPENAI_API_KEY and TAVILY_API_KEY from .env
    client = OpenAI()
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    claim = input("Enter your claim: ")
    print_result(check_claim(client, tavily, claim))


if __name__ == "__main__":
    main()
