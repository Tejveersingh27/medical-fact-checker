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

The web server limits each visitor to 10 checks per hour and the whole site to 300 per day, so a public deployment cannot run up API costs.

## Testing

`evaluate.py` runs the agent on 26 claims whose correct answers were written by hand from CDC/WHO guidance, including multi-part, half-true, and off-topic claims.

```bash
venv/bin/python evaluate.py
```

On the first run the agent got **25 of 26** right. The one miss was an off-topic claim ("Measles spreads through the air") that it judged on the CDC's measles pages instead of declining. The prompt was tightened and that claim now returns `INSUFFICIENT_EVIDENCE`; the full set has not been re-run since that fix.

The test set is small and written by the project author, so this shows the pipeline works, not that it is 96% accurate on real-world claims.

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
- The test set is small and hand-labelled.
- The agent does not learn from past claims; each check starts fresh.
- Prototype only. Not a substitute for professional medical advice.
