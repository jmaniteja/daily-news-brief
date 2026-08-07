from datetime import date, datetime, timezone

from news_brief.core import Story
from news_brief.generator import render_markdown
from news_brief.site import build_site


def test_empty_brief_and_site_is_deterministic_and_escaped(tmp_path):
    briefs = tmp_path / "briefs"
    briefs.mkdir()
    empty = render_markdown(date(2026, 8, 7), [])
    assert "No qualifying" in empty
    (briefs / "2026-08-07.md").write_text(empty + '\n<script>alert(1)</script>')
    build_site(tmp_path)
    first = (tmp_path / "site/index.html").read_text()
    build_site(tmp_path)
    assert (tmp_path / "site/index.html").read_text() == first
    assert "<script>" not in first and "&lt;script&gt;" in first
    assert 'name="viewport"' in first and "archive.html" in first


def test_markdown_has_attribution_and_hn_metadata():
    item = Story("Title", "https://article.test", "Publisher", datetime.now(timezone.utc),
                 summary="Facts.", why_it_matters="Impact.", discussion_url="https://news.ycombinator.com/item?id=1", hn_score=3, hn_comments=2)
    text = render_markdown(date(2026, 8, 7), [item])
    assert "[Title](https://article.test)" in text and "**Publisher" in text and "3 points, 2 comments" in text
