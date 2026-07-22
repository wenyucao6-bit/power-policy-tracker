"""
抓取 ENTSO-E 的新闻。

ENTSO-E官网的新闻列表页 (https://www.entsoe.eu/news-events/news/) 是JS异步加载的，
直接抓取拿不到内容，也没找到合规的官方RSS/API。这里改用第三方"网页转RSS"工具
(rss.app) 生成的RSS地址，它帮我们处理了JS渲染的问题。

⚠️ 依赖第三方服务，如果这个RSS地址失效（比如免费额度到期），需要重新生成一个
并更新下面的 RSS_URL。

这个feed里混杂了新闻(NEWS)和活动预告(EVENT)两种内容（用description开头的
[NEWS]/[EVENT]标签区分），这里只保留新闻，活动预告(webinar通知之类)跟政策
动态关系不大，先过滤掉。
"""
from __future__ import annotations

from typing import List, Dict
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime

from .base import fetch_html, make_absolute_url

SOURCE_NAME = "ENTSO-E"
BASE_URL = "https://www.entsoe.eu"
RSS_URL = "https://rss.app/feeds/043Zhn5HHw4gj99D.xml"


def fetch_items(limit: int = 30) -> List[Dict]:
    xml_text = fetch_html(RSS_URL)
    root = ET.fromstring(xml_text)

    items: List[Dict] = []
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        date_el = item.find("pubDate")

        title = (title_el.text or "").strip() if title_el is not None else None
        link = (link_el.text or "").strip() if link_el is not None else None
        description = (desc_el.text or "") if desc_el is not None else ""

        if not title or not link:
            continue

        # 只保留新闻，过滤掉活动预告(webinar通知等)
        if "[EVENT]" in description and "[NEWS]" not in description:
            continue

        published = None
        if date_el is not None and date_el.text:
            try:
                published = parsedate_to_datetime(date_el.text.strip()).date().isoformat()
            except (TypeError, ValueError):
                pass

        items.append({
            "source": SOURCE_NAME,
            "title": title,
            "url": make_absolute_url(BASE_URL, link),
            "published": published,
        })

        if len(items) >= limit:
            break

    return items