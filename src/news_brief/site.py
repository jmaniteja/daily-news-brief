from __future__ import annotations

import html
import re
import shutil
from pathlib import Path

import bleach
import markdown

ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {"h1", "h2", "p", "hr"}
CSS = """*{box-sizing:border-box}body{margin:0;background:#f7f7f4;color:#20211f;font:17px/1.65 system-ui,sans-serif}header,main,footer{max-width:850px;margin:auto;padding:1.25rem}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #ddd}a{color:#075a76}h1{line-height:1.15}h2{margin-top:2.5rem;line-height:1.3}.archive{display:flex;flex-wrap:wrap;gap:.75rem}footer{color:#666}@media(max-width:600px){body{font-size:16px}header{align-items:flex-start;flex-direction:column}}"""


def _page(title: str, body: str, archive: list[tuple[str, str]]) -> str:
    links = " ".join(f'<a href="{html.escape(url)}">{html.escape(label)}</a>' for label, url in archive)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><link rel="stylesheet" href="/assets/style.css"></head><body><header><a href="/">Daily AI News Brief</a><nav aria-label="Archive"><a href="/archive.html">Archive</a></nav></header><main>{body}</main><footer><div class="archive">{links}</div><p>Summaries link to and attribute their original publishers.</p></footer></body></html>'''


def build_site(root: Path) -> Path:
    briefs = sorted((root / "briefs").glob("????-??-??.md"), reverse=True)
    if not briefs:
        raise RuntimeError("No briefs found; generate one first")
    site = root / "site"
    if site.exists():
        shutil.rmtree(site)
    (site / "assets").mkdir(parents=True)
    (site / "assets/style.css").write_text(CSS, encoding="utf-8")
    archive = [(p.stem, f"/{p.stem}.html") for p in briefs]
    pages = []
    for path in briefs:
        raw = re.sub(r"\A---\n.*?\n---\n", "", path.read_text(encoding="utf-8"), flags=re.S)
        body = bleach.clean(markdown.markdown(raw), tags=ALLOWED_TAGS, attributes={"a": ["href", "title"]}, protocols={"http", "https"})
        page = _page(f"Daily AI News Brief — {path.stem}", body, archive[:7])
        (site / f"{path.stem}.html").write_text(page, encoding="utf-8")
        pages.append((path.stem, body))
    (site / "index.html").write_text(_page(f"Daily AI News Brief — {pages[0][0]}", pages[0][1], archive[:7]), encoding="utf-8")
    listing = "<h1>Archive</h1><ul>" + "".join(f'<li><a href="{u}">{d}</a></li>' for d, u in archive) + "</ul>"
    (site / "archive.html").write_text(_page("Daily AI News Brief archive", listing, archive[:7]), encoding="utf-8")
    (site / ".nojekyll").touch()
    return site
