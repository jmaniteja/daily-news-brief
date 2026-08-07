# Daily AI News Brief Generator

## Summary

Build a Python-based generator that runs daily at 07:00 Europe/London in GitHub Actions, discovers AI-related stories from the configured sources, uses Cloudflare Workers AI to filter and summarize them, commits a dated Markdown brief, and deploys a responsive static archive to GitHub Pages.

Core sources:

- OpenAI News via `https://openai.com/news/rss.xml`
- Hacker News front page, including linked article content and HN engagement
- GitHub AI & ML via `https://github.blog/ai-and-ml/feed/`
- GitHub Changelog via `https://github.blog/changelog/feed/`
- Google Developers, Microsoft Developers AI, LangChain, and Cloudflare Agents/Workers AI feeds

## Implementation

- Add a YAML configuration containing:
  - Tabs for `AI News`, `AI Coding`, `Agentic Systems`, and `Token Efficiency`
  - Per-topic descriptions and discovery keywords
  - Exclusion: `cryptocurrency`
  - Source URLs, source type, per-source limits, timezone, maximum 10 stories, and Cloudflare model name.
- Implement an RSS/Atom collector for OpenAI and GitHub.
- Implement a Hacker News collector that reads the current front page and supplements entries with score, comment count, discussion URL, and publication time from the official HN API.
- Fetch readable article text with timeouts, response-size limits, a descriptive user agent, retries, and per-source failure isolation. Do not bypass paywalls, authentication, robots restrictions, or anti-bot controls; fall back to feed/title excerpts when full text is unavailable.
- Normalize canonical URLs, remove duplicate stories across sources, and maintain a committed state file containing processed URLs and the last successful run. Bootstrap the first run with a 48-hour lookback and prune state older than 90 days.
- Send bounded article text to Cloudflare Workers AI through its OpenAI-compatible REST endpoint. Default to `@cf/zai-org/glm-4.7-flash`, configurable without code changes; Cloudflare currently recommends this model family for efficient long-form processing. Validate structured JSON output and retry malformed or transient responses once.
- Locally shortlist at most 30 title/excerpt matches before article fetches and model calls.
- Have the model return relevance, one primary tab, matched topics, relevance score, a concise factual summary, and “why it matters.” Rank qualifying stories by relevance, recency, and HN engagement, then select them across topics with per-tab and total limits.
- Write `briefs/YYYY-MM-DD.md` with front matter and grouped story entries containing title, publisher, date, source link, summary, relevance explanation, and optional HN metadata.
- Generate a no-news Markdown brief when collection succeeds but no items qualify. If every source fails or Cloudflare processing fails, fail the workflow without advancing state or publishing a misleading empty brief.
- Render the Markdown archive into static HTML:
  - Homepage containing the latest brief
  - Dated archive pages
  - Archive navigation
  - Responsive, accessible CSS
  - Hash-addressable, keyboard-accessible topic tabs with a small progressive-enhancement script and a no-JavaScript fallback
  - Escaped/sanitized generated content and visible attribution links

## Automation and Interfaces

- Provide CLI commands for:
  - Generating a brief for the current date or an explicit date
  - Building the static site without fetching news
  - Validating configuration
- Add a GitHub Actions workflow with manual dispatch and a timezone-aware `07:00` schedule using `Europe/London`.
- The workflow will install locked dependencies, run tests, generate the brief, commit Markdown/state changes using the Actions bot, build the site, upload the Pages artifact, and deploy it in the same run.
- Use workflow concurrency to prevent overlapping daily runs.
- Require these GitHub secrets:
  - `CLOUDFLARE_ACCOUNT_ID`
  - `CLOUDFLARE_API_TOKEN`
- Give the workflow only the required permissions: repository contents write, Pages write, and identity-token write.
- Document enabling GitHub Pages with GitHub Actions as its deployment source, configuring secrets, editing topics/sources, running manually, and interpreting failures.

## Test Plan

- Parse valid, malformed, and partially missing RSS entries.
- Parse Hacker News stories and preserve external and discussion links.
- Normalize and deduplicate tracking URLs and cross-posted stories.
- Verify first-run lookback, processed-URL persistence, pruning, and rerun idempotency.
- Mock Cloudflare success, irrelevant results, malformed JSON, rate limits, authentication failure, and retry exhaustion.
- Verify inaccessible articles fall back to available feed text.
- Verify partial source failure still produces a brief while complete collection failure does not.
- Verify empty days create an explicit no-news brief.
- Verify Markdown contains required attribution and the generated HTML escapes unsafe content.
- Verify homepage selection, archive ordering, tab/hash navigation, keyboard semantics, responsive markup, and deterministic rebuilds.
- Run an end-to-end fixture build without external network calls.

## Assumptions

- All initial sources are optional individually; one unavailable source will not prevent the other sources from producing the brief.
- Hacker News acts as a discovery source, so linked third-party articles may appear even though they were not authored by Hacker News.
- English output and English-language relevance evaluation are used initially.
- The repository’s default branch is the publication source, and generated Markdown plus state are intentionally committed for durable history.
- Scheduled GitHub workflows may start slightly after 07:00 during platform load.
