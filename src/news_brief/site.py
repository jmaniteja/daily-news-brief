from __future__ import annotations

import html
import re
import shutil
from datetime import datetime
from pathlib import Path

import bleach
import markdown
import yaml

ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {"h1", "h2", "h3", "p", "hr"}
CSS = """@charset "UTF-8";
:root{color-scheme:light dark;--bg:#f5f5f7;--surface:rgba(255,255,255,.88);--text:#1d1d1f;--muted:#6e6e73;--line:#d2d2d7;--accent:#c5221f;--link:#0066cc;--shadow:0 18px 60px rgba(0,0,0,.08)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:radial-gradient(circle at 50% -10%,#fff 0,var(--bg) 35rem);color:var(--text);font:17px/1.65 ui-serif,Georgia,Cambria,"Times New Roman",serif;-webkit-font-smoothing:antialiased}
a{color:var(--link);text-decoration-thickness:.06em;text-underline-offset:.18em}
a:hover{text-decoration-thickness:.12em}
.site-header{position:sticky;top:0;z-index:20;border-bottom:1px solid rgba(0,0,0,.1);background:rgba(250,250,252,.82);backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px)}
.header-inner{max-width:980px;margin:auto;padding:.85rem 1.5rem;display:flex;align-items:center;justify-content:space-between;font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.brand{display:flex;align-items:center;gap:.65rem;color:var(--text);font-size:.95rem;font-weight:700;letter-spacing:-.01em;text-decoration:none}
.brand-mark{width:1.6rem;height:1.6rem;display:grid;place-items:center;border-radius:50%;background:var(--accent);color:#fff;font-size:.72rem;box-shadow:0 3px 12px rgba(197,34,31,.25)}
.site-nav a{color:var(--muted);font-size:.86rem;font-weight:600;text-decoration:none}
.site-nav a:hover{color:var(--text)}
main{max-width:820px;margin:clamp(2rem,6vw,5rem) auto;padding:0 1.5rem 4rem;background:var(--surface);border:1px solid rgba(0,0,0,.06);border-radius:28px;box-shadow:var(--shadow)}
.brief-heading{padding:clamp(3rem,8vw,6rem) 0 clamp(2rem,5vw,3.2rem)}
.eyebrow{margin:0 0 1rem;color:var(--accent);font:700 .78rem/1.2 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:.12em;text-transform:uppercase}
h1{max-width:700px;margin:0;font-size:clamp(2.7rem,8vw,5.3rem);font-weight:700;line-height:.96;letter-spacing:-.055em;text-wrap:balance}
h1:after{content:"";display:block;width:3rem;height:.32rem;margin-top:1.8rem;border-radius:1rem;background:var(--accent)}
.brief-summary{max-width:620px;margin:1.4rem 0 0;color:var(--muted);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:.95rem}
.run-note{margin:0 0 1.2rem;padding:.8rem 1rem;border:1px solid var(--line);border-radius:14px;color:var(--muted);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:.82rem}
.topic-tabs{position:sticky;top:3.55rem;z-index:10;display:flex;gap:.5rem;overflow-x:auto;margin:0 -1.5rem 1.25rem;padding:.75rem 1.5rem;border-top:1px solid var(--line);border-bottom:1px solid var(--line);background:rgba(255,255,255,.9);backdrop-filter:blur(20px);scrollbar-width:none}
.topic-tabs::-webkit-scrollbar{display:none}
.topic-tab{display:inline-flex;align-items:center;gap:.45rem;flex:0 0 auto;padding:.48rem .78rem;border:1px solid var(--line);border-radius:999px;color:var(--muted);background:var(--surface);font:650 .78rem/1 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;text-decoration:none;white-space:nowrap}
.topic-tab:hover{color:var(--text);border-color:var(--muted);text-decoration:none}
.topic-tab[aria-selected="true"]{color:#fff;border-color:var(--accent);background:var(--accent);box-shadow:0 4px 14px rgba(197,34,31,.2)}
.topic-tab-count{min-width:1.35rem;padding:.12rem .34rem;border:1px solid currentColor;border-radius:999px;text-align:center;font-size:.68rem;opacity:.82}
.topic-panel[hidden]{display:none}
.topic-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:1.5rem;padding:1.4rem 0 1.8rem}
.topic-heading h2{margin:0;font-size:clamp(1.8rem,5vw,2.6rem);line-height:1.05;letter-spacing:-.035em}
.topic-description{max-width:590px;margin:.7rem 0 0;color:var(--muted);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:.9rem;line-height:1.55}
.topic-count{flex:0 0 auto;padding:.35rem .62rem;border:1px solid var(--line);border-radius:999px;color:var(--muted);font:600 .72rem/1 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;white-space:nowrap}
.stories h2,.stories h3{margin:0;padding:2.4rem 0 .65rem;border-top:1px solid var(--line);font-size:clamp(1.45rem,4vw,2rem);line-height:1.16;letter-spacing:-.025em;text-wrap:balance}
.stories h2 a,.stories h3 a{color:var(--text);text-decoration:none}
.stories h2 a:hover,.stories h3 a:hover{color:var(--link)}
p{margin:.65rem 0;color:#333336}
p strong{font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:.82rem;letter-spacing:.015em;color:var(--muted)}
.stories>p:last-child{margin-bottom:2rem}
.empty-state{padding:2.2rem 0;border-top:1px solid var(--line);color:var(--muted);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
hr{height:1px;margin:2.5rem 0;border:0;background:var(--line)}
ul{padding:0;list-style:none;border-top:1px solid var(--line)}
li{border-bottom:1px solid var(--line)}
li a{display:block;padding:1.15rem 0;color:var(--text);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-weight:600;text-decoration:none}
li a:after{content:"→";float:right;color:var(--muted)}
.site-footer{max-width:820px;margin:0 auto;padding:0 1.5rem 3rem;color:var(--muted);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:.78rem}
.archive-links{display:flex;flex-wrap:wrap;gap:.6rem;margin-bottom:1rem}
.archive-links a{padding:.45rem .75rem;border:1px solid var(--line);border-radius:999px;color:var(--muted);text-decoration:none}
.archive-links a:hover{border-color:var(--text);color:var(--text)}
@media(max-width:640px){body{font-size:16px}.header-inner{padding:.75rem 1rem}main{margin:1rem;border-radius:20px;padding:0 1.15rem 2.5rem}.brief-heading{padding-top:3rem}.topic-tabs{top:3.35rem;margin-left:-1.15rem;margin-right:-1.15rem;padding-left:1.15rem;padding-right:1.15rem}.topic-heading{flex-direction:column;gap:.8rem}.site-footer{padding:1rem 1.25rem 2.5rem}}
@media(prefers-color-scheme:dark){:root{--bg:#000;--surface:rgba(28,28,30,.92);--text:#f5f5f7;--muted:#a1a1a6;--line:#3a3a3c;--link:#2997ff;--shadow:none}body{background:radial-gradient(circle at 50% -10%,#27272a 0,#000 35rem)}.site-header{background:rgba(20,20,22,.8);border-color:#333}main{border-color:#333}p{color:#d1d1d6}.topic-tabs{background:rgba(28,28,30,.92)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""

APP_JS = """(function(){
  "use strict";
  var tabs=Array.prototype.slice.call(document.querySelectorAll("[data-topic-tab]"));
  var panels=Array.prototype.slice.call(document.querySelectorAll("[data-topic-panel]"));
  if(!tabs.length||!panels.length)return;
  function valid(id){return panels.some(function(panel){return panel.dataset.topicPanel===id;});}
  function activate(id,updateUrl,moveFocus){
    if(!valid(id))id=panels[0].dataset.topicPanel;
    panels.forEach(function(panel){panel.hidden=panel.dataset.topicPanel!==id;});
    var activeTab=null;
    tabs.forEach(function(tab){
      var active=tab.dataset.topicTab===id;
      tab.setAttribute("aria-selected",active?"true":"false");
      tab.setAttribute("tabindex",active?"0":"-1");
      if(active)activeTab=tab;
    });
    if(activeTab){activeTab.scrollIntoView({block:"nearest",inline:"nearest"});if(moveFocus)activeTab.focus();}
    if(updateUrl&&window.location.hash!=="#"+id)window.history.replaceState(null,"","#"+id);
  }
  tabs.forEach(function(tab,index){
    tab.addEventListener("click",function(event){event.preventDefault();activate(tab.dataset.topicTab,true,false);});
    tab.addEventListener("keydown",function(event){
      var next=index;
      if(event.key==="ArrowRight")next=(index+1)%tabs.length;
      else if(event.key==="ArrowLeft")next=(index-1+tabs.length)%tabs.length;
      else if(event.key==="Home")next=0;
      else if(event.key==="End")next=tabs.length-1;
      else return;
      event.preventDefault();activate(tabs[next].dataset.topicTab,true,true);
    });
  });
  window.addEventListener("hashchange",function(){activate(window.location.hash.slice(1),false,false);});
  activate(window.location.hash.slice(1),false,false);
})();
"""


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "topic"


def _parse_brief(raw: str) -> tuple[dict, str]:
    match = re.match(r"\A---\n(.*?)\n---\n?", raw, flags=re.S)
    if not match:
        return {}, raw
    return yaml.safe_load(match.group(1)) or {}, raw[match.end():]


def _clean_markdown(value: str) -> str:
    rendered = markdown.markdown(value)
    return bleach.clean(rendered, tags=ALLOWED_TAGS, attributes={"a": ["href", "title"]}, protocols={"http", "https"})


def _topic_sections(metadata: dict, body: str) -> tuple[str, list[dict]]:
    lines = body.strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    configured = metadata.get("topics")
    if not isinstance(configured, list) or not configured:
        content = "\n".join(lines).strip()
        count = len(re.findall(r"(?m)^##+ \[", content))
        return "", [{"id": "ai-news", "name": "AI News", "description": "", "content": content, "count": count}]

    heading_indexes = [index for index, line in enumerate(lines) if re.fullmatch(r"## .+", line)]
    configured_names = {str(topic.get("name", "Topic")) for topic in configured}
    # Operational notes such as "Source health" are not tabs. Keep them in
    # the brief prelude even though they use a Markdown section heading.
    first_topic = next((index for index in heading_indexes if lines[index][3:].strip() in configured_names), None)
    prelude_end = first_topic if first_topic is not None else len(lines)
    prelude = "\n".join(lines[:prelude_end]).strip()
    found = {}
    for position, start in enumerate(heading_indexes):
        end = heading_indexes[position + 1] if position + 1 < len(heading_indexes) else len(lines)
        name = lines[start][3:].strip()
        found[name] = "\n".join(lines[start + 1:end]).strip()

    sections = []
    used_ids = set()
    for topic in configured:
        name = str(topic.get("name", "Topic"))
        topic_id = _slug(str(topic.get("id") or name))
        if topic_id in used_ids:
            topic_id = f"{topic_id}-{len(used_ids) + 1}"
        used_ids.add(topic_id)
        content = found.get(name, "No qualifying stories were found for this topic today.")
        sections.append({
            "id": topic_id,
            "name": name,
            "description": str(topic.get("description", "")),
            "content": content,
            "count": len(re.findall(r"(?m)^### \[", content)),
        })
    return prelude, sections


def _render_brief(raw: str, fallback_date: str) -> tuple[str, int]:
    metadata, body = _parse_brief(raw)
    prelude, sections = _topic_sections(metadata, body)
    story_count = int(metadata.get("story_count", sum(section["count"] for section in sections)))
    date_value = str(metadata.get("date", fallback_date))
    try:
        display_date = datetime.strptime(date_value, "%Y-%m-%d").strftime("%-d %B %Y")
    except ValueError:
        display_date = date_value

    heading = (f'<section class="brief-heading"><p class="eyebrow">Daily AI News Brief</p>'
               f'<h1>{html.escape(display_date)}</h1><p class="brief-summary">'
               f'{story_count} {"story" if story_count == 1 else "stories"} across {len(sections)} interests.</p></section>')
    note = f'<div class="run-note">{_clean_markdown(prelude)}</div>' if prelude else ""
    tabs = []
    panels = []
    for index, section in enumerate(sections):
        active = index == 0
        tab_id = f'tab-{section["id"]}'
        panel_id = section["id"]
        tabs.append(
            f'<a class="topic-tab" id="{tab_id}" href="#{panel_id}" role="tab" '
            f'aria-controls="{panel_id}" aria-selected="{str(active).lower()}" tabindex="{0 if active else -1}" '
            f'data-topic-tab="{panel_id}">{html.escape(section["name"])} '
            f'<span class="topic-tab-count">{section["count"]}</span></a>'
        )
        count_label = f'{section["count"]} {"story" if section["count"] == 1 else "stories"}'
        description = (f'<p class="topic-description">{html.escape(section["description"])}</p>'
                       if section["description"] else "")
        content = _clean_markdown(section["content"])
        if section["content"].strip() == "No qualifying stories were found for this topic today.":
            content = '<p class="empty-state">No qualifying stories were found for this topic today.</p>'
        panels.append(
            f'<section class="topic-panel" id="{panel_id}" role="tabpanel" aria-labelledby="{tab_id}" '
            f'data-topic-panel="{panel_id}"{"" if active else " hidden"}><div class="topic-heading"><div><h2>{html.escape(section["name"])}</h2>'
            f'{description}</div><span class="topic-count">{count_label}</span></div>'
            f'<div class="stories">{content}</div></section>'
        )
    nav = f'<nav class="topic-tabs" role="tablist" aria-label="Interests">{"".join(tabs)}</nav>'
    return heading + note + nav + '<div class="topic-panels">' + "".join(panels) + "</div>", story_count


def _page(title: str, body: str, archive: list[tuple[str, str]]) -> str:
    links = " ".join(f'<a href="{html.escape(url)}">{html.escape(label)}</a>' for label, url in archive)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="A concise daily briefing on artificial intelligence, coding agents, agentic systems, and token efficiency."><meta name="theme-color" content="#f5f5f7"><title>{html.escape(title)}</title><link rel="stylesheet" href="assets/style.css"><script src="assets/app.js" defer></script><noscript><style>.topic-panel[hidden]{{display:block!important}}</style></noscript></head><body><header class="site-header"><div class="header-inner"><a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true">AI</span><span>Daily AI Brief</span></a><nav class="site-nav" aria-label="Primary"><a href="archive.html">Archive</a></nav></div></header><main>{body}</main><footer class="site-footer"><nav class="archive-links" aria-label="Recent editions">{links}</nav><p>Independent AI news summaries with attribution and links to original reporting.</p></footer></body></html>'''


def build_site(root: Path) -> Path:
    briefs = sorted((root / "briefs").glob("????-??-??.md"), reverse=True)
    if not briefs:
        raise RuntimeError("No briefs found; generate one first")
    site = root / "site"
    if site.exists():
        shutil.rmtree(site)
    (site / "assets").mkdir(parents=True)
    (site / "assets/style.css").write_text(CSS, encoding="utf-8")
    (site / "assets/app.js").write_text(APP_JS, encoding="utf-8")
    archive = [(path.stem, f"{path.stem}.html") for path in briefs]
    pages = []
    for path in briefs:
        body, story_count = _render_brief(path.read_text(encoding="utf-8"), path.stem)
        page = _page(f"Daily AI News Brief — {path.stem}", body, archive[:7])
        (site / f"{path.stem}.html").write_text(page, encoding="utf-8")
        pages.append((path.stem, body, story_count))
    (site / "index.html").write_text(_page(f"Daily AI News Brief — {pages[0][0]}", pages[0][1], archive[:7]), encoding="utf-8")
    listing = "<section class=\"brief-heading\"><p class=\"eyebrow\">Daily AI News Brief</p><h1>Archive</h1></section><ul>" + "".join(f'<li><a href="{url}">{day}</a></li>' for day, url in archive) + "</ul>"
    (site / "archive.html").write_text(_page("Daily AI News Brief archive", listing, archive[:7]), encoding="utf-8")
    (site / ".nojekyll").touch()
    return site
