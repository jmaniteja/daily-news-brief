from __future__ import annotations

import json
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .core import Story


class CloudflareAnalyzer:
    def __init__(self, account_id: str, token: str, model: str, session=None):
        self.url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions"
        self.token, self.model = token, model
        self.session = session or self._session()

    @staticmethod
    def _session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"POST"}),
            respect_retry_after_header=True,
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        return session

    def analyze(self, story: Story, config: dict) -> Story:
        prompt = {
            "topic": config["topic"], "keywords": config["keywords"], "exclude": config["exclude"],
            "article": {"title": story.title, "publisher": story.publisher, "text": (story.content or story.excerpt)[:12000]},
            "instruction": "Return only JSON with relevance (boolean), matched_topics (string array), relevance_score (0..1), summary (2 factual sentences), why_it_matters (1 sentence).",
        }
        last_error = None
        for attempt in range(2):
            try:
                response = self.session.post(self.url, timeout=(10, 60),
                    headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                    json={"model": self.model, "temperature": 0.1, "response_format": {"type": "json_object"},
                          "messages": [{"role": "system", "content": "You are a precise news editor."},
                                       {"role": "user", "content": json.dumps(prompt)}]})
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                data = json.loads(content)
                required = {"relevance", "matched_topics", "relevance_score", "summary", "why_it_matters"}
                if not required <= set(data) or not isinstance(data["relevance"], bool):
                    raise ValueError("Malformed analysis object")
                story.relevance = data["relevance"]
                story.matched_topics = [str(x) for x in data["matched_topics"]]
                story.relevance_score = max(0.0, min(1.0, float(data["relevance_score"])))
                story.summary = str(data["summary"]).strip()
                story.why_it_matters = str(data["why_it_matters"]).strip()
                return story
            except (requests.RequestException, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(1)
        raise RuntimeError(f"Cloudflare analysis failed for {story.url}: {last_error}")
