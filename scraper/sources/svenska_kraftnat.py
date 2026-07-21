"""
抓取瑞典国家电网 (Svenska kraftnät) 的新闻，用官方RSS，比解析HTML更稳定可靠。
RSS地址: https://www.svk.se/Api/RSSFeed/GetAllNews
"""
from __future__ import annotations

from typing import List, Dict

from .base import fetch_html, parse_rss

SOURCE_NAME = "Svenska kraftnät (瑞典)"
RSS_URL = "https://www.svk.se/Api/RSSFeed/GetAllNews"


def fetch_items(limit: int = 20) -> List[Dict]:
    xml_text = fetch_html(RSS_URL)
    return parse_rss(xml_text, SOURCE_NAME, limit=limit)
