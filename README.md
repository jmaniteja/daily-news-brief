# Daily AI News Brief

A small Python pipeline that collects stories about AI, coding agents, agentic systems, and token efficiency; asks Cloudflare Workers AI to categorize and summarize them; commits dated Markdown briefs; and publishes a tabbed static GitHub Pages archive.

## Setup

1. Use Python 3.11 or newer and run `pip install -r requirements.lock`.
2. Set `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`.
3. Adjust the topic names, descriptions, keywords, exclusions, sources, limits, or `cloudflare_model` in `config.yml`.
4. Run `PYTHONPATH=src python -m news_brief.cli validate`, then `generate`, then `build`.

An explicit date can be generated with `generate --date YYYY-MM-DD`. Building never accesses the network. Generated Markdown is stored in `briefs/`, durable URL history in `state.json`, daily public-safe source reports in `reports/`, and the disposable website in `site/`.

## Source reports

Every successful generation writes `reports/YYYY-MM-DD.json` (schema version 1) and retains the latest 90 days. Each report has run metadata and a configuration hash, aggregate totals, and one record per configured source. A source record tracks collection requests/statuses and discovered, malformed, deduplicated, shortlisted, fetched, analyzed, and selected counts. It also records aggregate fallback/retry/failure counters and a short error category, never article text, URLs, response bodies, or credentials.

Compare `discovered → shortlisted → selected` over time to spot source quality changes. High excerpt fallbacks or article failures point to extraction/access trouble; high analysis failures or malformed/retry counts point to Cloudflare analysis; an `error` source can be an isolated outage while the rest of a brief still publishes. The Markdown edition includes a compact Source health summary; the JSON reports are the detailed diagnostic record.

## GitHub Pages

Add `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` as Actions secrets. In repository settings, select **GitHub Actions** as the Pages deployment source. The workflow runs at 07:00 Europe/London (including daylight-saving changes) and can also be started through **Run workflow**.

Each source is isolated: a partial outage is noted in the brief, but does not block publication. If every source fails, or if any required Cloudflare analysis exhausts its retry, the command exits without advancing `state.json` or writing a misleading empty brief. An ordinary successful day with no qualifying items creates an explicit no-news brief.

The four default tabs are **AI News**, **AI Coding**, **Agentic Systems**, and **Token Efficiency**. Each relevant article receives one primary tab plus optional cross-topic labels. The static site uses hash-addressable, keyboard-accessible tabs; its Markdown editions remain readable without JavaScript.

To bound model usage as sources are added, title and feed excerpts are matched locally first. At most `max_candidates` articles are fetched and analyzed per run, `max_stories_per_topic` limits any one tab, and `max_stories` caps the complete edition.

The collector uses bounded requests and does not attempt to bypass authentication, paywalls, robots restrictions, or anti-bot measures. Unavailable article bodies fall back to feed excerpts. The default source mix combines OpenAI, Hacker News, focused GitHub AI feeds, Google and Microsoft developer blogs, LangChain, and Cloudflare's agent/Workers AI changelogs.
