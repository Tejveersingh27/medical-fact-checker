"""
Web API for the hantavirus fact-checker.

Run with:  venv/bin/uvicorn server:app --reload
Then open http://127.0.0.1:8000
"""

import logging
import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from main import check_claim, make_clients

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

client, tavily = make_clients()

app = FastAPI(title="Hantavirus Fact-Checker")

# Spending protection (in memory, so it resets when the server restarts).
PER_VISITOR_LIMIT = 10       # checks per visitor per hour
DAILY_LIMIT = 25             # checks across all visitors per day (Tavily free plan is limited)
MAX_TRACKED_VISITORS = 10_000  # safety net so the visitor table cannot grow without bound
# How many proxies we run in front of this app (0 = none, e.g. local development).
TRUSTED_PROXY_HOPS = int(os.getenv("TRUSTED_PROXY_HOPS", "0"))
hits_by_visitor = defaultdict(deque)
hits_today = deque()


def client_ip(request: Request) -> str:
    """Return the visitor's IP address.

    X-Forwarded-For can be forged by the client, so it is ignored unless we know
    how many trusted proxies sit in front of us. Each proxy appends the address
    it saw, so with N trusted proxies the real visitor is the Nth entry from the
    right; anything to its left was supplied by the client and cannot be trusted.
    """
    if TRUSTED_PROXY_HOPS > 0:
        parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
        if len(parts) >= TRUSTED_PROXY_HOPS:
            return parts[-TRUSTED_PROXY_HOPS]
    return request.client.host if request.client else "unknown"


def prune_visitors(now: float) -> None:
    """Forget visitors who have made no check in the last hour."""
    for ip in [ip for ip, hits in hits_by_visitor.items() if not hits or now - hits[-1] > 3600]:
        del hits_by_visitor[ip]


def enforce_limits(request: Request) -> None:
    """Raise 429 if this visitor, or the whole site, has used up its checks."""
    now = time.time()
    visitor = client_ip(request)
    logger.info("Check requested by visitor %s", visitor)  # lets you verify TRUSTED_PROXY_HOPS after deploying

    while hits_today and now - hits_today[0] > 86400:
        hits_today.popleft()
    if len(hits_today) >= DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Daily limit reached. Please try again tomorrow.")

    if visitor not in hits_by_visitor and len(hits_by_visitor) >= MAX_TRACKED_VISITORS:
        prune_visitors(now)
        if len(hits_by_visitor) >= MAX_TRACKED_VISITORS:
            raise HTTPException(status_code=429, detail="The service is busy. Please try again later.")

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
        logger.exception("Fact-check failed")
        raise HTTPException(status_code=502, detail="The fact-check failed. Please try again.")


@app.get("/health")
def health():
    """Used by the host to see that the app is up. Calls no external service and uses no quota."""
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse("static/index.html")
