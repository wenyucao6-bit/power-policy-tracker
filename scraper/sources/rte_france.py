"""
抓取法国电网 (RTE) 的"Espace presse et actualités"页面，包含两部分内容：

1. 新闻公告（Communiqués de presse）——支持翻页，把历史记录也一起抓下来
   页面: https://www.rte-france.com/presse (第一页) / ?page=1, ?page=2... (后续页)
   已根据实际HTML核对：每条在 <li> 里，<time datetime="..."> 给日期，<a href="/actualites/...">给标题链接

2. 精选文档（Les essentiels presse）——年度报告等PDF文档
   已根据实际HTML核对：每条在 <div class="document-item">，
   .media-download__date-span 给日期文本(DD/MM/YYYY)，.media-download__title a 给标题+PDF直链
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Dict

import requests

from .base import HEADERS, TIMEOUT, make_absolute_url, soupify

SOURCE_NAME = "RTE"
PUBLICATIONS_SOURCE_NAME = "RTE Publications"
LIST_URL = "https://www.rte-france.com/presse"
BASE_URL = "https://www.rte-france.com"

# 用同一个session访问两个函数需要的页面，模拟真实浏览器"先建立会话再请求"的顺序，
# 避免裸请求偶尔遇到重定向循环（"Exceeded 30 redirects"）的问题
_session = requests.Session()


def _get_html(url: str) -> str:
    resp = _session.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def _fetch_press_releases_page(page: int) -> List[Dict]:
    url = LIST_URL if page == 0 else f"{LIST_URL}?page={page}"
    html = _get_html(url)
    soup = soupify(html)

    items: List[Dict] = []
    for li in soup.find_all("li"):
        a = li.find("a", href=True)
        time_tag = li.find("time", attrs={"datetime": True})
        if not a or not time_tag:
            continue
        if "/actualites/" not in a["href"]:
            continue

        title = a.get_text(strip=True)
        if not title:
            continue

        items.append({
            "source": SOURCE_NAME,
            "title": title,
            "url": make_absolute_url(BASE_URL, a["href"]),
            "published": time_tag["datetime"][:10],
        })
    return items


def _fetch_press_releases() -> List[Dict]:
    """目前只抓第一页（约4条最新公告）。
    之前尝试的 ?page=1 这种翻页URL经验证是无效的（就算直接访问也是404），
    说明这个页面的翻页机制不是简单的URL参数，可能是JS异步请求实现的，
    跟当年Ei瑞典遇到的情况类似。历史存量数据以后需要单独调查翻页接口再补上，
    不影响日常增量抓取（新公告总会出现在第一页）。"""
    return _fetch_press_releases_page(0)


def _fetch_publications() -> List[Dict]:
    """抓"Les essentiels presse"精选文档区块（PDF报告）。
    这部分内容只在第一页出现，不用翻页。"""
    html = _get_html(LIST_URL)
    soup = soupify(html)

    items: List[Dict] = []
    for div in soup.find_all("div", class_="document-item"):
        date_span = div.find("span", class_="media-download__date-span")
        title_a = div.select_one(".media-download__title a")
        if not date_span or not title_a:
            continue

        title = title_a.get_text(strip=True)
        if not title:
            continue

        published = None
        date_text = date_span.get_text(strip=True)
        try:
            published = datetime.strptime(date_text, "%d/%m/%Y").date().isoformat()
        except ValueError:
            pass

        items.append({
            "source": PUBLICATIONS_SOURCE_NAME,
            "title": title,
            "url": title_a["href"],  # 这里已经是完整的PDF直链，不需要拼BASE_URL
            "published": published,
        })
    return items


def fetch_items(limit: int = 100) -> List[Dict]:
    items = _fetch_press_releases() + _fetch_publications()
    return items[:limit]