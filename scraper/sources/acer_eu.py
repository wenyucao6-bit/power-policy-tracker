"""
抓取欧盟能源监管机构合作署 (ACER) 的新闻页
页面: https://www.acer.europa.eu/news-and-events/news

已根据实际抓到的HTML核对过结构（Drupal Views渲染，服务端直出）：
每条新闻在 <div class="views-row ...">，标题链接 href 形如 /news/xxx-slug，
日期形如 "17th July 2026"（带序数词后缀），转换成标准 YYYY-MM-DD 格式存储，
跟其他数据源保持一致，避免排序/筛选时出现字符串比较导致的顺序错乱。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Dict, Optional

from .base import fetch_html, make_absolute_url, soupify

SOURCE_NAME = "ACER"
LIST_URL = "https://www.acer.europa.eu/news-and-events/news"
BASE_URL = "https://www.acer.europa.eu"

# 实际HTML里日期形如 "17th July 2026"，带序数词后缀（st/nd/rd/th）
DATE_RE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})")


def _parse_date(text: str) -> Optional[str]:
    """把 "17th July 2026" 这种带序数词后缀的英文日期转成 YYYY-MM-DD。"""
    match = DATE_RE.search(text)
    if not match:
        return None
    day, month_name, year = match.groups()
    try:
        dt = datetime.strptime(f"{day} {month_name} {year}", "%d %B %Y")
        return dt.date().isoformat()
    except ValueError:
        return None


def fetch_items(limit: int = 20) -> List[Dict]:
    html = fetch_html(LIST_URL)
    soup = soupify(html)

    items: List[Dict] = []
    seen_urls = set()

    # 新闻条目在 <div class="views-row ..."> 里，标题链接的 href 形如 /news/xxx-slug
    # （注意不是 /news-and-events/news/xxx，之前猜错了）
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("/news/"):
            continue

        title = a.get_text(strip=True)
        if not title or len(title) < 8 or title.lower() in ("read more", "en savoir plus"):
            continue

        url = make_absolute_url(BASE_URL, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        published = None
        container = a
        for _ in range(4):
            if container is None:
                break
            container = container.parent
            if container is None:
                break
            published = _parse_date(container.get_text(" ", strip=True))
            if published:
                break

        items.append({
            "source": SOURCE_NAME,
            "title": title,
            "url": url,
            "published": published,
        })

        if len(items) >= limit:
            break

    return items