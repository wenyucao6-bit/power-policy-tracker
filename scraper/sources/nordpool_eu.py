"""
抓取 Nord Pool（北欧电力市场）的新闻公告，用官方RSS。

在 https://www.nordpoolgroup.com/en/message-center-container/newsroom/exchange-message-list/
这个新闻列表页面里发现的官方RSS地址，是Nord Pool自己提供的，不依赖第三方服务。
"""
from __future__ import annotations

from typing import List, Dict

from .base import fetch_html, parse_rss

SOURCE_NAME = "Nord Pool"
RSS_URL = "https://www.nordpoolgroup.com/en/message-center-container/newsroom/exchange-message-list/Rss/"


def fetch_items(limit: int = 20) -> List[Dict]:
    xml_text = fetch_html(RSS_URL)
    return parse_rss(xml_text, SOURCE_NAME, limit=limit)