"""
Web API for the hantavirus fact-checker.

Run with:  venv/bin/uvicorn server:app --reload
Then open http://127.0.0.1:8000
"""

import os
import time
from collections import defaultdict, deque

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel, Field
from tavily import TavilyClient

from main import check_claim

load_dotenv()
client = OpenAI()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

app = FastAPI(title="Hantavirus Fact-Checker")

# Spending protection (in memory, so it resets when the server restarts).
PER_VISITOR_LIMIT = 10       # checks per visitor per hour
DAILY_LIMIT = 300            # checks across all visitors per day
hits_by_visitor = defaultdict(deque)
hits_today = deque()


def enforce_limits(request: Request) -> None:
    """Raise 429 if this visitor, or the whole site, has used up its checks."""
    now = time.time()
    # Behind a proxy (e.g. Render) the real visitor IP is in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    visitor = forwarded.split(",")[0].strip() if forwarded else request.client.host

    while hits_today and now - hits_today[0] > 86400:
        hits_today.popleft()
    if len(hits_today) >= DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Daily limit reached. Please try again tomorrow.")

    mine = hits_by_visitor[visitor]
    while mine and now - mine[0] > 3600:
        mine.popleft()
    if len(mine) >= PER_VISITOR_LIMIT:
        raise HTTPException(status_code=429, detail="You've reached the hourly limit. Please try again later.")

    mine.append(now)
    hits_today.append(now)


class ClaimRequest(BaseModel):
    claim: str = Field(min_length=3, max_length=500)


@app.post("/api/check")
def check(req: ClaimRequest, request: Request):
    enforce_limits(request)
    try:
        return check_claim(client, tavily, req.claim.strip())
    except Exception:
        raise HTTPException(status_code=502, detail="The fact-check failed. Please try again.")


@app.get("/")
def index():
    return FileResponse("static/index.html")
