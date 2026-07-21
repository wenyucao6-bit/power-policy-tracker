"""
抓取法国能源监管委员会 (CRE) 的新闻列表页
页面: https://www.cre.fr/actualites/toute-lactualite.html

已根据实际抓到的HTML核对过结构：每条新闻是
    <li data-document-url="/actualites/toute-lactualite/xxx.html">
        ...
        <a href="同上的url">标题</a>
        ...
        <time datetime="2026-07-20T13:42:36+02:00">20/07/2026</time>
        ...
    </li>
日期直接从 <time> 标签的 datetime 属性拿（ISO格式，比解析"20/07/2026"文本更可靠）。
"""
from __future__ import annotations

from typing import List, Dict

from .base import fetch_html, make_absolute_url, soupify

SOURCE_NAME = "CRE (法国)"
LIST_URL = "https://www.cre.fr/actualites/toute-lactualite.html"
BASE_URL = "https://www.cre.fr"


def fetch_items(limit: int = 20) -> List[Dict]:
    html = fetch_html(LIST_URL)
    soup = soupify(html)

    items: List[Dict] = []

    list_items = soup.find_all("li", attrs={"data-document-url": True})
    for li in list_items:
        href = li["data-document-url"]
        url = make_absolute_url(BASE_URL, href)

        a = li.find("a", href=True)
        title = a.get_text(strip=True) if a else None
        if not title:
            continue

        published = None
        time_tag = li.find("time", attrs={"datetime": True})
        if time_tag:
            # datetime属性形如 "2026-07-20T13:42:36+02:00"，前10位就是 YYYY-MM-DD
            published = time_tag["datetime"][:10]

        items.append({
            "source": SOURCE_NAME,
            "title": title,
            "url": url,
            "published": published,
        })

        if len(items) >= limit:
            break

    return items
