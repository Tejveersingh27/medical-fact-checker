"""
Runs the fact-checker on a set of labelled claims and reports accuracy.

Each claim lists the verdicts we accept as correct (some claims are
reasonably either FALSE or MISLEADING). Labels are based on CDC/WHO guidance.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

from main import check_claim

CLAIMS = [
    ("Hantavirus spreads to people through contact with rodent urine, droppings, or saliva.", ["TRUE"]),
    ("Hantavirus spreads easily from person to person.", ["FALSE"]),
    ("The Andes virus in South America can spread between people.", ["TRUE"]),
    ("The deer mouse is the main carrier of hantavirus in the United States.", ["TRUE"]),
    ("Hantavirus is spread by mosquito bites.", ["FALSE"]),
    ("Antibiotics can cure a hantavirus infection.", ["FALSE"]),
    ("There is an FDA-approved vaccine for hantavirus.", ["FALSE"]),
    ("Hantavirus infection is always fatal.", ["FALSE"]),
    ("About 38% of people who develop hantavirus pulmonary syndrome die.", ["TRUE"]),
    ("Symptoms of HPS usually appear 1 to 8 weeks after exposure.", ["TRUE"]),
    ("Early symptoms of HPS include fever, fatigue, and muscle aches.", ["TRUE"]),
    ("Sweeping or vacuuming rodent droppings is the safest way to clean them up.", ["FALSE"]),
    ("Spraying rodent droppings with a bleach solution before cleaning reduces risk.", ["TRUE"]),
    ("Cats and dogs commonly give hantavirus to their owners.", ["FALSE"]),
    ("Hantavirus pulmonary syndrome was first identified in the Four Corners region in 1993.", ["TRUE"]),
    ("Hantavirus only exists in the United States.", ["FALSE"]),
    ("Hantavirus is a type of bacteria.", ["FALSE"]),
    ("Thousands of people in the US get hantavirus every year.", ["FALSE", "MISLEADING"]),
    ("Hantavirus is not contagious between humans.", ["MISLEADING", "FALSE"]),
    ("Sealing holes in your home to keep rodents out lowers your risk of hantavirus.", ["TRUE"]),
    # Harder: multi-part, half-true, and off-topic claims
    ("Hantavirus is spread by rodents and there is a vaccine that prevents it.", ["FALSE", "MISLEADING"]),
    ("Hantavirus only spreads from rodents, never between people, anywhere in the world.", ["FALSE", "MISLEADING"]),
    ("Hantavirus is mild and most people recover without hospital care.", ["FALSE", "MISLEADING"]),
    ("Only people who live in rural areas can get hantavirus.", ["FALSE", "MISLEADING"]),
    ("Measles spreads through the air.", ["INSUFFICIENT_EVIDENCE"]),
    ("Drinking bleach cures hantavirus.", ["FALSE"]),
]


def main() -> None:
    load_dotenv()
    client = OpenAI()
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    correct = with_sources = 0
    for claim, expected in CLAIMS:
        result = check_claim(client, tavily, claim)
        ok = result["verdict"] in expected
        correct += ok
        with_sources += bool(result["sources"])
        mark = "PASS" if ok else "FAIL"
        print(f"{mark}  got {result['verdict']:<21} expected {'/'.join(expected):<16} {claim}")

    n = len(CLAIMS)
    print(f"\nAccuracy: {correct}/{n} ({correct / n:.0%})")
    print(f"Answers with at least one source: {with_sources}/{n}")


if __name__ == "__main__":
    main()
