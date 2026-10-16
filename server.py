"""
Web API for the hantavirus fact-checker.

Run with:  venv/bin/uvicorn server:app --reload
Then open http://127.0.0.1:8000
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel, Field
from tavily import TavilyClient

from main import check_claim

load_dotenv()
client = OpenAI()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

app = FastAPI(title="Hantavirus Fact-Checker")


class ClaimRequest(BaseModel):
    claim: str = Field(min_length=3, max_length=500)


@app.post("/api/check")
def check(req: ClaimRequest):
    try:
        return check_claim(client, tavily, req.claim.strip())
    except Exception:
        raise HTTPException(status_code=502, detail="The fact-check failed. Please try again.")


@app.get("/")
def index():
    return FileResponse("static/index.html")
