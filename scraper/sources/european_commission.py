"""
抓取欧盟委员会能源总司 (DG Energy) 的新闻，用官方RSS。
RSS地址: https://energy.ec.europa.eu/node/2/rss_en
"""
from __future__ import annotations

from typing import List, Dict

from .base import fetch_html, parse_rss

SOURCE_NAME = "European Commission DG Energy (欧盟)"
RSS_URL = "https://energy.ec.europa.eu/node/2/rss_en"


def fetch_items(limit: int = 20) -> List[Dict]:
    xml_text = fetch_html(RSS_URL)
    return parse_rss(xml_text, SOURCE_NAME, limit=limit)
