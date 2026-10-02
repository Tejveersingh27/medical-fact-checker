# Hantavirus Medical Fact-Checker

A command-line AI agent that fact-checks health claims about hantavirus. It searches **only trusted public-health sources (CDC and WHO)** and then has **GPT-4o-mini** return a structured verdict with an explanation and citations.

> ⚠️ This is a learning prototype, not a medical tool. It does not provide medical advice.

---

## Why I built this

Health misinformation spreads quickly, and large language models can "hallucinate" confident answers that aren't true. Instead of letting the model answer from memory, this agent **retrieves real information from the CDC and WHO first** and asks the model to reason only from that evidence. Grounding the answer in trusted sources is the core idea behind retrieval-augmented generation (RAG), and it is what this project is building toward.

## How it works

```
Claim (user input)
      │
      ▼
Tavily search ──► restricted to cdc.gov and who.int (advanced depth)
      │
      ▼
Search results combined into context
      │
      ▼
GPT-4o-mini + system prompt
      │
      ▼
VERDICT (TRUE / FALSE / MISLEADING) · EXPLANATION · SOURCES
```

1. You enter a health claim.
2. The Tavily API searches only `cdc.gov` and `who.int`.
3. The text from those results is passed to GPT-4o-mini as context.
4. A system prompt instructs the model to respond with a verdict, an explanation, and citations.

## Tech stack

- **Python**
- **OpenAI API** (GPT-4o-mini)
- **Tavily API** (domain-restricted web search)
- **python-dotenv** (API keys loaded from a local `.env` file, never committed)

## Getting started

```bash
# 1. Clone the repo
git clone https://github.com/Tejveersingh27/medical-fact-checker.git
cd medical-fact-checker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API keys
cp .env.example .env
#    then open .env and paste your OpenAI and Tavily keys

# 4. Run it
python main.py
```

## Example

```
Enter your claim: Hantavirus spreads easily from person to person.
```

<!-- TODO: run the command above and paste the real output (or a screenshot) here -->

## Roadmap

| Sprint | Goal | Status |
|---|---|---|
| **1. CLI agent** | Domain-restricted search (CDC/WHO) + GPT-4o-mini verdicts with citations | ✅ Done |
| **2. API + interface** | Wrap the agent in a **FastAPI** endpoint and build a **React** frontend to submit claims and view results | 🔜 Planned |
| **3. Better grounding + confidence** | Add a **RAG pipeline** (vector store over CDC/WHO/PubMed documents) and a **logistic regression** model that scores confidence in each verdict | 🔜 Planned |
| **4. Insights + deployment** | Use **K-means clustering** to group recurring claims, containerize with **Docker**, and add a **GitHub Actions** CI pipeline | 🔜 Planned |

## Limitations

- Verdicts depend on what the search returns; if CDC/WHO pages don't cover a claim, the answer will be limited.
- There is no evaluation set yet to measure accuracy. Building one is part of Sprint 3.
- Prototype only. Not a substitute for professional medical advice.
