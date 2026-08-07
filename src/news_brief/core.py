from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yaml

TRACKING = {"fbclid", "gclid", "mc_cid", "mc_eid"}


@dataclass
class Story:
    title: str
    url: str
    publisher: str
    published: datetime
    excerpt: str = ""
    content: str = ""
    hn_score: int | None = None
    hn_comments: int | None = None
    discussion_url: str | None = None
    relevance: bool = False
    primary_topic: str | None = None
    matched_topics: list[str] = field(default_factory=list)
    relevance_score: float = 0
    summary: str = ""
    why_it_matters: str = ""


def load_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    required = {"exclude", "timezone", "max_stories", "cloudflare_model", "sources"}
    missing = required - set(data or {})
    if missing:
        raise ValueError(f"Missing configuration keys: {', '.join(sorted(missing))}")
    if "topics" not in data:
        if not {"topic", "keywords"} <= set(data):
            raise ValueError("Configuration requires topics, or the legacy topic and keywords keys")
        data["topics"] = [{
            "id": "ai-news",
            "name": str(data["topic"]),
            "description": "",
            "keywords": data["keywords"],
        }]
    if not isinstance(data["topics"], list) or not data["topics"]:
        raise ValueError("topics must be a non-empty list")
    topic_ids = set()
    for topic in data["topics"]:
        if not {"id", "name", "keywords"} <= set(topic):
            raise ValueError("Each topic requires id, name, and keywords")
        topic_id = str(topic["id"])
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", topic_id):
            raise ValueError(f"Invalid topic id: {topic_id}")
        if topic_id in topic_ids:
            raise ValueError(f"Duplicate topic id: {topic_id}")
        if not isinstance(topic["keywords"], list) or not topic["keywords"]:
            raise ValueError(f"Topic {topic_id} requires at least one keyword")
        topic.setdefault("description", "")
        topic_ids.add(topic_id)
    if not isinstance(data["sources"], list) or not data["sources"]:
        raise ValueError("sources must be a non-empty list")
    if not 1 <= int(data["max_stories"]) <= 50:
        raise ValueError("max_stories must be between 1 and 50")
    data.setdefault("max_stories_per_topic", data["max_stories"])
    if not 1 <= int(data["max_stories_per_topic"]) <= int(data["max_stories"]):
        raise ValueError("max_stories_per_topic must be between 1 and max_stories")
    data.setdefault("max_candidates", max(20, int(data["max_stories"]) * 2))
    if not 1 <= int(data["max_candidates"]) <= 100:
        raise ValueError("max_candidates must be between 1 and 100")
    for source in data["sources"]:
        if not {"name", "type", "url", "limit"} <= set(source):
            raise ValueError("Each source requires name, type, url, and limit")
        if source["type"] not in {"rss", "hacker_news"}:
            raise ValueError(f"Unsupported source type: {source['type']}")
    return data


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_") and k.lower() not in TRACKING]
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def deduplicate(stories: list[Story]) -> list[Story]:
    seen, result = set(), []
    for story in stories:
        story.url = canonical_url(story.url)
        key = story.url.lower()
        if key not in seen:
            seen.add(key)
            result.append(story)
    return result


class State:
    def __init__(self, path: Path):
        self.path = path
        self.data = {"processed": {}, "last_successful_run": None}
        if path.exists():
            self.data.update(json.loads(path.read_text(encoding="utf-8")))

    def unseen(self, stories: list[Story]) -> list[Story]:
        return [s for s in stories if canonical_url(s.url) not in self.data["processed"]]

    def commit(self, stories: list[Story], now: datetime) -> None:
        cutoff = now - timedelta(days=90)
        processed = {u: ts for u, ts in self.data["processed"].items() if datetime.fromisoformat(ts) >= cutoff}
        processed.update({canonical_url(s.url): now.isoformat() for s in stories})
        self.data = {"processed": processed, "last_successful_run": now.isoformat()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rank(stories: list[Story], now: datetime) -> list[Story]:
    def score(s: Story) -> float:
        age_hours = max(0, (now - s.published.astimezone(timezone.utc)).total_seconds() / 3600)
        engagement = min(1.0, ((s.hn_score or 0) + 2 * (s.hn_comments or 0)) / 500)
        return s.relevance_score * .7 + max(0, 1 - age_hours / 72) * .2 + engagement * .1
    return sorted((s for s in stories if s.relevance), key=score, reverse=True)
