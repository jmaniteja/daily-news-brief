from __future__ import annotations

import os
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import yaml

from .analyzer import CloudflareAnalyzer
from .collectors import collect_all, fetch_article
from .core import State, Story, deduplicate, rank


DEFAULT_TOPICS = [{
    "id": "ai-news",
    "name": "AI News",
    "description": "The most important developments in artificial intelligence.",
    "keywords": ["artificial intelligence"],
}]


def _story_topic(story: Story, topics: list[dict]) -> str:
    topic_ids = {topic["id"] for topic in topics}
    if story.primary_topic in topic_ids:
        return str(story.primary_topic)
    for topic_id in story.matched_topics:
        if topic_id in topic_ids:
            story.primary_topic = topic_id
            return topic_id
    story.primary_topic = topics[0]["id"]
    return story.primary_topic


def _matches_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(phrase.lower())}(?!\w)", text))


def shortlist(stories: list[Story], topics: list[dict], limit: int, now: datetime) -> list[Story]:
    """Keep likely-interesting candidates before article fetches and model calls."""
    keywords = [str(keyword).strip().lower() for topic in topics for keyword in topic["keywords"] if str(keyword).strip()]
    scored = []
    for story in stories:
        text = f"{story.title} {story.excerpt}".lower()
        matches = sum(_matches_phrase(text, keyword) for keyword in keywords)
        if not matches:
            continue
        age_hours = max(0, (now - story.published.astimezone(timezone.utc)).total_seconds() / 3600)
        recency = max(0, 1 - age_hours / 72)
        engagement = min(1.0, ((story.hn_score or 0) + 2 * (story.hn_comments or 0)) / 500)
        scored.append((matches + recency * .25 + engagement * .5, story))
    return [story for _, story in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def select_by_topic(stories: list[Story], topics: list[dict], now: datetime,
                    max_stories: int, max_per_topic: int) -> list[Story]:
    ranked = rank(stories, now)
    buckets = {
        topic["id"]: [story for story in ranked if _story_topic(story, topics) == topic["id"]][:max_per_topic]
        for topic in topics
    }
    selected = []
    for index in range(max_per_topic):
        for topic in topics:
            bucket = buckets[topic["id"]]
            if index < len(bucket):
                selected.append(bucket[index])
                if len(selected) == max_stories:
                    return selected
    return selected


def render_markdown(day: date, stories: list[Story], source_errors: list[str] | None = None,
                    topics: list[dict] | None = None) -> str:
    topics = topics or DEFAULT_TOPICS
    front_matter = {
        "title": f"Daily AI News Brief — {day.isoformat()}",
        "date": day.isoformat(),
        "story_count": len(stories),
        "topics": [{
            "id": topic["id"],
            "name": topic["name"],
            "description": topic.get("description", ""),
        } for topic in topics],
    }
    lines = ["---", yaml.safe_dump(front_matter, sort_keys=False).rstrip(), "---", "",
             f"# Daily AI News Brief — {day:%-d %B %Y}", ""]
    if source_errors:
        lines += [f"_Some sources were unavailable during this run ({len(source_errors)}). The brief uses the remaining sources._", ""]

    topic_names = {topic["id"]: topic["name"] for topic in topics}
    for topic in topics:
        lines += [f"## {topic['name']}", ""]
        topic_stories = [story for story in stories if _story_topic(story, topics) == topic["id"]]
        if not topic_stories:
            lines += ["No qualifying stories were found for this topic today.", ""]
            continue
        for story in topic_stories:
            lines += [f"### [{story.title}]({story.url})", "",
                      f"**{story.publisher} · {story.published:%Y-%m-%d}**", "",
                      story.summary, "", f"**Why it matters:** {story.why_it_matters}", ""]
            if story.discussion_url:
                lines += [f"[Hacker News discussion]({story.discussion_url}) — {story.hn_score or 0} points, {story.hn_comments or 0} comments", ""]
            if story.matched_topics:
                labels = [topic_names.get(topic_id, topic_id) for topic_id in story.matched_topics]
                lines += [f"Topics: {', '.join(dict.fromkeys(labels))}", ""]
    return "\n".join(lines)


def generate(config: dict, root: Path, day: date | None = None, now: datetime | None = None) -> Path:
    now = now or datetime.now(timezone.utc)
    day = day or now.date()
    output = root / "briefs" / f"{day.isoformat()}.md"
    # A manual same-day rerun should rebuild/deploy the existing edition rather
    # than replace it after state deduplication.
    if output.exists():
        return output

    state = State(root / "state.json")
    stories, errors = collect_all(config)
    cutoff = datetime.combine(day, time.min, tzinfo=timezone.utc) - timedelta(hours=int(config.get("lookback_hours", 48)))
    unseen = state.unseen(deduplicate([story for story in stories if story.published >= cutoff]))
    candidates = shortlist(unseen, config["topics"], int(config["max_candidates"]), now)
    analyzed = []
    analysis_errors = []
    if candidates:
        account, token = os.environ.get("CLOUDFLARE_ACCOUNT_ID"), os.environ.get("CLOUDFLARE_API_TOKEN")
        if not account or not token:
            raise RuntimeError("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required")
        analyzer = CloudflareAnalyzer(account, token, config["cloudflare_model"])
        for story in candidates:
            story.content = fetch_article(story)
            try:
                analyzed_story = analyzer.analyze(story, config)
                if analyzed_story.relevance:
                    _story_topic(analyzed_story, config["topics"])
                analyzed.append(analyzed_story)
            except RuntimeError as exc:
                analysis_errors.append(str(exc))
        if not analyzed:
            raise RuntimeError("Cloudflare could not analyze any candidate: " + "; ".join(analysis_errors))
    selected = select_by_topic(
        analyzed,
        config["topics"],
        now,
        int(config["max_stories"]),
        int(config["max_stories_per_topic"]),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(day, selected, errors, config["topics"]), encoding="utf-8")
    state.commit(analyzed, now)
    return output
