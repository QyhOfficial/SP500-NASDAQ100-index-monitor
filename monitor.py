"""
监控 S&P Global 和 Nasdaq 指数调整新闻页面
检测到新条目时通过 Telegram 发送通知
"""

import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────
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


# ── 页面解析 ──────────────────────────────────────────
def parse_spglobal(html: str) -> list[dict]:
    """解析 S&P Global 新闻列表"""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    articles = (
        soup.select("article")
        or soup.select(".wd_item, .wd_news_item")
        or soup.select(".news-item, .press-release")
        or soup.select("div.item, li.item")
    )

    if not articles:
        for link in soup.select("a[href]"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if title and "to join" in title.lower() and len(title) > 20:
                full_url = href if href.startswith("http") else f"https://press.spglobal.com{href}"
                items.append({"title": title, "url": full_url})
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
            items.append({"title": title, "url": full_url})

    return items


def parse_nasdaq(html: str) -> list[dict]:
    """解析 Nasdaq IR 新闻列表"""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    articles = (
        soup.select(".view-content .views-row")
        or soup.select("article")
        or soup.select(".search-result, .news-item")
        or soup.select("div.item, li.item")
    )

    if not articles:
        for link in soup.select("a[href]"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if title and len(title) > 20 and "/news/" in href.lower():
                full_url = href if href.startswith("http") else f"https://ir.nasdaq.com{href}"
                items.append({"title": title, "url": full_url})
    else:
        for article in articles:
            link = article.find("a", href=True)
            if not link:
                continue
            title = link.get_text(strip=True)
            href = link["href"]
            if not title:
                continue
            full_url = href if href.startswith("http") else f"https://ir.nasdaq.com{href}"
            items.append({"title": title, "url": full_url})

    return items


PARSERS = {
    "S&P Global - Index Changes": parse_spglobal,
    "Nasdaq IR - Index Changes": parse_nasdaq,
}


# ── 缓存与比较 ────────────────────────────────────────
def load_cache(cache_file: Path) -> set[str]:
    """加载已知条目的指纹集合"""
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        return set(data)
    return set()


def save_cache(cache_file: Path, fingerprints: set[str]):
    cache_file.write_text(json.dumps(sorted(fingerprints), ensure_ascii=False, indent=2))


def fingerprint(item: dict) -> str:
    """为单个条目生成唯一指纹"""
    raw = f"{item['title']}|{item['url']}"
    return hashlib.md5(raw.encode()).hexdigest()


# ── Telegram 通知 ──────────────────────────────────────
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
    print(f"✅ Telegram 通知已发送")


# ── 主逻辑 ─────────────────────────────────────────────
def check_target(target: dict) -> list[dict]:
    """检查单个目标页面，返回新增条目"""
    name = target["name"]
    url = target["url"]
    cache_file = target["cache_file"]

    print(f"\n🔍 正在检查: {name}")
    print(f"   URL: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"   ❌ 请求失败: {e}")
        return []

    parser = PARSERS[name]
    items = parser(resp.text)
    print(f"   📄 解析到 {len(items)} 条结果")

    if not items:
        print("   ⚠️ 未解析到任何条目（页面结构可能已变化）")
        page_hash = hashlib.md5(resp.text.encode()).hexdigest()
        old_cache = load_cache(cache_file)
        if page_hash not in old_cache:
            save_cache(cache_file, {page_hash})
            if old_cache:
                return [{"title": f"⚠️ {name} 页面内容有变化（未能解析具体条目，请手动查看）", "url": url}]
        return []

    old_fingerprints = load_cache(cache_file)
    new_items = []
    all_fingerprints = set()

    for item in items:
        fp = fingerprint(item)
        all_fingerprints.add(fp)
        if fp not in old_fingerprints:
            new_items.append(item)

    save_cache(cache_file, all_fingerprints)

    if not old_fingerprints:
        print(f"   📝 首次运行，已缓存 {len(all_fingerprints)} 条作为基线")
        return []

    if new_items:
        print(f"   🆕 发现 {len(new_items)} 条新消息!")
    else:
        print(f"   ✅ 无新消息")

    return new_items


def main():
    print("=" * 60)
    print("📡 指数调整新闻监控")
    print("=" * 60)

    all_new = []
    for target in TARGETS:
        new_items = check_target(target)
        if new_items:
            all_new.append((target["name"], new_items))

    if all_new:
        lines = ["🔔 <b>指数调整新消息</b>\n"]
        for source, items in all_new:
            lines.append(f"📌 <b>{source}</b>")
            for item in items:
                lines.append(f'  • <a href="{item["url"]}">{item["title"]}</a>')
            lines.append("")
        message = "\n".join(lines)
        send_telegram(message)
    else:
        print("\n✅ 所有页面均无新消息")


if __name__ == "__main__":
    main()
