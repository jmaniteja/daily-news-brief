from __future__ import annotations

import html
import re
import shutil
from pathlib import Path

import bleach
import markdown

ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {"h1", "h2", "p", "hr"}
CSS = """@charset "UTF-8";
:root{color-scheme:light dark;--bg:#f5f5f7;--surface:rgba(255,255,255,.86);--text:#1d1d1f;--muted:#6e6e73;--line:#d2d2d7;--accent:#c5221f;--link:#0066cc;--shadow:0 18px 60px rgba(0,0,0,.08)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:radial-gradient(circle at 50% -10%,#fff 0,var(--bg) 35rem);color:var(--text);font:17px/1.65 ui-serif,Georgia,Cambria,"Times New Roman",serif;-webkit-font-smoothing:antialiased}
a{color:var(--link);text-decoration-thickness:.06em;text-underline-offset:.18em}
a:hover{text-decoration-thickness:.12em}
.site-header{position:sticky;top:0;z-index:10;border-bottom:1px solid rgba(0,0,0,.1);background:rgba(250,250,252,.82);backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px)}
.header-inner{max-width:980px;margin:auto;padding:.85rem 1.5rem;display:flex;align-items:center;justify-content:space-between;font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.brand{display:flex;align-items:center;gap:.65rem;color:var(--text);font-size:.95rem;font-weight:700;letter-spacing:-.01em;text-decoration:none}
.brand-mark{width:1.6rem;height:1.6rem;display:grid;place-items:center;border-radius:50%;background:var(--accent);color:#fff;font-size:.72rem;box-shadow:0 3px 12px rgba(197,34,31,.25)}
.site-nav a{color:var(--muted);font-size:.86rem;font-weight:600;text-decoration:none}
.site-nav a:hover{color:var(--text)}
main{max-width:820px;margin:clamp(2rem,6vw,5rem) auto;padding:0 1.5rem 4rem;background:var(--surface);border:1px solid rgba(0,0,0,.06);border-radius:28px;box-shadow:var(--shadow);overflow:hidden}
h1{max-width:700px;margin:0 auto;padding:clamp(3rem,8vw,6rem) 0 clamp(2rem,5vw,4rem);font-size:clamp(2.7rem,8vw,5.3rem);font-weight:700;line-height:.96;letter-spacing:-.055em;text-wrap:balance}
h1:after{content:"";display:block;width:3rem;height:.32rem;margin-top:1.8rem;border-radius:1rem;background:var(--accent)}
h2{margin:0;padding:2.4rem 0 .65rem;border-top:1px solid var(--line);font-size:clamp(1.45rem,4vw,2rem);line-height:1.16;letter-spacing:-.025em;text-wrap:balance}
h2 a{color:var(--text);text-decoration:none}
h2 a:hover{color:var(--link)}
p{margin:.65rem 0;color:#333336}
p strong{font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:.82rem;letter-spacing:.015em;color:var(--muted)}
hr{height:1px;margin:2.5rem 0;border:0;background:var(--line)}
ul{padding:0;list-style:none;border-top:1px solid var(--line)}
li{border-bottom:1px solid var(--line)}
li a{display:block;padding:1.15rem 0;color:var(--text);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-weight:600;text-decoration:none}
li a:after{content:"→";float:right;color:var(--muted)}
.site-footer{max-width:820px;margin:0 auto;padding:0 1.5rem 3rem;color:var(--muted);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:.78rem}
.archive-links{display:flex;flex-wrap:wrap;gap:.6rem;margin-bottom:1rem}
.archive-links a{padding:.45rem .75rem;border:1px solid var(--line);border-radius:999px;color:var(--muted);text-decoration:none}
.archive-links a:hover{border-color:var(--text);color:var(--text)}
@media(max-width:640px){body{font-size:16px}.header-inner{padding:.75rem 1rem}main{margin:1rem;border-radius:20px;padding:0 1.15rem 2.5rem}h1{padding-top:3rem}.site-footer{padding:1rem 1.25rem 2.5rem}}
@media(prefers-color-scheme:dark){:root{--bg:#000;--surface:rgba(28,28,30,.9);--text:#f5f5f7;--muted:#a1a1a6;--line:#3a3a3c;--link:#2997ff;--shadow:none}body{background:radial-gradient(circle at 50% -10%,#27272a 0,#000 35rem)}.site-header{background:rgba(20,20,22,.8);border-color:#333}main{border-color:#333}p{color:#d1d1d6}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""


def _page(title: str, body: str, archive: list[tuple[str, str]]) -> str:
    links = " ".join(f'<a href="{html.escape(url)}">{html.escape(label)}</a>' for label, url in archive)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="A concise daily briefing on artificial intelligence, agents, and reasoning models."><meta name="theme-color" content="#f5f5f7"><title>{html.escape(title)}</title><link rel="stylesheet" href="assets/style.css"></head><body><header class="site-header"><div class="header-inner"><a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true">AI</span><span>Daily AI Brief</span></a><nav class="site-nav" aria-label="Primary"><a href="archive.html">Archive</a></nav></div></header><main>{body}</main><footer class="site-footer"><nav class="archive-links" aria-label="Recent editions">{links}</nav><p>Independent AI news summaries with attribution and links to original reporting.</p></footer></body></html>'''


def build_site(root: Path) -> Path:
    briefs = sorted((root / "briefs").glob("????-??-??.md"), reverse=True)
    if not briefs:
        raise RuntimeError("No briefs found; generate one first")
    site = root / "site"
    if site.exists():
        shutil.rmtree(site)
    (site / "assets").mkdir(parents=True)
    (site / "assets/style.css").write_text(CSS, encoding="utf-8")
    archive = [(p.stem, f"{p.stem}.html") for p in briefs]
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
