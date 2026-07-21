"""
每日运行的主脚本：
1. 依次抓取 CRE(法国) / Ei(瑞典) / ACER(欧盟) 的最新动态
2. 和历史数据合并去重，按日期倒序排列
3. 写入 data/news.json
4. 用 data/news.json 渲染出 docs/index.html 静态页面

用法：
    python -m scraper.main
"""
from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .sources import cre_france, ei_sweden, acer_eu

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "news.json"
HTML_OUT = ROOT / "docs" / "index.html"

SOURCES = [
    ("cre_france", cre_france),
    ("ei_sweden", ei_sweden),
    ("acer_eu", acer_eu),
]


def load_existing() -> List[Dict]:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def dedupe_and_merge(existing: List[Dict], fresh: List[Dict]) -> List[Dict]:
    by_url = {item["url"]: item for item in existing}
    for item in fresh:
        by_url[item["url"]] = item  # 新抓到的信息覆盖旧的（比如日期补全了）

    merged = list(by_url.values())
    # 排序：有日期的按日期倒序，没日期的排最后
    merged.sort(key=lambda x: (x.get("published") or ""), reverse=True)
    return merged


def run_all_scrapers() -> List[Dict]:
    all_items: List[Dict] = []
    for name, module in SOURCES:
        try:
            items = module.fetch_items()
            print(f"[{name}] 抓到 {len(items)} 条")
            all_items.extend(items)
        except Exception as e:
            # 单个来源失败不应该让整个脚本挂掉
            print(f"[{name}] 抓取失败: {e}")
            traceback.print_exc()
    return all_items


def render_html(items: List[Dict], updated_at: str) -> str:
    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    groups: Dict[str, List[Dict]] = {}
    for item in items:
        groups.setdefault(item["source"], []).append(item)

    section_html = []
    for source, group_items in groups.items():
        rows = []
        for it in group_items[:50]:  # 每个来源最多展示50条，避免页面过长
            date_txt = it.get("published") or "日期未知"
            rows.append(f"""
            <li class="news-item">
                <span class="date">{esc(date_txt)}</span>
                <a href="{esc(it['url'])}" target="_blank" rel="noopener noreferrer">{esc(it['title'])}</a>
            </li>""")
        section_html.append(f"""
        <section class="source-block">
            <h2>{esc(source)}</h2>
            <ul>{''.join(rows)}</ul>
        </section>""")

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>欧盟/法国/瑞典 电力市场政策追踪</title>
<style>
  :root {{
    --bg: #0f1420;
    --card: #171d2b;
    --text: #e8ecf5;
    --muted: #8b95ab;
    --accent: #5b8def;
    --border: #262d3d;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
  }}
  header {{
    padding: 32px 24px 16px;
    max-width: 900px;
    margin: 0 auto;
  }}
  header h1 {{
    font-size: 24px;
    margin: 0 0 4px;
  }}
  header p {{
    color: var(--muted);
    font-size: 14px;
    margin: 0;
  }}
  main {{
    max-width: 900px;
    margin: 0 auto;
    padding: 0 24px 48px;
    display: grid;
    gap: 20px;
  }}
  .source-block {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px;
  }}
  .source-block h2 {{
    font-size: 16px;
    margin: 0 0 12px;
    color: var(--accent);
  }}
  ul {{
    list-style: none;
    margin: 0;
    padding: 0;
  }}
  .news-item {{
    padding: 10px 0;
    border-bottom: 1px solid var(--border);
    display: flex;
    gap: 14px;
    align-items: baseline;
  }}
  .news-item:last-child {{ border-bottom: none; }}
  .date {{
    color: var(--muted);
    font-size: 12px;
    white-space: nowrap;
    min-width: 84px;
  }}
  a {{
    color: var(--text);
    text-decoration: none;
    font-size: 14px;
  }}
  a:hover {{ color: var(--accent); text-decoration: underline; }}
</style>
</head>
<body>
<header>
  <h1>⚡ 欧盟 / 法国 / 瑞典 电力市场政策追踪</h1>
  <p>数据来源：CRE（法国能源监管委员会）、Ei（瑞典能源市场监察局）、ACER（欧盟能源监管机构合作署）。最后更新：{esc(updated_at)}</p>
</header>
<main>
{''.join(section_html)}
</main>
</body>
</html>
"""


def main():
    existing = load_existing()
    fresh = run_all_scrapers()
    merged = dedupe_and_merge(existing, fresh)

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"共保存 {len(merged)} 条记录到 {DATA_FILE}")

    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(render_html(merged, updated_at), encoding="utf-8")
    print(f"已生成展示页 {HTML_OUT}")


if __name__ == "__main__":
    main()
