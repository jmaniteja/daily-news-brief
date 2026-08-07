from datetime import date, datetime, timezone

from news_brief.core import Story
from news_brief.generator import render_markdown
from news_brief.site import build_site


TOPICS = [
    {"id": "ai-news", "name": "AI News", "description": "Important AI developments.", "keywords": ["AI"]},
    {"id": "ai-coding", "name": "AI Coding", "description": "Practical coding-agent workflows.", "keywords": ["coding agent"]},
]


def test_empty_brief_and_site_is_deterministic_and_escaped(tmp_path):
    briefs = tmp_path / "briefs"
    briefs.mkdir()
    empty = render_markdown(date(2026, 8, 7), [], topics=TOPICS)
    assert "No qualifying" in empty
    (briefs / "2026-08-07.md").write_text(empty + '\n<script>alert(1)</script>')
    build_site(tmp_path)
    first = (tmp_path / "site/index.html").read_text()
    build_site(tmp_path)
    assert (tmp_path / "site/index.html").read_text() == first
    assert "<script>alert(1)</script>" not in first and "&lt;script&gt;alert(1)&lt;/script&gt;" in first
    assert 'name="viewport"' in first and "archive.html" in first
    assert 'href="assets/style.css"' in first
    assert 'href="index.html"' in first
    assert 'href="/assets/style.css"' not in first
    assert "prefers-color-scheme:dark" in (tmp_path / "site/assets/style.css").read_text()
    assert 'role="tablist"' in first and 'data-topic-tab="ai-news"' in first
    assert 'data-topic-panel="ai-coding"' in first and 'href="#ai-coding"' in first
    assert 'aria-selected="true"' in first and 'aria-selected="false"' in first
    assert 'data-topic-panel="ai-coding" hidden' in first
    assert ".topic-panel[hidden]{display:block!important}" in first
    assert 'src="assets/app.js"' in first
    script = (tmp_path / "site/assets/app.js").read_text()
    assert "ArrowRight" in script and "hashchange" in script


def test_markdown_has_attribution_and_hn_metadata():
    item = Story("Title", "https://article.test", "Publisher", datetime.now(timezone.utc),
                 summary="Facts.", why_it_matters="Impact.", discussion_url="https://news.ycombinator.com/item?id=1",
                 hn_score=3, hn_comments=2, primary_topic="ai-coding", matched_topics=["ai-coding"])
    text = render_markdown(date(2026, 8, 7), [item], topics=TOPICS)
    assert "### [Title](https://article.test)" in text and "**Publisher" in text and "3 points, 2 comments" in text
    assert "## AI Coding" in text and "Topics: AI Coding" in text
