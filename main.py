"""
Hantavirus Medical Fact-Checker

Takes a health claim, searches only trusted public-health sources (CDC and WHO)
with the Tavily API, and asks GPT-4o-mini to return a verdict and explanation
based on that evidence. The model decides what to search for and can search
several times. Sources are taken from the search results themselves,
so every cited link is a page that was actually retrieved.
"""

import json
import logging
import os
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

TRUSTED_DOMAINS = ["cdc.gov", "who.int"]
MODEL = "gpt-4o-mini"
VERDICTS = ["TRUE", "FALSE", "MISLEADING", "INSUFFICIENT_EVIDENCE"]

MAX_SEARCHES = 3
MAX_STEPS = MAX_SEARCHES + 3  # model calls allowed per claim; spare steps cover a malformed reply or two
REQUEST_TIMEOUT = 20  # seconds to wait on OpenAI or Tavily before giving up

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a medical fact checker specializing in hantavirus. "
    "You can only learn facts by calling search_trusted_sources, which searches CDC and WHO pages. "
    "Do NOT use your own knowledge. Search first, using short, specific queries. "
    "If a claim has several parts, or the first results do not settle it, search again with a different query. "
    "When you have enough evidence, call submit_verdict. "
    "Verdicts: TRUE, FALSE, MISLEADING (partly true but missing important context), "
    "or INSUFFICIENT_EVIDENCE (the sources do not cover it). "
    "Use FALSE only when the sources actively contradict the claim. If the sources simply never mention "
    "what the claim says, that is INSUFFICIENT_EVIDENCE, not FALSE, even though no evidence was found. "
    "You only judge claims about hantavirus: if the claim is about any other disease or topic, "
    "answer INSUFFICIENT_EVIDENCE with an explanation that this tool only covers hantavirus, even if the sources support the claim. "
    "Never guess. In source_ids, list only the numbers of results that support your explanation."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_trusted_sources",
            "description": "Search CDC and WHO web pages. Returns numbered results.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Short search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_verdict",
            "description": "Give the final answer once you have enough evidence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "verdict": {"type": "string", "enum": VERDICTS},
                    "explanation": {"type": "string", "description": "2-4 sentences based on the evidence"},
                    "source_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["verdict", "explanation", "source_ids"],
            },
        },
    },
]


def make_clients() -> Tuple[OpenAI, TavilyClient]:
    """Load API keys from .env and build the OpenAI and Tavily clients."""
    load_dotenv()  # loads OPENAI_API_KEY and TAVILY_API_KEY from .env
    return (
        OpenAI(timeout=REQUEST_TIMEOUT, max_retries=1),
        TavilyClient(api_key=os.getenv("TAVILY_API_KEY")),
    )


def search_trusted_sources(tavily: TavilyClient, claim: str) -> List[Dict]:
    """Search CDC and WHO for the claim and return the results (title, url, content)."""
    results = tavily.search(
        query=claim,
        timeout=REQUEST_TIMEOUT,
        search_depth="basic",  # 1 Tavily credit per search; "advanced" costs 2
        include_domains=TRUSTED_DOMAINS,
    )
    return [
        {"title": r.get("title", ""), "url": r["url"], "content": r["content"]}
        for r in results["results"]
    ]


def format_results(results: List[Dict], first_id: int) -> str:
    """Number each search result (continuing from first_id) so the model can cite it."""
    return "\n\n".join(
        f"[{i}] {s['title']} ({s['url']})\n{s['content']}"
        for i, s in enumerate(results, start=first_id)
    )


def insufficient(explanation: str) -> Dict:
    return {"verdict": "INSUFFICIENT_EVIDENCE", "explanation": explanation, "sources": []}


def check_claim(client: OpenAI, tavily: TavilyClient, claim: str) -> Dict:
    """Agent loop: the model searches CDC/WHO as many times as it needs (up to
    MAX_SEARCHES), then submits a verdict that cites the results it used."""
    sources: List[Dict] = []  # every result found, in order; id = position + 1
    searches = 0
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Claim: {claim}"},
    ]

    for _ in range(MAX_STEPS):
        # Once the search budget is used up, the only thing left to do is answer.
        if searches >= MAX_SEARCHES:
            tool_choice = {"type": "function", "function": {"name": "submit_verdict"}}
        else:
            tool_choice = "required"

        response = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            messages=messages,
            tools=TOOLS,
            tool_choice=tool_choice,
            parallel_tool_calls=False,
        )
        message = response.choices[0].message
        if not message.tool_calls:
            logger.warning("Model replied without calling a tool")
            return insufficient("The model did not give a usable answer.")
        messages.append(message)
        call = message.tool_calls[0]

        # The model writes the tool arguments as text, so they can be malformed.
        # Tell it what went wrong and let it try again (MAX_STEPS bounds the retries).
        try:
            args = json.loads(call.function.arguments)
            if not isinstance(args, dict):
                raise ValueError("arguments must be a JSON object")
        except ValueError:
            logger.warning("Malformed arguments for %s: %r", call.function.name, call.function.arguments[:200])
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": "Error: the arguments were not valid JSON. Call the tool again with valid arguments.",
            })
            continue

        if call.function.name == "submit_verdict":
            if not sources:
                return insufficient("No CDC or WHO evidence was gathered. This tool only checks claims about hantavirus.")
            verdict = str(args.get("verdict", "")).upper()
            if verdict not in VERDICTS:
                verdict = "INSUFFICIENT_EVIDENCE"
            cited = []
            for i in args.get("source_ids", []):
                if isinstance(i, int) and not isinstance(i, bool) and 1 <= i <= len(sources) and sources[i - 1] not in cited:
                    cited.append(sources[i - 1])
            return {
                "verdict": verdict,
                "explanation": args.get("explanation", ""),
                "sources": [{"title": s["title"], "url": s["url"]} for s in cited],
            }

        # Otherwise the model asked to search.
        searches += 1
        query = args.get("query") or claim
        results = search_trusted_sources(tavily, query)
        logger.info("Search %d/%d %r returned %d results", searches, MAX_SEARCHES, query, len(results))
        text = format_results(results, len(sources) + 1) if results else "No results found."
        sources.extend(results)
        messages.append({"role": "tool", "tool_call_id": call.id, "content": text})

    return insufficient("The fact-check did not finish.")


def print_result(result: Dict) -> None:
    print(f"\nVERDICT: {result['verdict']}")
    print(f"\nEXPLANATION: {result['explanation']}")
    print("\nSOURCES:")
    if not result["sources"]:
        print("  (none)")
    for s in result["sources"]:
        print(f"  - {s['title']}\n    {s['url']}")


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    client, tavily = make_clients()

    claim = input("Enter your claim: ")
    print_result(check_claim(client, tavily, claim))


if __name__ == "__main__":
    main()
