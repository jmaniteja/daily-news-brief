from datetime import datetime, timedelta, timezone

from news_brief.core import State, Story, canonical_url, deduplicate, rank


def story(url="https://example.com/a", **kw):
    return Story("Title", url, "Publisher", kw.pop("published", datetime.now(timezone.utc)), **kw)


def test_canonical_url_removes_tracking_and_fragment():
    assert canonical_url("HTTPS://Example.com/a/?utm_source=x&keep=1#part") == "https://example.com/a?keep=1"


def test_deduplicate_canonical_urls():
    assert len(deduplicate([story(), story("https://example.com/a/?utm_medium=email")])) == 1


def test_state_persistence_pruning_and_idempotency(tmp_path):
    path = tmp_path / "state.json"
    state = State(path)
    old = datetime.now(timezone.utc) - timedelta(days=100)
    state.data["processed"]["https://old.test/"] = old.isoformat()
    item = story()
    state.commit([item], datetime.now(timezone.utc))
    loaded = State(path)
    assert loaded.unseen([item]) == []
    assert "https://old.test/" not in loaded.data["processed"]


def test_rank_filters_and_uses_relevance():
    low = story("https://x/low", relevance=True, relevance_score=.2)
    high = story("https://x/high", relevance=True, relevance_score=.9)
    irrelevant = story("https://x/no", relevance=False, relevance_score=1)
    assert rank([low, irrelevant, high], datetime.now(timezone.utc)) == [high, low]
