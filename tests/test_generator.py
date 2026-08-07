from datetime import date, datetime, timezone

import pytest

from news_brief.core import Story
from news_brief.generator import generate, select_by_topic, shortlist


def candidate(url: str) -> Story:
    return Story("AI story", url, "Test", datetime.now(timezone.utc), excerpt="AI agents")


def config():
    return {"topics": [{"id": "ai-news", "name": "AI News", "description": "AI", "keywords": ["AI", "agents"]}],
            "exclude": [], "cloudflare_model": "model", "lookback_hours": 48, "max_stories": 10,
            "max_stories_per_topic": 10, "max_candidates": 20, "sources": [{"name": "Test"}]}


def test_one_analysis_failure_does_not_abort(monkeypatch, tmp_path):
    stories = [candidate("https://failed.test"), candidate("https://works.test")]
    monkeypatch.setattr("news_brief.generator.collect_all", lambda _: (stories, []))
    monkeypatch.setattr("news_brief.generator.fetch_article", lambda story: story.excerpt)

    def analyze(_, story, __):
        if "failed" in story.url:
            raise RuntimeError("timeout")
        story.relevance = True
        story.primary_topic = "ai-news"
        story.matched_topics = ["ai-news"]
        story.summary = "Summary."
        story.why_it_matters = "Impact."
        return story

    monkeypatch.setattr("news_brief.generator.CloudflareAnalyzer.analyze", analyze)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    output = generate(config(), tmp_path, date.today())
    assert "works.test" in output.read_text()
    state = (tmp_path / "state.json").read_text()
    assert "works.test" in state and "failed.test" not in state


def test_complete_analysis_failure_aborts_without_output_or_state(monkeypatch, tmp_path):
    monkeypatch.setattr("news_brief.generator.collect_all", lambda _: ([candidate("https://failed.test")], []))
    monkeypatch.setattr("news_brief.generator.fetch_article", lambda story: story.excerpt)
    monkeypatch.setattr("news_brief.generator.CloudflareAnalyzer.analyze", lambda *_: (_ for _ in ()).throw(RuntimeError("timeout")))
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    with pytest.raises(RuntimeError, match="could not analyze any candidate"):
        generate(config(), tmp_path, date.today())
    assert not (tmp_path / "state.json").exists()
    assert not (tmp_path / "briefs").exists()


def test_same_day_rerun_preserves_existing_brief(monkeypatch, tmp_path):
    briefs = tmp_path / "briefs"
    briefs.mkdir()
    output = briefs / f"{date.today().isoformat()}.md"
    output.write_text("existing edition")
    monkeypatch.setattr("news_brief.generator.collect_all", lambda _: (_ for _ in ()).throw(AssertionError("must not collect")))
    assert generate(config(), tmp_path, date.today()) == output
    assert output.read_text() == "existing edition"


def test_shortlist_filters_locally_and_caps_candidates():
    now = datetime.now(timezone.utc)
    stories = [candidate("https://one.test"), candidate("https://two.test")]
    stories.append(Story("Unrelated gardening", "https://other.test", "Test", now, excerpt="Tomatoes"))
    result = shortlist(stories, config()["topics"], 1, now)
    assert len(result) == 1 and "other.test" not in result[0].url


def test_topic_selection_round_robins_across_interests():
    now = datetime.now(timezone.utc)
    topics = [
        {"id": "news", "name": "News", "keywords": ["AI"]},
        {"id": "coding", "name": "Coding", "keywords": ["agent"]},
    ]
    stories = [
        Story("News 1", "https://news.test/1", "Test", now, relevance=True, relevance_score=.9, primary_topic="news"),
        Story("News 2", "https://news.test/2", "Test", now, relevance=True, relevance_score=.8, primary_topic="news"),
        Story("Coding", "https://coding.test", "Test", now, relevance=True, relevance_score=.7, primary_topic="coding"),
    ]
    selected = select_by_topic(stories, topics, now, max_stories=2, max_per_topic=2)
    assert {story.primary_topic for story in selected} == {"news", "coding"}
