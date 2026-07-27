"""
每日运行的抓取脚本：
1. 依次抓取 CRE(法国) / Ei(瑞典) / ACER(欧盟) 的最新动态
2. 写入 SQLite (data/policy.db)，url 相同的自动更新、不会重复

展示交给 app.py（Streamlit）负责，这个脚本不再生成HTML。

用法：
    python -m scraper.scrape
"""
from __future__ import annotations

import traceback
from typing import Dict, List

from . import db
from . import ai_report
from .sources import cre_france, ei_sweden, acer_eu, svenska_kraftnat, european_commission, rte_france, entsoe_eu, nordpool_eu, rte_service_france

SOURCES = [
    ("cre_france", cre_france),
    ("ei_sweden", ei_sweden),
    ("acer_eu", acer_eu),
    ("svenska_kraftnat", svenska_kraftnat),
    ("european_commission", european_commission),
    ("rte_france", rte_france),
    ("entsoe_eu", entsoe_eu),
    ("nordpool_eu", nordpool_eu),
    ("rte_service_france", rte_service_france),
]


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


def main():
    fresh = run_all_scrapers()

    conn = db.get_connection()
    db.upsert_items(conn, fresh)

    counts = db.count_by_source(conn)
    total = sum(counts.values())

    recent_items = db.fetch_recent(conn, days=7)
    print(f"最近7天共有 {len(recent_items)} 条新闻，准备生成AI周报...")
    report = ai_report.generate_weekly_report(recent_items)
    if report:
        db.save_weekly_brief(conn, report)
        print("AI周报已生成并保存")

    conn.close()

    print(f"数据库现有 {total} 条记录，按来源统计: {counts}")


if __name__ == "__main__":
    main()