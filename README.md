# Daily AI News Brief

A small Python pipeline that collects AI stories from OpenAI, GitHub, and Hacker News; asks Cloudflare Workers AI to select and summarize them; commits dated Markdown briefs; and publishes a static GitHub Pages archive.

## Setup

1. Use Python 3.11 or newer and run `pip install -r requirements.lock`.
2. Set `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`.
3. Adjust topics, exclusions, sources, limits, or `cloudflare_model` in `config.yml`.
4. Run `PYTHONPATH=src python -m news_brief.cli validate`, then `generate`, then `build`.

An explicit date can be generated with `generate --date YYYY-MM-DD`. Building never accesses the network. Generated Markdown is stored in `briefs/`, durable URL history in `state.json`, and the disposable website in `site/`.

## GitHub Pages

Add `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` as Actions secrets. In repository settings, select **GitHub Actions** as the Pages deployment source. The workflow runs at 07:00 Europe/London (including daylight-saving changes) and can also be started through **Run workflow**.

Each source is isolated: a partial outage is noted in the brief, but does not block publication. If every source fails, or if any required Cloudflare analysis exhausts its retry, the command exits without advancing `state.json` or writing a misleading empty brief. An ordinary successful day with no qualifying items creates an explicit no-news brief.

The collector uses bounded requests and does not attempt to bypass authentication, paywalls, robots restrictions, or anti-bot measures. Unavailable article bodies fall back to feed excerpts.
