import json

import responses

from news_brief.collectors import collect_hn, collect_rss, fetch_article


@responses.activate
def test_rss_skips_partial_entries_and_parses_html():
    url = "https://feed.test/rss"
    responses.add(responses.GET, url, body='''<rss><channel><item><title>AI launch</title><link>https://example.test/a</link><pubDate>Thu, 07 Aug 2025 08:00:00 GMT</pubDate><description><![CDATA[<b>Useful</b> text]]></description></item><item><title>Missing link</title></item></channel></rss>''')
    result = collect_rss({"url": url, "name": "Test", "limit": 5})
    assert len(result) == 1
    assert result[0].excerpt == "Useful text"


@responses.activate
def test_malformed_feed_fails():
    url = "https://feed.test/rss"
    responses.add(responses.GET, url, body="not a feed")
    try:
        collect_rss({"url": url, "name": "Test", "limit": 5})
    except ValueError:
        pass
    else:
        raise AssertionError("expected invalid feed failure")


@responses.activate
def test_hn_preserves_external_and_discussion_links():
    responses.add(responses.GET, "https://news.ycombinator.com/", body='<table><tr class="athing" id="42"><td class="title"><span class="titleline"><a href="https://article.test">Story</a></span></td></tr></table>')
    responses.add(responses.GET, "https://hacker-news.firebaseio.com/v0/item/42.json", json={"url": "https://article.test", "time": 1754553600, "score": 25, "descendants": 8})
    item = collect_hn({"url": "https://news.ycombinator.com/", "limit": 5})[0]
    assert item.url == "https://article.test" and item.discussion_url.endswith("id=42")
    assert (item.hn_score, item.hn_comments) == (25, 8)


@responses.activate
def test_article_failure_falls_back():
    responses.add(responses.GET, "https://article.test/", status=403)
    from news_brief.core import Story
    from datetime import datetime, timezone
    item = Story("x", "https://article.test/", "x", datetime.now(timezone.utc), excerpt="fallback")
    assert fetch_article(item) == "fallback"
