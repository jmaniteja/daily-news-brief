from datetime import datetime, timezone

import responses

from news_brief.analyzer import CloudflareAnalyzer
from news_brief.core import Story


def item():
    return Story("AI agents", "https://example.test", "Test", datetime.now(timezone.utc), content="Article")


CONFIG = {"topic": "AI", "keywords": ["agents"], "exclude": ["crypto"]}


@responses.activate
def test_cloudflare_success():
    url = "https://api.cloudflare.com/client/v4/accounts/acct/ai/v1/chat/completions"
    content = '{"relevance":true,"matched_topics":["agents"],"relevance_score":0.9,"summary":"Summary.","why_it_matters":"Important."}'
    responses.add(responses.POST, url, json={"choices": [{"message": {"content": content}}]})
    result = CloudflareAnalyzer("acct", "token", "model").analyze(item(), CONFIG)
    assert result.relevance and result.relevance_score == .9


@responses.activate
def test_cloudflare_retries_malformed(monkeypatch):
    monkeypatch.setattr("news_brief.analyzer.time.sleep", lambda _: None)
    url = "https://api.cloudflare.com/client/v4/accounts/acct/ai/v1/chat/completions"
    responses.add(responses.POST, url, json={"choices": [{"message": {"content": "bad"}}]})
    content = '{"relevance":false,"matched_topics":[],"relevance_score":0,"summary":"No.","why_it_matters":"N/A"}'
    responses.add(responses.POST, url, json={"choices": [{"message": {"content": content}}]})
    assert not CloudflareAnalyzer("acct", "token", "model").analyze(item(), CONFIG).relevance
