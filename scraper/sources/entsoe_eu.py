"""
抓取 ENTSO-E 官网首页的"Latest News"板块（不再依赖第三方rss.app服务）。

之前用的是rss.app生成的第三方RSS，后来遇到"402 Payment Required"（免费额度用完），
所以放弃第三方路线。改用ENTSO-E官网首页(entsoe.eu)——这个首页本身是服务端直出的，
带一个"Latest News"板块，展示最新的几条新闻（标题+日期+链接），不需要JS渲染就能拿到。

⚠️ 这个是根据一次抓取结果写的选择器，还没有拿到真实原始HTML核对过具体的CSS结构。
如果跑出来是空的，运行:
    python -m scraper.debug_fetch entsoe
把原始HTML存到 data/debug/entsoe.html，用浏览器"检查元素"看一下"Latest News"
这个板块实际的HTML结构，再调整下面的选择器。

限制：首页的"Latest News"板块通常只展示最新的5条左右，不是完整历史存档，
但对日常增量抓取来说足够（新文章总会先出现在首页）。
"""
from __future__ import annotations

import re
from typing import List, Dict

from .base import fetch_html, make_absolute_url, soupify

SOURCE_NAME = "ENTSO-E"
LIST_URL = "https://www.entsoe.eu/"
BASE_URL = "https://www.entsoe.eu"

DATE_RE = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})")


def fetch_items(limit: int = 20) -> List[Dict]:
    html = fetch_html(LIST_URL)
    soup = soupify(html)

    items: List[Dict] = []
    seen_urls = set()

    # "Latest News"板块里的新闻链接，href形如 /news/2026/07/23/xxx-slug/
    news_links = [
        a for a in soup.find_all("a", href=True)
        if re.match(r"^/news/\d{4}/\d{2}/\d{2}/", a["href"])
    ]

    for a in news_links:
        title = a.get_text(strip=True)
        if not title:
            continue

        url = make_absolute_url(BASE_URL, a["href"])
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # 日期通常紧挨着标题链接出现（在标题前面），向前扫描找 DD/MM/YYYY 格式的日期文本
        published = None
        for el in a.find_all_previous(string=True, limit=10):
            match = DATE_RE.search(str(el))
            if match:
                d, m, y = match.group(1).split("/")
                published = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
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