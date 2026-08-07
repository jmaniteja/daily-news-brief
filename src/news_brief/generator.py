from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from .analyzer import CloudflareAnalyzer
from .collectors import collect_all, fetch_article
from .core import State, deduplicate, rank


def render_markdown(day: date, stories: list, source_errors: list[str] | None = None) -> str:
    lines = ["---", f'title: "Daily AI News Brief — {day.isoformat()}"', f"date: {day.isoformat()}",
             f"story_count: {len(stories)}", "---", "", f"# Daily AI News Brief — {day:%-d %B %Y}", ""]
    if not stories:
        lines += ["No qualifying AI news stories were found today.", ""]
    for story in stories:
        lines += [f"## [{story.title}]({story.url})", "", f"**{story.publisher} · {story.published:%Y-%m-%d}**", "",
                  story.summary, "", f"**Why it matters:** {story.why_it_matters}", ""]
        if story.discussion_url:
            lines += [f"[Hacker News discussion]({story.discussion_url}) — {story.hn_score or 0} points, {story.hn_comments or 0} comments", ""]
        if story.matched_topics:
            lines += [f"Topics: {', '.join(story.matched_topics)}", ""]
    if source_errors:
        lines += ["---", "", f"_Some sources were unavailable during this run ({len(source_errors)}). The brief uses the remaining sources._", ""]
    return "\n".join(lines)


def generate(config: dict, root: Path, day: date | None = None, now: datetime | None = None) -> Path:
    now = now or datetime.now(timezone.utc)
    day = day or now.date()
    output = root / "briefs" / f"{day.isoformat()}.md"
    # Preserve a published edition on same-day manual reruns. This also makes
    # style-only Pages deployments fast and prevents transiently failed URLs
    # from changing an edition that has already been published.
    if output.exists():
        return output
    state = State(root / "state.json")
    stories, errors = collect_all(config)
    cutoff = datetime.combine(day, time.min, tzinfo=timezone.utc) - timedelta(hours=int(config.get("lookback_hours", 48)))
    candidates = state.unseen(deduplicate([s for s in stories if s.published >= cutoff]))
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
                analyzed.append(analyzer.analyze(story, config))
            except RuntimeError as exc:
                analysis_errors.append(str(exc))
        if not analyzed:
            raise RuntimeError("Cloudflare could not analyze any candidate: " + "; ".join(analysis_errors))
    selected = rank(analyzed, now)[: int(config["max_stories"])]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(day, selected, errors), encoding="utf-8")
    state.commit(analyzed, now)
    return output
