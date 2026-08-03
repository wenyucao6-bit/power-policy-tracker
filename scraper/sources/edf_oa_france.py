"""
监测 EDF OA 的"Arrêt ou limitation des sites sous OA"（Smart OA强制限电机制）页面。

这不是一个"新闻列表"，是一个单页面的监管说明文档，EDF OA会不定期更新内容
（比如新发布的政策文件、新的操作细则）。页面本身带一个精确的"最后更新时间"
（HTML的 <meta property="article:modified_time"> 标签，页面上也显示"Mis à jour le
DD/MM/YYYY"文字），我们把这个更新时间当作这条新闻的published日期。

这样设计的好处：因为数据库是按url做upsert更新的，只要这个页面的更新时间变了，
这一条记录的published会被刷新成新日期，自然会重新进入"最近7天"的范围，
在主列表和AI周报里重新出现，不需要额外写"变化检测"逻辑。如果页面没更新，
每次抓到的日期都一样，7天之后会自动从"最近动态"里淡出，不会一直刷屏。
"""
from __future__ import annotations

import re
from typing import List, Dict

from .base import fetch_html, soupify

SOURCE_NAME = "EDF OA"
PAGE_URL = "https://www.edf-oa.fr/collectivite-et-entreprise/ressources-reglementaires/arret-ou-limitation-des-sites-sous-oa"
TITLE = "Arrêt ou limitation des sites sous OA (dispositif Smart OA)"

DATE_TEXT_RE = re.compile(r"Mis à jour le (\d{2})/(\d{2})/(\d{4})")


def fetch_items(limit: int = 1) -> List[Dict]:
    html = fetch_html(PAGE_URL)
    soup = soupify(html)

    published = None

    # 优先用meta标签里的精确时间戳（格式类似 2026-07-28T10:57:13+02:00）
    meta_tag = soup.find("meta", attrs={"property": "article:modified_time"})
    if meta_tag and meta_tag.get("content"):
        published = meta_tag["content"][:10]

    # meta标签抓不到的话，退而用页面正文里的"Mis à jour le DD/MM/YYYY"文字
    if not published:
        match = DATE_TEXT_RE.search(soup.get_text(" ", strip=True))
        if match:
            day, month, year = match.groups()
            published = f"{year}-{month}-{day}"

    return [{
        "source": SOURCE_NAME,
        "title": TITLE,
        "url": PAGE_URL,
        "published": published,
    }]