from __future__ import annotations

import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests
from bs4 import BeautifulSoup

from .core import Story
from .observability import SourceMetrics

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


def collect_rss(source: dict, session=requests, metrics: SourceMetrics | None = None) -> list[Story]:
    started = time.monotonic()
    response = session.get(source["url"], timeout=20, headers={"User-Agent": USER_AGENT})
    if metrics:
        metrics.request(response)
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Invalid feed from {source['name']}: {feed.bozo_exception}")
    stories = []
    metrics and setattr(metrics, "entries_discovered", len(feed.entries))
    for entry in feed.entries[: int(source["limit"])]:
        title, link = entry.get("title"), entry.get("link")
        if not title or not link:
            if metrics: metrics.entries_malformed += 1
            continue
        stories.append(Story(title=title.strip(), url=link, publisher=source["name"],
            published=_date(entry.get("published") or entry.get("updated")),
            excerpt=BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True),
            source_name=source["name"], topic_hints=list(source.get("topic_hints", []))))
    if metrics: metrics.collection_duration_ms += round((time.monotonic() - started) * 1000)
    return stories


def collect_hn(source: dict, session=requests, metrics: SourceMetrics | None = None) -> list[Story]:
    started = time.monotonic()
    response = session.get(source["url"], timeout=20, headers={"User-Agent": USER_AGENT})
    if metrics: metrics.request(response)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    stories = []
    for row in soup.select("tr.athing")[: int(source["limit"])]:
        if metrics: metrics.entries_discovered += 1
        story_id = row.get("id")
        link = row.select_one(".titleline > a")
        if not story_id or not link:
            if metrics: metrics.entries_malformed += 1
            continue
        try:
            item_response = session.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=10)
            if metrics: metrics.request(item_response)
            item_response.raise_for_status()
            item = item_response.json()
            url = item.get("url") or link.get("href")
            if not url:
                raise ValueError("HN item has no link")
            stories.append(Story(title=link.get_text(strip=True), url=url,
                publisher="Hacker News", published=datetime.fromtimestamp(item.get("time", time.time()), timezone.utc),
                hn_score=item.get("score", 0), hn_comments=item.get("descendants", 0),
                discussion_url=f"https://news.ycombinator.com/item?id={story_id}", source_name=source.get("name", "Hacker News"),
                topic_hints=list(source.get("topic_hints", []))))
        except Exception as exc:
            if metrics: metrics.entries_malformed += 1; metrics.error(exc)
            continue
    if metrics: metrics.collection_duration_ms += round((time.monotonic() - started) * 1000)
    return stories


def collect_all(config: dict) -> tuple[list[Story], list[str], list[SourceMetrics]]:
    stories, errors, metrics = [], [], []
    for source in config["sources"]:
        report = SourceMetrics(source["name"], source["type"])
        metrics.append(report)
        started = time.monotonic()
        try:
            stories.extend(collect_rss(source, metrics=report) if source["type"] == "rss" else collect_hn(source, metrics=report))
        except Exception as exc:
            errors.append(f"{source['name']}: {exc}")
            report.error(exc)
        finally:
            # Successful collectors set this themselves; failures still receive a
            # meaningful elapsed time rather than an ambiguous zero.
            if not report.collection_duration_ms:
                report.collection_duration_ms = round((time.monotonic() - started) * 1000)
    if len(errors) == len(config["sources"]):
        raise RuntimeError("Every source failed: " + "; ".join(errors))
    return stories, errors, metrics


def fetch_article(story: Story, session=requests, max_bytes: int = 1_000_000, metrics: SourceMetrics | None = None) -> str:
    if metrics: metrics.article_fetch_attempts += 1
    try:
        response = session.get(story.url, timeout=20, headers={"User-Agent": USER_AGENT, "Range": f"bytes=0-{max_bytes - 1}"})
        if metrics: metrics.request(response)
        response.raise_for_status()
        if "html" not in response.headers.get("content-type", "html"):
            if metrics: metrics.article_excerpt_fallback += 1; metrics.article_unsupported_content += 1
            return story.excerpt
        soup = BeautifulSoup(response.content[:max_bytes], "html.parser")
        for node in soup.select("script,style,nav,footer,header,aside"):
            node.decompose()
        text = (soup.select_one("article") or soup.select_one("main") or soup).get_text(" ", strip=True)
        if text:
            if metrics: metrics.article_extracted += 1
            return text[:12000]
        if metrics: metrics.article_excerpt_fallback += 1
        return story.excerpt
    except requests.RequestException as exc:
        if metrics:
            metrics.article_failures += 1
            metrics.article_excerpt_fallback += 1
            if isinstance(exc, requests.Timeout):
                metrics.article_timeouts += 1
            elif isinstance(exc, requests.HTTPError):
                metrics.article_http_failures += 1
            metrics.error(exc)
        return story.excerpt
