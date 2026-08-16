"""
Monitor S&P Global and Nasdaq index rebalance news pages.
Send Telegram notifications when new entries are detected.
"""

import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# ── Config ────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

TARGETS = [
    {
        "name": "S&P Global - Index Changes",
        "url": "https://press.spglobal.com/index.php?s=2429&category=781&keywords=to+join",
        "cache_file": CACHE_DIR / "spglobal.json",
    },
    {
        "name": "Nasdaq IR - Index Changes",
        "url": "https://ir.nasdaq.com/search?query=to+join&f%5B0%5D=type%3Anir_news",
        "cache_file": CACHE_DIR / "nasdaq.json",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
}


# ── Page Parsing ──────────────────────────────────────
def parse_spglobal(html: str) -> list[dict]:
    """Parse S&P Global news list."""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # Try multiple selectors to adapt to page structure changes
    articles = (
        soup.select("article")
        or soup.select(".wd_item, .wd_news_item")
        or soup.select(".news-item, .press-release")
        or soup.select("div.item, li.item")
    )

    # Fallback: scan all links and filter by keyword and title length
    if not articles:
        for link in soup.select("a[href]"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if title and "to join" in title.lower() and len(title) > 20:
                full_url = href if href.startswith("http") else f"https://press.spglobal.com{href}"
                items.append({"title": clean_title(title), "url": full_url})
    else:
        for article in articles:
            link = article.find("a", href=True)
            if not link:
                continue
            title = link.get_text(strip=True)
            href = link["href"]
            if not title:
                continue
            full_url = href if href.startswith("http") else f"https://press.spglobal.com{href}"
            items.append({"title": clean_title(title), "url": full_url})

    return items


def parse_nasdaq(html: str) -> list[dict]:
    """Parse Nasdaq IR news list."""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # Primary: each search result has a direct <a> containing <h3> for the title
    for result in soup.select(".search-result"):
        link = result.find("a", href=True)
        # Skip the category filter link (first <a> has class "search-result-contenttype")
        # The article link is the one whose href starts with /news-releases/
        for a_tag in result.find_all("a", href=True):
            href = a_tag.get("href", "")
            if "/news-releases/" in href:
                title = a_tag.get_text(strip=True)
                if title:
                    full_url = f"https://ir.nasdaq.com{href}" if not href.startswith("http") else href
                    items.append({"title": clean_title(title), "url": full_url})
                break

    # Fallback: scan all links if structured selectors didn't match
    if not items:
        for link in soup.select("a[href]"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if title and len(title) > 20 and "/news-releases/" in href:
                full_url = href if href.startswith("http") else f"https://ir.nasdaq.com{href}"
                items.append({"title": clean_title(title), "url": full_url})

    return items


PARSERS = {
    "S&P Global - Index Changes": parse_spglobal,
    "Nasdaq IR - Index Changes": parse_nasdaq,
}


# ── Cache & Comparison ────────────────────────────────
def load_cache(cache_file: Path) -> dict[str, str]:
    """Load known entry fingerprints from cache. Returns {hash: title}."""
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        # Support old format (list of hashes) and new format (dict)
        if isinstance(data, list):
            return {h: "" for h in data}
        return data
    return {}


def save_cache(cache_file: Path, entries: dict[str, str]):
    cache_file.write_text(json.dumps(entries, ensure_ascii=False, indent=2))


def clean_title(title: str, max_len: int = 200) -> str:
    """Normalize whitespace and truncate overly long titles."""
    title = " ".join(title.split())
    if len(title) > max_len:
        title = title[:max_len] + "..."
    return title


def fingerprint(item: dict) -> str:
    """Generate a unique fingerprint for an entry."""
    raw = f"{item['title']}|{item['url']}"
    return hashlib.md5(raw.encode()).hexdigest()


# ── Telegram Notification ─────────────────────────────
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    print("Telegram notification sent")


# ── Main Logic ────────────────────────────────────────
def check_target(target: dict) -> list[dict]:
    """Check a single target page, return new entries."""
    name = target["name"]
    url = target["url"]
    cache_file = target["cache_file"]

    print(f"\nChecking: {name}")
    print(f"  URL: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Request failed: {e}")
        return []

    parser = PARSERS[name]
    items = parser(resp.text)
    print(f"  Parsed {len(items)} entries")

    if not items:
        print("  No entries parsed (page structure may have changed)")
        # Fallback: use page content hash to detect changes
        page_hash = hashlib.md5(resp.text.encode()).hexdigest()
        old_cache = load_cache(cache_file)
        if page_hash not in old_cache:
            save_cache(cache_file, {page_hash: "(whole page hash)"})
            if old_cache:  # Not the first run
                return [{"title": f"Warning: {name} page content changed (could not parse entries, please check manually)", "url": url}]
        return []

    # Compare with cache
    old_cache = load_cache(cache_file)
    new_items = []
    all_entries = {}

    for item in items:
        fp = fingerprint(item)
        all_entries[fp] = item["title"]
        if fp not in old_cache:
            new_items.append(item)

    # Update cache
    save_cache(cache_file, all_entries)

    # First run: only establish baseline, no notifications
    if not old_cache:
        print(f"  First run, cached {len(all_entries)} entries as baseline")
        return []

    if new_items:
        print(f"  Found {len(new_items)} new entries!")
    else:
        print("  No new entries")

    return new_items


def main():
    print("=" * 60)
    print("Index Rebalance News Monitor")
    print("=" * 60)

    all_new = []
    for target in TARGETS:
        new_items = check_target(target)
        if new_items:
            all_new.append((target["name"], new_items))

    if all_new:
        # Build Telegram message
        lines = ["<b>Index Rebalance Alert</b>\n"]
        for source, items in all_new:
            lines.append(f"<b>{source}</b>")
            for item in items:
                lines.append(f'  - <a href="{item["url"]}">{item["title"]}</a>')
            lines.append("")
        message = "\n".join(lines)
        send_telegram(message)
    else:
        print("\nNo new entries across all sources")


if __name__ == "__main__":
    main()
