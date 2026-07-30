#!/usr/bin/env python3
"""
news_digest.py — Generates a static HTML "morning digest" combining:
  - Hacker News top stories (tech news, great for English reading practice)
  - GitHub Trending repositories (today, all languages, general popularity)
  - GitHub security repos (newly created repos tagged "security", by stars)
  - Latest CVEs from NVD (description, CVSS severity, references)

Design goals:
  - No browser automation, no headless Chrome, no background daemon.
  - A handful of lightweight HTTP requests, runs in a few seconds, then exits.
  - Writes a single self-contained HTML file and opens it with the default browser.

Usage:
  python3 news_digest.py            # generate + open in browser
  python3 news_digest.py --no-open  # just generate the file (for cron/systemd logging)
"""
import json
import re
import sys
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"
GH_TRENDING = "https://github.com/trending?since=daily"
GH_SEARCH = "https://api.github.com/search/repositories"
NVD_CVE = "https://services.nvd.nist.gov/rest/json/cves/2.0"

OUT_DIR = Path.home() / ".cache" / "news-digest"
OUT_FILE = OUT_DIR / "digest.html"

HN_COUNT = 12
GH_COUNT = 10
SEC_REPO_COUNT = 10
CVE_COUNT = 12
SEC_REPO_WINDOW_DAYS = 14   # "newly created" security repos
CVE_WINDOW_DAYS = 3         # look back this many days for new CVEs
CVE_FETCH_LIMIT = 400       # how many raw CVE records to pull before ranking
TIMEOUT = 8

SECURITY_KEYWORDS = re.compile(
    r"\b(security|vulnerab|exploit|breach|malware|ransomware|CVE|hack|"
    r"phishing|zero-day|0-day|leak|encrypt|backdoor)\b",
    re.IGNORECASE,
)

SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
SEVERITY_COLOR = {
    "CRITICAL": "#f85149",
    "HIGH": "#ff8c42",
    "MEDIUM": "#e3b341",
    "LOW": "#3fb950",
}


def fetch_json(url, headers=None):
    h = {"User-Agent": "news-digest/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "news-digest/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", errors="ignore")


# ---------------------------------------------------------------- Hacker News

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


# ---------------------------------------------------------- GitHub Trending

def get_github_trending():
    try:
        html = fetch_text(GH_TRENDING)
    except Exception:
        return []

    repos = []
    for block in re.findall(r'<article class="Box-row">(.*?)</article>', html, re.S)[:GH_COUNT]:
        repo = _parse_trending_block(block)
        if repo:
            repos.append(repo)
    return repos


def _parse_trending_block(block):
    name_match = re.search(r'href="/([^"]+)"\s+data-view-component', block)
    if not name_match:
        name_match = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"', block, re.S)
    if not name_match:
        return None
    repo = name_match.group(1).strip()

    desc_match = re.search(r'<p class="col-9[^"]*"[^>]*>\s*(.*?)\s*</p>', block, re.S)
    desc = re.sub(r"\s+", " ", desc_match.group(1)).strip() if desc_match else ""

    lang_match = re.search(r'itemprop="programmingLanguage">([^<]+)<', block)
    lang = lang_match.group(1).strip() if lang_match else ""

    stars_match = re.search(r'/stargazers".*?</svg>\s*([\d,]+)\s*</a>', block, re.S)
    stars = stars_match.group(1).strip() if stars_match else "?"

    return {
        "name": repo,
        "url": f"https://github.com/{repo}",
        "desc": desc,
        "lang": lang,
        "stars": stars,
    }


# ------------------------------------------------------- GitHub security repos

def get_security_repos():
    """Newly-created repos tagged 'security' on GitHub, ranked by stars."""
    since = (datetime.utcnow() - timedelta(days=SEC_REPO_WINDOW_DAYS)).strftime("%Y-%m-%d")
    query = f"topic:security created:>{since}"
    url = (
        f"{GH_SEARCH}?q={urllib.parse.quote(query)}"
        f"&sort=stars&order=desc&per_page={SEC_REPO_COUNT}"
    )
    try:
        data = fetch_json(url, headers={"Accept": "application/vnd.github+json"})
    except Exception:
        return []

    repos = []
    for item in data.get("items", [])[:SEC_REPO_COUNT]:
        repos.append(
            {
                "name": item.get("full_name", ""),
                "url": item.get("html_url", ""),
                "desc": item.get("description") or "",
                "lang": item.get("language") or "",
                "stars": f"{item.get('stargazers_count', 0):,}",
                "created": (item.get("created_at") or "")[:10],
            }
        )
    return repos


# ------------------------------------------------------------------------ CVE

def get_cves():
    end = datetime.utcnow()
    start = end - timedelta(days=CVE_WINDOW_DAYS)
    url = (
        f"{NVD_CVE}?resultsPerPage={CVE_FETCH_LIMIT}"
        f"&pubStartDate={start.strftime('%Y-%m-%dT%H:%M:%S.000')}"
        f"&pubEndDate={end.strftime('%Y-%m-%dT%H:%M:%S.000')}"
    )
    try:
        data = fetch_json(url)
    except Exception:
        return []

    cves = []
    for entry in data.get("vulnerabilities", []):
        cve = entry.get("cve", {})
        cve_id = cve.get("id", "")
        if not cve_id:
            continue

        desc = ""
        for d in cve.get("descriptions", []):
            if d.get("lang") == "en":
                desc = d.get("value", "")
                break

        severity, score = _extract_cvss(cve.get("metrics", {}))
        refs = [r.get("url") for r in cve.get("references", []) if r.get("url")]

        cves.append(
            {
                "id": cve_id,
                "published": cve.get("published", ""),
                "desc": desc,
                "severity": severity,
                "score": score,
                "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                "ref": refs[0] if refs else "",
            }
        )

    # Rank by severity first, then recency, so the most relevant CVEs surface.
    cves.sort(
        key=lambda c: (SEVERITY_RANK.get(c["severity"], 0), c["published"]),
        reverse=True,
    )
    return cves[:CVE_COUNT]


def _extract_cvss(metrics):
    for key in ("cvssMetricV31", "cvssMetricV40", "cvssMetricV30"):
        m = metrics.get(key)
        if m:
            data = m[0].get("cvssData", {})
            return data.get("baseSeverity", "UNKNOWN"), data.get("baseScore", "?")
    m = metrics.get("cvssMetricV2")
    if m:
        return m[0].get("baseSeverity", "UNKNOWN"), m[0].get("cvssData", {}).get("baseScore", "?")
    return "UNKNOWN", "?"


def esc(s):
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(stories, repos, sec_repos, cves):
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

    def repo_items(rlist, show_created=False):
        return "\n".join(
            f"""
        <li class="item">
          <a class="title" href="{esc(r['url'])}" target="_blank">{esc(r['name'])}</a>
          <div class="desc">{esc(r['desc'])}</div>
          <div class="meta">
            {'<span class="tag lang">' + esc(r['lang']) + '</span>' if r['lang'] else ''}
            <span>★ {esc(r['stars'])}</span>
            {'<span>created ' + esc(r.get('created', '')) + '</span>' if show_created else ''}
          </div>
        </li>"""
            for r in rlist
        )

    gh_items = repo_items(repos)
    sec_repo_items = repo_items(sec_repos, show_created=True)

    cve_items = "\n".join(
        f"""
        <li class="item">
          <div class="cve-head">
            <a class="title" href="{esc(c['url'])}" target="_blank">{esc(c['id'])}</a>
            <span class="tag sev" style="background:{SEVERITY_COLOR.get(c['severity'], '#8b949e')}22;color:{SEVERITY_COLOR.get(c['severity'], '#8b949e')}">
              {esc(c['severity'])}{' · ' + str(c['score']) if c['score'] != '?' else ''}
            </span>
          </div>
          <div class="desc">{esc(c['desc'])}</div>
          <div class="meta">
            <span>{esc(c['published'][:10])}</span>
            {'<span><a href="' + esc(c['ref']) + '" target="_blank">reference</a></span>' if c['ref'] else ''}
          </div>
        </li>"""
        for c in cves
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
  .wrap {{ max-width: 1180px; margin: 0 auto; }}
  header {{ margin-bottom: 32px; }}
  header h1 {{ font-size: 26px; margin: 0 0 4px; }}
  header .sub {{ color: var(--muted); font-size: 14px; }}
  .cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  @media (max-width: 900px) {{ .cols {{ grid-template-columns: 1fr; }} }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 18px 20px; margin-bottom: 24px; }}
  .card h2 {{ font-size: 15px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 0 0 6px; }}
  .card .card-sub {{ font-size: 12px; color: var(--muted); margin: 0 0 14px; }}
  .info-box {{
    background: rgba(88,166,255,.08); border: 1px solid rgba(88,166,255,.25);
    border-radius: 8px; padding: 12px 14px; font-size: 12.5px; color: var(--muted);
    margin-bottom: 14px; line-height: 1.5;
  }}
  .info-box b {{ color: var(--text); }}
  ul.list {{ list-style: none; margin: 0; padding: 0; }}
  li.item {{ padding: 12px 0; border-top: 1px solid var(--border); }}
  li.item:first-child {{ border-top: none; padding-top: 0; }}
  li.item.sec {{ border-left: 3px solid var(--sec); padding-left: 10px; }}
  a.title {{ color: var(--text); text-decoration: none; font-size: 15px; font-weight: 500; line-height: 1.4; }}
  a.title:hover {{ color: var(--accent); text-decoration: underline; }}
  .desc {{ color: var(--muted); font-size: 13px; margin-top: 4px; }}
  .meta {{ margin-top: 6px; font-size: 12px; color: var(--muted); display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
  .meta a {{ color: var(--muted); }}
  .tag {{ background: rgba(88,166,255,.15); color: var(--accent); padding: 1px 8px; border-radius: 10px; font-size: 11px; white-space: nowrap; }}
  .tag.lang {{ background: rgba(63,185,80,.15); color: #3fb950; }}
  li.item.sec .tag {{ background: rgba(248,81,73,.15); color: var(--sec); }}
  .cve-head {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }}
  .tag.sev {{ font-weight: 600; }}
  footer {{ text-align: center; color: var(--muted); font-size: 12px; margin-top: 8px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>📰 Daily Tech &amp; Security Digest</h1>
    <div class="sub">{esc(now)} · Hacker News · GitHub Trending · GitHub Security · NVD CVEs</div>
  </header>
  <div class="cols">
    <div class="card">
      <h2>Hacker News — Top Stories</h2>
      <ul class="list">{hn_items or '<li class="item">Could not load Hacker News right now.</li>'}</ul>
    </div>
    <div class="card">
      <h2>GitHub Trending — Today (General)</h2>
      <ul class="list">{gh_items or '<li class="item">Could not load GitHub Trending right now.</li>'}</ul>
    </div>
    <div class="card">
      <h2>GitHub — New Security Projects</h2>
      <div class="card-sub">Repos tagged "security", created in the last {SEC_REPO_WINDOW_DAYS} days, ranked by stars</div>
      <ul class="list">{sec_repo_items or '<li class="item">Could not load security repos right now.</li>'}</ul>
    </div>
    <div class="card">
      <h2>Latest CVEs (NVD)</h2>
      <div class="info-box">
        <b>What is a CVE?</b> A CVE (Common Vulnerabilities and Exposures) is a unique ID assigned
        by MITRE/NVD to a publicly known security flaw, so researchers, vendors, and tools can all
        reference the same issue consistently. Each entry below describes <b>what the flaw is</b>
        (e.g. improper input validation, path traversal, command injection) and <b>how it can be
        exploited</b> (attack vector, privileges required, whether user interaction is needed).
        The <b>CVSS score</b> (0–10) and severity label (Low/Medium/High/Critical) summarize how
        dangerous and easy-to-exploit the flaw is — higher means worse.
      </div>
      <div class="card-sub">Published in the last {CVE_WINDOW_DAYS} days, sorted by severity then recency</div>
      <ul class="list">{cve_items or '<li class="item">Could not load CVE data right now.</li>'}</ul>
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
    sec_repos = get_security_repos()
    cves = get_cves()
    html = render_html(stories, repos, sec_repos, cves)
    OUT_FILE.write_text(html, encoding="utf-8")
    print(
        f"Wrote {OUT_FILE} "
        f"({len(stories)} HN, {len(repos)} trending, {len(sec_repos)} security repos, {len(cves)} CVEs)"
    )

    if "--no-open" not in sys.argv:
        webbrowser.open(f"file://{OUT_FILE}")


if __name__ == "__main__":
    main()
