import os

# server.py builds its API clients when it is imported. These dummy keys let the
# tests import it without real credentials; no test ever contacts OpenAI or Tavily.
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "test-key")
