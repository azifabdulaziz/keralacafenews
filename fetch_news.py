#!/usr/bin/env python3
"""Fetch Malayalam/Kerala headlines from the RSS/Atom feeds in feeds.json and write news.json.

Stored per story: headline, short snippet, thumbnail URL, link to the original article,
source, category, publish time, and a "hot" score. Full articles are never copied.

"Hot" = how many different outlets reported the same story (title similarity) plus a
recency boost. Python 3.8+, no third-party packages.
"""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
UA = "Mozilla/5.0 (compatible; KeralaCafeNewsBot/1.0; +https://keralacafenews.com)"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def snippet(text, limit):
    text = strip_html(text)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(".,;:- ") + "…"


def parse_date(value):
    if not value:
        return None
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def text_of(el, path):
    found = el.find(path, NS)
    return found.text.strip() if found is not None and found.text else ""


def find_image(item, description_html):
    for tag in ("media:content", "media:thumbnail"):
        for el in item.findall(tag, NS):
            url = el.get("url")
            if url:
                return url
    for el in item.findall("enclosure"):
        if (el.get("type") or "").startswith("image") and el.get("url"):
            return el.get("url")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', description_html or "")
    return m.group(1) if m else ""


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def infer_category(link, default, url_map):
    """Pick a category from the URL's section segments, never from the article slug.

    The first path segment is tried first (e.g. /kerala-news/...). If it matches nothing,
    the second is tried (e.g. /news/kerala/...) unless it looks like a slug (2+ hyphens).
    """
    segments = [s.lower() for s in urlparse(link).path.split("/") if s]
    candidates = segments[:1]
    if len(segments) > 1 and segments[1].count("-") < 2:
        candidates.append(segments[1])
    for seg in candidates:
        for needle, label in url_map:
            if needle.strip("/") in seg:
                return label
    return default


def parse_feed(raw, feed, cfg):
    max_items = cfg.get("maxItemsPerFeed", 30)
    max_chars = cfg.get("maxSnippetChars", 220)
    url_map = cfg.get("urlCategoryMap", [])
    root = ET.fromstring(raw)
    items = []
    entries = root.findall(".//item") or root.findall(".//atom:entry", NS)
    for entry in entries[:max_items]:
        title = strip_html(text_of(entry, "title") or text_of(entry, "atom:title"))
        link = text_of(entry, "link")
        if not link:
            a = entry.find("atom:link", NS)
            link = a.get("href", "") if a is not None else ""
        desc_raw = (
            text_of(entry, "description")
            or text_of(entry, "atom:summary")
            or text_of(entry, "content:encoded")
        )
        when = parse_date(
            text_of(entry, "pubDate")
            or text_of(entry, "atom:published")
            or text_of(entry, "atom:updated")
            or text_of(entry, "dc:date")
        )
        if not title or not link:
            continue
        items.append(
            {
                "title": title,
                "link": link,
                "snippet": snippet(desc_raw, max_chars),
                "image": find_image(entry, desc_raw),
                "source": feed["source"],
                "category": infer_category(link, feed["category"], url_map),
                "published": (when or datetime.now(timezone.utc)).isoformat(),
            }
        )
    return items


# ---------- hot-story ranking ----------

def shingles(title, n=4):
    """Character n-grams. Works for Malayalam, whose words change form with suffixes."""
    t = re.sub(r"[^\wഀ-ൿ]+", " ", title.lower()).strip()
    t = re.sub(r"\s+", " ", t)
    if len(t) <= n:
        return {t} if t else set()
    return {t[i : i + n] for i in range(len(t) - n + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster_and_score(items, hot_cfg):
    threshold = hot_cfg.get("similarity", 0.3)
    w_src = hot_cfg.get("sourceWeight", 3)
    w_rec = hot_cfg.get("recencyWeight", 4)
    half = hot_cfg.get("recencyHalfLifeHours", 8)
    now = datetime.now(timezone.utc)

    items = sorted(items, key=lambda i: i["published"], reverse=True)
    clusters = []  # each: {"rep": item, "members": [items], "sh": shingles}
    for it in items:
        sh = shingles(it["title"])
        placed = False
        for c in clusters:
            if it["link"] == c["rep"]["link"] or jaccard(sh, c["sh"]) >= threshold:
                c["members"].append(it)
                placed = True
                break
        if not placed:
            clusters.append({"rep": it, "members": [it], "sh": sh})

    out = []
    for c in clusters:
        members = c["members"]
        # representative: newest item that has an image, else newest
        rep = next((m for m in members if m["image"]), members[0])
        sources = []
        also = []
        for m in members:
            if m["source"] not in sources:
                sources.append(m["source"])
            if m is not rep and m["source"] != rep["source"] and all(a["source"] != m["source"] for a in also):
                also.append({"source": m["source"], "link": m["link"]})
        newest = max(datetime.fromisoformat(m["published"]) for m in members)
        age_h = max(0.0, (now - newest).total_seconds() / 3600)
        coverage = len(sources)
        hot = w_src * coverage + w_rec * (0.5 ** (age_h / half))
        item = dict(rep)
        item["published"] = newest.isoformat()
        item["coverage"] = coverage
        item["also"] = also
        item["hot"] = round(hot, 3)
        out.append(item)
    return out


def main():
    cfg = json.loads((ROOT / "feeds.json").read_text(encoding="utf-8"))
    all_items, ok, failed = [], 0, []
    for feed in cfg["feeds"]:
        try:
            raw = fetch(feed["url"])
            got = parse_feed(raw, feed, cfg)
            all_items.extend(got)
            ok += 1
            print(f"OK   {feed['source']} ({feed['url']}): {len(got)} items")
        except Exception as exc:  # keep going if one feed is down
            failed.append(feed["url"])
            print(f"FAIL {feed['source']} ({feed['url']}): {exc}", file=sys.stderr)

    if not all_items:
        print("No items fetched; keeping the existing news.json.", file=sys.stderr)
        sys.exit(1)

    stories = cluster_and_score(all_items, cfg.get("hot", {}))
    stories.sort(key=lambda i: i["published"], reverse=True)

    out = {
        "siteName": cfg.get("siteName", "News"),
        "updated": datetime.now(timezone.utc).isoformat(),
        "items": stories[:200],
    }
    (ROOT / "news.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    multi = sum(1 for s in out["items"] if s["coverage"] > 1)
    print(f"Wrote {len(out['items'])} stories ({multi} covered by 2+ outlets) from {ok} feeds. Failed: {failed or 'none'}")


if __name__ == "__main__":
    main()
