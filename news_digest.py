#!/usr/bin/env python3
"""
news_digest.py — Generates a static HTML "morning digest" combining:
  - Hacker News top stories (tech + security news, great for English reading practice)
  - GitHub Trending repositories (today, all languages)

Design goals:
  - No browser automation, no headless Chrome, no background daemon.
  - A handful of lightweight HTTP requests, runs in <2 seconds, then exits.
  - Writes a single self-contained HTML file and opens it with the default browser.

Usage:
  python3 news_digest.py            # generate + open in browser
  python3 news_digest.py --no-open  # just generate the file (for cron/systemd logging)
"""
import json
import re
import sys
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"
GH_TRENDING = "https://github.com/trending?since=daily"

OUT_DIR = Path.home() / ".cache" / "news-digest"
OUT_FILE = OUT_DIR / "digest.html"

HN_COUNT = 15
GH_COUNT = 12
TIMEOUT = 6

SECURITY_KEYWORDS = re.compile(
    r"\b(security|vulnerab|exploit|breach|malware|ransomware|CVE|hack|"
    r"phishing|zero-day|0-day|leak|encrypt|backdoor)\b",
    re.IGNORECASE,
)


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "news-digest/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "news-digest/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", errors="ignore")


def get_hn_stories():
    ids = fetch_json(HN_TOP)[:40]  # grab extra, we'll filter/trim
    stories = []
    for i in ids:
        if len(stories) >= HN_COUNT:
            break
        try:
            item = fetch_json(HN_ITEM.format(i))
        except Exception:
            continue
        if not item or item.get("type") != "story" or not item.get("title"):
            continue
        title = item["title"]
        stories.append(
            {
                "title": title,
                "url": item.get("url") or f"https://news.ycombinator.com/item?id={i}",
                "points": item.get("score", 0),
                "comments": item.get("descendants", 0),
                "hn_link": f"https://news.ycombinator.com/item?id={i}",
                "is_security": bool(SECURITY_KEYWORDS.search(title)),
            }
        )
    return stories


def get_github_trending():
    try:
        html = fetch_text(GH_TRENDING)
    except Exception:
        return []

    repos = []
    # Each trending repo sits in an <article class="Box-row"> block.
    for block in re.findall(r'<article class="Box-row">(.*?)</article>', html, re.S)[:GH_COUNT]:
        name_match = re.search(r'href="/([^"]+)"\s+data-view-component', block)
        if not name_match:
            name_match = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"', block, re.S)
        if not name_match:
            continue
        repo = name_match.group(1).strip()

        desc_match = re.search(r'<p class="col-9[^"]*"[^>]*>\s*(.*?)\s*</p>', block, re.S)
        desc = re.sub(r"\s+", " ", desc_match.group(1)).strip() if desc_match else ""

        lang_match = re.search(r'itemprop="programmingLanguage">([^<]+)<', block)
        lang = lang_match.group(1).strip() if lang_match else ""

        stars_match = re.search(r'/stargazers".*?</svg>\s*([\d,]+)\s*</a>', block, re.S)
        stars = stars_match.group(1).strip() if stars_match else "?"

        repos.append(
            {
                "name": repo,
                "url": f"https://github.com/{repo}",
                "desc": desc,
                "lang": lang,
                "stars": stars,
            }
        )
    return repos


def esc(s):
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(stories, repos):
    now = datetime.now().strftime("%A, %d %B %Y — %H:%M")

    hn_items = "\n".join(
        f"""
        <li class="item{' sec' if s['is_security'] else ''}">
          <a class="title" href="{esc(s['url'])}" target="_blank">{esc(s['title'])}</a>
          <div class="meta">
            <span>▲ {s['points']}</span>
            <span>💬 <a href="{esc(s['hn_link'])}" target="_blank">{s['comments']} comments</a></span>
            {'<span class="tag">security</span>' if s['is_security'] else ''}
          </div>
        </li>"""
        for s in stories
    )

    gh_items = "\n".join(
        f"""
        <li class="item">
          <a class="title" href="{esc(r['url'])}" target="_blank">{esc(r['name'])}</a>
          <div class="desc">{esc(r['desc'])}</div>
          <div class="meta">
            {'<span class="tag lang">' + esc(r['lang']) + '</span>' if r['lang'] else ''}
            <span>★ {esc(r['stars'])}</span>
          </div>
        </li>"""
        for r in repos
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Daily Digest — {esc(now)}</title>
<style>
  :root {{
    --bg: #0d1117; --card: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff; --sec: #f85149;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 40px 20px; background: var(--bg); color: var(--text);
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  .wrap {{ max-width: 920px; margin: 0 auto; }}
  header {{ margin-bottom: 32px; }}
  header h1 {{ font-size: 26px; margin: 0 0 4px; }}
  header .sub {{ color: var(--muted); font-size: 14px; }}
  .cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  @media (max-width: 800px) {{ .cols {{ grid-template-columns: 1fr; }} }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 18px 20px; }}
  .card h2 {{ font-size: 15px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 0 0 14px; }}
  ul.list {{ list-style: none; margin: 0; padding: 0; }}
  li.item {{ padding: 12px 0; border-top: 1px solid var(--border); }}
  li.item:first-child {{ border-top: none; padding-top: 0; }}
  li.item.sec {{ border-left: 3px solid var(--sec); padding-left: 10px; }}
  a.title {{ color: var(--text); text-decoration: none; font-size: 15px; font-weight: 500; line-height: 1.4; }}
  a.title:hover {{ color: var(--accent); text-decoration: underline; }}
  .desc {{ color: var(--muted); font-size: 13px; margin-top: 4px; }}
  .meta {{ margin-top: 6px; font-size: 12px; color: var(--muted); display: flex; gap: 12px; align-items: center; }}
  .meta a {{ color: var(--muted); }}
  .tag {{ background: rgba(88,166,255,.15); color: var(--accent); padding: 1px 8px; border-radius: 10px; font-size: 11px; }}
  .tag.lang {{ background: rgba(63,185,80,.15); color: #3fb950; }}
  li.item.sec .tag {{ background: rgba(248,81,73,.15); color: var(--sec); }}
  footer {{ text-align: center; color: var(--muted); font-size: 12px; margin-top: 32px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>📰 Daily Tech &amp; Security Digest</h1>
    <div class="sub">{esc(now)} · Hacker News + GitHub Trending</div>
  </header>
  <div class="cols">
    <div class="card">
      <h2>Hacker News — Top Stories</h2>
      <ul class="list">{hn_items or '<li class="item">Could not load Hacker News right now.</li>'}</ul>
    </div>
    <div class="card">
      <h2>GitHub Trending — Today</h2>
      <ul class="list">{gh_items or '<li class="item">Could not load GitHub Trending right now.</li>'}</ul>
    </div>
  </div>
  <footer>Generated locally — no tracking, no ads. Refresh: run news_digest.py again.</footer>
</div>
</body>
</html>
"""


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stories = get_hn_stories()
    repos = get_github_trending()
    html = render_html(stories, repos)
    OUT_FILE.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_FILE} ({len(stories)} HN stories, {len(repos)} trending repos)")

    if "--no-open" not in sys.argv:
        webbrowser.open(f"file://{OUT_FILE}")


if __name__ == "__main__":
    main()
