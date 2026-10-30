"""
Runs the fact-checker on a set of labelled claims and reports accuracy.

Every claim has exactly one correct verdict, chosen with this rule from what the
CDC and WHO pages say:
  TRUE                  fully supported by CDC/WHO
  FALSE                 the main thing the claim asserts is contradicted
  MISLEADING            partly true, but leaves out something that leads to the wrong conclusion
  INSUFFICIENT_EVIDENCE CDC/WHO pages do not address it, or it is not about hantavirus
                        (the off-topic case is a design choice: this tool only judges hantavirus)
"""

from main import check_claim, make_clients

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
    ("Symptoms of HPS can appear as early as 1 week and as late as 8 weeks after exposure.", ["TRUE"]),
    ("Early symptoms of HPS include fever, fatigue, and muscle aches.", ["TRUE"]),
    ("Sweeping or vacuuming rodent droppings is the safest way to clean them up.", ["FALSE"]),
    ("Spraying rodent droppings with a bleach solution before cleaning reduces risk.", ["TRUE"]),
    ("Cats and dogs commonly give hantavirus to their owners.", ["FALSE"]),
    ("Hantavirus pulmonary syndrome was first identified in the Four Corners region in 1993.", ["TRUE"]),
    ("Hantavirus only exists in the United States.", ["FALSE"]),
    ("Hantavirus is a type of bacteria.", ["FALSE"]),
    ("Thousands of people in the US get hantavirus every year.", ["FALSE"]),
    ("Hantavirus is not contagious between humans.", ["MISLEADING"]),
    ("Sealing holes in your home to keep rodents out lowers your risk of hantavirus.", ["TRUE"]),
    # Harder: multi-part, half-true, and off-topic claims
    ("Hantavirus is spread by rodents and there is a vaccine that prevents it.", ["FALSE"]),
    ("Hantavirus only spreads from rodents, never between people, anywhere in the world.", ["FALSE"]),
    ("Hantavirus is mild and most people recover without hospital care.", ["FALSE"]),
    ("Only people who live in rural areas can get hantavirus.", ["FALSE"]),
    ("Measles spreads through the air.", ["INSUFFICIENT_EVIDENCE"]),
    ("Drinking bleach cures hantavirus.", ["FALSE"]),
    # Added later: labels were written before running the tool on them
    ("Hantavirus is rare in the United States, so precautions when cleaning up rodent droppings are unnecessary.", ["MISLEADING"]),
    ("Most people who get hantavirus pulmonary syndrome survive, so it is not a dangerous illness.", ["MISLEADING"]),
    ("Hantavirus infections in the United States peak in winter.", ["FALSE"]),
    ("A hantavirus test taken within the first day of symptoms is always reliable.", ["FALSE"]),
    ("Hantavirus can spread through a rodent bite or scratch, although this is rare.", ["TRUE"]),
    ("People with blood type O are more likely to develop severe hantavirus disease.", ["INSUFFICIENT_EVIDENCE"]),
]


def main() -> None:
    client, tavily = make_clients()

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
