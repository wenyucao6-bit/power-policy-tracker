"""
调试小工具：把某个数据源的原始HTML存到 data/debug/ 下面，
方便你打开浏览器"查看网页源代码"/"检查元素"，对照实际结构调整抓取选择器。

用法（在项目根目录下）：
    python -m scraper.debug_fetch cre
    python -m scraper.debug_fetch ei
    python -m scraper.debug_fetch acer
"""
import sys
from pathlib import Path

from .sources import cre_france, ei_sweden, acer_eu
from .sources.base import fetch_html

SOURCES = {
    "cre": cre_france.LIST_URL,
    "ei": ei_sweden.LIST_URL,
    "acer": acer_eu.LIST_URL,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in SOURCES:
        print(f"用法: python -m scraper.debug_fetch [{'|'.join(SOURCES)}]")
        sys.exit(1)

    key = sys.argv[1]
    url = SOURCES[key]
    print(f"正在抓取 {url} ...")
    html = fetch_html(url)

    out_dir = Path(__file__).resolve().parent.parent / "data" / "debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{key}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"已保存到 {out_path}，用浏览器打开看看实际结构。")


if __name__ == "__main__":
    main()
