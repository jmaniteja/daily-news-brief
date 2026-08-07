from __future__ import annotations

import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests
from bs4 import BeautifulSoup

from .core import Story

USER_AGENT = "daily-news-brief/0.1 (+https://github.com/)"


def _date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)


def collect_rss(source: dict, session=requests) -> list[Story]:
    response = session.get(source["url"], timeout=20, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Invalid feed from {source['name']}: {feed.bozo_exception}")
    stories = []
    for entry in feed.entries[: int(source["limit"])]:
        title, link = entry.get("title"), entry.get("link")
        if not title or not link:
            continue
        stories.append(Story(title=title.strip(), url=link, publisher=source["name"],
            published=_date(entry.get("published") or entry.get("updated")),
            excerpt=BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True)))
    return stories


def collect_hn(source: dict, session=requests) -> list[Story]:
    response = session.get(source["url"], timeout=20, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    stories = []
    for row in soup.select("tr.athing")[: int(source["limit"])]:
        story_id = row.get("id")
        link = row.select_one(".titleline > a")
        if not story_id or not link:
            continue
        item = session.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=10).json()
        stories.append(Story(title=link.get_text(strip=True), url=item.get("url") or link.get("href"),
            publisher="Hacker News", published=datetime.fromtimestamp(item.get("time", time.time()), timezone.utc),
            hn_score=item.get("score", 0), hn_comments=item.get("descendants", 0),
            discussion_url=f"https://news.ycombinator.com/item?id={story_id}"))
    return stories


def collect_all(config: dict) -> tuple[list[Story], list[str]]:
    stories, errors = [], []
    for source in config["sources"]:
        try:
            stories.extend(collect_rss(source) if source["type"] == "rss" else collect_hn(source))
        except Exception as exc:
            errors.append(f"{source['name']}: {exc}")
    if len(errors) == len(config["sources"]):
        raise RuntimeError("Every source failed: " + "; ".join(errors))
    return stories, errors


def fetch_article(story: Story, session=requests, max_bytes: int = 1_000_000) -> str:
    try:
        response = session.get(story.url, timeout=20, headers={"User-Agent": USER_AGENT, "Range": f"bytes=0-{max_bytes - 1}"})
        response.raise_for_status()
        if "html" not in response.headers.get("content-type", "html"):
            return story.excerpt
        soup = BeautifulSoup(response.content[:max_bytes], "html.parser")
        for node in soup.select("script,style,nav,footer,header,aside"):
            node.decompose()
        text = (soup.select_one("article") or soup.select_one("main") or soup).get_text(" ", strip=True)
        return text[:12000] or story.excerpt
    except requests.RequestException:
        return story.excerpt
