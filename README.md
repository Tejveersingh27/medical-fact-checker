# Hantavirus Medical Fact-Checker

An AI agent that fact-checks health claims about hantavirus. It searches **only trusted public-health sources (CDC and WHO)**, decides for itself what to look up, and returns a verdict, an explanation, and links to the pages it actually used. It runs as a command-line tool or as a small web app.

> ⚠️ This is a learning prototype, not a medical tool. It does not provide medical advice.

---

## Why I built this

Health misinformation spreads quickly, and large language models can "hallucinate" confident answers that aren't true. Instead of letting the model answer from memory, this agent **retrieves real information from the CDC and WHO first** and only lets the model reason from that evidence. Grounding answers in trusted sources is the core idea behind retrieval-augmented generation (RAG).

## How it works

```
Claim (user input)
      │
      ▼
GPT-4o-mini agent  ◄───────────────┐
      │                            │
      ├─ search_trusted_sources ───┘   (up to 3 searches, cdc.gov and who.int only)
      │
      └─ submit_verdict
            │
            ▼
VERDICT · EXPLANATION · SOURCES
```

1. You enter a claim.
2. The agent chooses a search query and calls the search tool (Tavily, limited to `cdc.gov` and `who.int`). If the results don't settle the claim, it searches again with a different query. A claim with two parts can get a search for each part.
3. When it has enough evidence, it submits a verdict: `TRUE`, `FALSE`, `MISLEADING`, or `INSUFFICIENT_EVIDENCE`.
4. **Citations are real.** Every search result is numbered, the model only says *which numbers* it used, and the code prints the matching titles and URLs. The model never writes a link itself, so it cannot invent one.
5. Claims that are not about hantavirus, or that the sources don't cover, return `INSUFFICIENT_EVIDENCE` instead of a guess.

## Tech stack

- **Python**
- **OpenAI API** (GPT-4o-mini with tool calling)
- **Tavily API** (domain-restricted web search)
- **FastAPI** + a single-page HTML frontend
- **python-dotenv** (API keys loaded from a local `.env` file, never committed)

## Getting started

```bash
# 1. Clone the repo
git clone https://github.com/Tejveersingh27/medical-fact-checker.git
cd medical-fact-checker

# 2. Create a virtual environment and install dependencies
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 3. Add your API keys
cp .env.example .env
#    then open .env and paste your OpenAI and Tavily keys
```

**Command line**

```bash
venv/bin/python main.py
```

**Web app**

```bash
venv/bin/uvicorn server:app --reload
# open http://127.0.0.1:8000
```

The web server limits each visitor to 10 checks per hour and the whole site to 25 per day, so a public deployment cannot use up the free API quotas.
When deployed behind a proxy, set the `TRUSTED_PROXY_HOPS` environment variable to the number of proxies in front of the app (default `0`); otherwise visitors are identified by the connecting IP and the `X-Forwarded-For` header is ignored.

## Testing

`evaluate.py` runs the agent on 32 claims. Each claim has exactly one correct verdict, chosen with this rule from what the CDC and WHO pages say:

| Verdict | Meaning |
|---|---|
| `TRUE` | fully supported by CDC/WHO |
| `FALSE` | the main thing the claim asserts is contradicted |
| `MISLEADING` | partly true, but leaves out something that leads to the wrong conclusion |
| `INSUFFICIENT_EVIDENCE` | CDC/WHO pages don't address it, or it isn't about hantavirus |

Claims outside hantavirus (for example measles) are expected to return `INSUFFICIENT_EVIDENCE`. That is a design choice for this tool, not a statement about the facts.

```bash
venv/bin/python evaluate.py
```

**Latest full run: 26 of 32 correct (81%).** The six misses:

- **Blood-type claim** (expected `INSUFFICIENT_EVIDENCE`, got `FALSE`). A real weakness: when the sources are silent, the agent says "no evidence supports this" and calls the claim false, instead of saying the sources don't cover it. It did this on 3 of 3 repeat runs.
- **"Rare, so precautions are unnecessary" and "most survive, so it isn't dangerous"** (expected `MISLEADING`, got `FALSE`). Arguable: the agent judged the conclusion in each claim, which the sources contradict. These labels were written by hand under the rule above, so they may be the weaker side of the disagreement.
- **Three claims about person-to-person spread or vaccines** (expected `FALSE`, got `MISLEADING`). Also arguable, since each contains a true part (rodents spread the virus; Andes virus can spread between people).

Results move by about a claim between runs even at temperature 0, because the live search results vary (one claim passed in earlier runs and was `MISLEADING` in this one). An earlier version of the test accepted two verdicts for some claims and scored 26 of 26; it was tightened to one verdict per claim, and six new claims, labelled before they were run, were added.

The 32 claims are few and were written by the project's author with an AI assistant, and the labels have not been reviewed by anyone else. Treat the score as a way to find weaknesses, not as an accuracy figure.

### Unit tests

```bash
venv/bin/pip install -r requirements-dev.txt
venv/bin/python -m pytest
```

These tests use fake OpenAI and Tavily clients, so they need no API keys, make no network calls, and cost nothing. They cover how sources are numbered and cited (including invalid ids from the model), verdict handling, the search budget, malformed model output, and the web server's rate limits. They run automatically on every push through GitHub Actions.

## Roadmap

| Step | Goal | Status |
|---|---|---|
| **1. CLI agent** | Domain-restricted search (CDC/WHO) + GPT-4o-mini verdicts | ✅ Done |
| **2. Real citations + tests** | Source links come from search results, structured output, labelled test set | ✅ Done |
| **3. Agent + web app** | Model chooses its own searches; FastAPI backend and web page; rate limits | ✅ Done |
| **4. Deployment** | Public demo link (Render) | 🔜 Next |
| **5. Better evaluation** | Larger test set using real social-media-style claims; compare models | 🔜 Planned |

## Limitations

- Verdicts depend on what the search returns; if CDC/WHO pages don't cover a claim, the answer will be limited.
- The test set is small, and its labels have not been independently reviewed.
- The agent does not learn from past claims; each check starts fresh.
- Prototype only. Not a substitute for professional medical advice.
