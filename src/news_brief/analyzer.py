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
            total=1,
            connect=1,
            read=1,
            status=1,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"POST"}),
            respect_retry_after_header=True,
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        return session

    def analyze(self, story: Story, config: dict) -> Story:
        topics = [{
            "id": topic["id"],
            "name": topic["name"],
            "description": topic.get("description", ""),
            "keywords": topic["keywords"],
        } for topic in config["topics"]]
        prompt = {
            "topics": topics, "exclude": config["exclude"],
            "article": {"title": story.title, "publisher": story.publisher, "text": (story.content or story.excerpt)[:12000]},
            "instruction": "Return only JSON with relevance (boolean), primary_topic (an exact topic id, or null when irrelevant), matched_topics (array of exact topic ids), relevance_score (0..1), summary (2 factual sentences), and why_it_matters (1 sentence). Choose one primary topic for every relevant article.",
        }
        last_error = None
        for attempt in range(2):
            try:
                response = self.session.post(self.url, timeout=(10, 30),
                    headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                    json={"model": self.model, "temperature": 0.1, "response_format": {"type": "json_object"},
                          "messages": [{"role": "system", "content": "You are a precise news editor."},
                                       {"role": "user", "content": json.dumps(prompt)}]})
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                data = json.loads(content)
                required = {"relevance", "primary_topic", "matched_topics", "relevance_score", "summary", "why_it_matters"}
                if not required <= set(data) or not isinstance(data["relevance"], bool):
                    raise ValueError("Malformed analysis object")
                if not isinstance(data["matched_topics"], list):
                    raise ValueError("Malformed topic matches")
                valid_topics = {topic["id"] for topic in topics}
                primary_topic = data["primary_topic"]
                if data["relevance"] and primary_topic not in valid_topics:
                    raise ValueError("Relevant article has an invalid primary topic")
                matched_topics = [str(value) for value in data["matched_topics"] if str(value) in valid_topics]
                if data["relevance"] and primary_topic not in matched_topics:
                    matched_topics.insert(0, str(primary_topic))
                story.relevance = data["relevance"]
                story.primary_topic = str(primary_topic) if data["relevance"] else None
                story.matched_topics = matched_topics
                story.relevance_score = max(0.0, min(1.0, float(data["relevance_score"])))
                story.summary = str(data["summary"]).strip()
                story.why_it_matters = str(data["why_it_matters"]).strip()
                return story
            except requests.RequestException as exc:
                # The configured adapter has already retried transient network
                # failures. Do not multiply those attempts at this layer.
                raise RuntimeError(f"Cloudflare analysis failed for {story.url}: {exc}") from exc
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(1)
        raise RuntimeError(f"Cloudflare analysis failed for {story.url}: {last_error}")
