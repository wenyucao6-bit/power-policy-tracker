"""
抓取 RTE 客户服务门户（Portail Services）的新闻，这里的内容更偏向市场参与者/
平衡责任商相关的服务变更公告（跟rte_france.py里的企业公关新闻性质不同）。

接口是通过浏览器F12抓包找到的，返回结构很简单：
[
    {"title": "...", "date": "2025-02-03T00:00:00+01:00", "path": "/fr/actualites/xxx.html"},
    ...
]
注意：源数据里偶尔path字段前面会有多余的空格/双斜杠（比如"/ /fr/actualites/..."），
拼接URL之前要清理一下。
"""
from __future__ import annotations

import json
import re
from typing import List, Dict

import requests


from .base import HEADERS, TIMEOUT, make_absolute_url


SOURCE_NAME = "RTE Services"
PAGE_URL = "https://www.services-rte.com/fr/actualites"
API_URL = "https://www.services-rte.com/cms/public/v1/news?locale=fr"
BASE_URL = "https://www.services-rte.com"


def fetch_items(limit: int = 20) -> List[Dict]:
    # 这个接口背后似乎依赖会话状态做负载均衡路由（抓包时看到JSESSIONID/ROUTEID这些cookie），
    # 直接裸请求API有时会遇到500错误。这里先访问一次正常网页建立会话，
    # 再用同一个session带着cookie去请求API，模拟真实浏览器的访问顺序。
    session = requests.Session()
    session.get(PAGE_URL, headers=HEADERS, timeout=TIMEOUT)  # 建立会话，结果不需要用
    resp = session.get(API_URL, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
 
    # 这个接口的返回结构不太稳定，有时候是纯数组[...]，有时候可能包了一层对象
    # 比如 {"news": [...]}。这里做个防御性处理：如果拿到的是字典，
    # 就找里面第一个值是"列表"的字段当作真正的新闻数据。
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                data = value
                break
 
    if not isinstance(data, list):
        print(f"[services_rte] 返回的数据结构不是预期的列表，跳过。实际类型: {type(data)}")
        return []

    
    items: List[Dict] = []
    for entry in data:
        title = (entry.get("title") or "").strip()
        path = (entry.get("path") or "").strip()
        date_str = entry.get("date") or ""

        if not title or not path:
            continue

        # 清理path里可能出现的多余空格和多余斜杠，比如 "/ /fr/actualites/xxx.html"
        # 注意：要把多个连续的开头斜杠合并成一个，不然"//fr/..."会被urljoin误判成
        # 协议相对URL（把"fr"当成域名），导致拼出来的链接是错的
        path = path.replace(" ", "")
        path = re.sub(r"^/+", "/", path)

        published = date_str[:10] if len(date_str) >= 10 else None

        items.append({
            "source": SOURCE_NAME,
            "title": title,
            "url": make_absolute_url(BASE_URL, path),
            "published": published,
        })

        if len(items) >= limit:
            break

    return items