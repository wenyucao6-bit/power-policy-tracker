"""
抓取瑞典能源市场监察局 (Ei, Energimarknadsinspektionen) 的新闻列表页

⚠️ 重要：https://ei.se/om-oss/nyheter 这个页面本身是空壳，新闻列表是
页面加载后用JS异步请求下面这个接口填进去的（SiteVision的搜索组件）：
    /4.668ca5111744c9a9eed32e24/12.91d19d217638286b77fc8.htm
        ?state=ajaxQuery&isRenderingAjaxResult=true&query=*
所以直接抓这个接口的返回HTML片段，不用等JS执行。

如果以后这个接口路径失效（网站改版后SiteVision组件ID会变），
需要重新打开 https://ei.se/om-oss/nyheter，F12打开Network面板，
搜索 "query=*" 或 "ajaxQuery" 找新的接口地址。

链接格式类似: /om-oss/nyheter/2026/2026-03-19-eis-uppdrag-om-effektavgifter...
标题前面通常带有 YYYY-MM-DD 日期。
"""
from __future__ import annotations

import re
from typing import List, Dict

from .base import fetch_html, make_absolute_url, soupify

SOURCE_NAME = "Ei"
BASE_URL = "https://ei.se"
LIST_URL = (
    BASE_URL
    + "/4.668ca5111744c9a9eed32e24/12.91d19d217638286b77fc8.htm"
    + "?state=ajaxQuery&isRenderingAjaxResult=true&query=*"
)

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def fetch_items(limit: int = 20) -> List[Dict]:
    html = fetch_html(LIST_URL)
    soup = soupify(html)

    items: List[Dict] = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/om-oss/nyheter/" not in href:
            continue
        if href.rstrip("/").endswith("/om-oss/nyheter"):
            continue

        title = a.get_text(strip=True)
        if not title:
            continue

        url = make_absolute_url(BASE_URL, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # 日期通常直接编码在URL里 (/nyheter/2026/2026-03-19-xxx)
        date_match = DATE_RE.search(href)
        published = date_match.group(1) if date_match else None

        items.append({
            "source": SOURCE_NAME,
            "title": title,
            "url": url,
            "published": published,
        })

        if len(items) >= limit:
            break

    return items
