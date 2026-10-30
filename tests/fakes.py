"""Stand-ins for the OpenAI and Tavily clients so the tests never touch the network."""

import json
from types import SimpleNamespace


def tool_reply(name, arguments):
    """A model reply that calls one tool. `arguments` is the raw text the model wrote."""
    call = SimpleNamespace(id="call-1", function=SimpleNamespace(name=name, arguments=arguments))
    return SimpleNamespace(tool_calls=[call])


def search_reply(query="hantavirus"):
    return tool_reply("search_trusted_sources", json.dumps({"query": query}))


def verdict_reply(verdict="TRUE", explanation="Because.", source_ids=()):
    args = {"verdict": verdict, "explanation": explanation, "source_ids": list(source_ids)}
    return tool_reply("submit_verdict", json.dumps(args))


def result(n):
    """A fake search result."""
    return {"title": f"Page {n}", "url": f"https://www.cdc.gov/page{n}", "content": f"Text {n}"}


class FakeOpenAI:
    """Plays back scripted model replies, in order, and records every request."""

    def __init__(self, replies, repeat_last=False):
        self.replies = list(replies)
        self.repeat_last = repeat_last
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        if not self.replies:
            raise AssertionError("the model was called more times than the test scripted")
        if self.repeat_last and len(self.replies) == 1:
            reply = self.replies[0]  # keep replaying the last reply forever
        else:
            reply = self.replies.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=reply)])


class FakeTavily:
    """Returns one scripted list of results per search and records the arguments."""

    def __init__(self, results_per_search=()):
        self.results_per_search = list(results_per_search)
        self.searches = []

    def search(self, **kwargs):
        self.searches.append(kwargs)
        results = self.results_per_search.pop(0) if self.results_per_search else []
        return {"results": results}
