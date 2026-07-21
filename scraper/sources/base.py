"""公共工具函数：请求、解析、URL处理"""
from __future__ import annotations

import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    # 表明这是一个正常浏览器请求，很多政府网站对无User-Agent的请求会拒绝
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

TIMEOUT = 40  # 部分政府网站响应较慢，20秒偶尔不够，放宽到40秒
RETRIES = 2   # 超时/失败后自动重试的次数
RETRY_DELAY = 3  # 重试前等待秒数


def fetch_html(url: str) -> str:
    last_error = None
    for attempt in range(1, RETRIES + 2):  # 共尝试 1 + RETRIES 次
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding
            return resp.text
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt <= RETRIES:
                print(f"  请求失败（第{attempt}次尝试）: {e}，{RETRY_DELAY}秒后重试...")
                time.sleep(RETRY_DELAY)
    raise last_error


def soupify(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def make_absolute_url(base: str, href: str) -> str:
    return urljoin(base, href)
