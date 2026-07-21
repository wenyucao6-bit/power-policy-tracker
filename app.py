"""
Streamlit 展示页面。

本地运行：
    streamlit run app.py

部署：推到 GitHub 仓库后，去 https://share.streamlit.io 用同一个GitHub账号登录，
选这个仓库、入口文件填 app.py，几分钟就能拿到公开链接。
"""
from __future__ import annotations

import streamlit as st

from scraper import db

st.set_page_config(
    page_title="欧盟/法国/瑞典 电力市场政策追踪",
    page_icon="⚡",
    layout="wide",
)

# ---------- 一点自定义样式，让卡片更好看 ----------
st.markdown("""
<style>
    .news-card {
        background: #151b28;
        border: 1px solid #232b3d;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .news-card a {
        color: #e8ecf5;
        text-decoration: none;
        font-size: 14px;
    }
    .news-card a:hover { color: #5b8def; }
    .news-date {
        color: #7c8698;
        font-size: 12px;
        display: block;
        margin-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)

conn = db.get_connection()
counts = db.count_by_source(conn)
total = sum(counts.values())

# ---------- 顶部：今日概览 ----------
st.title("⚡ 欧盟 / 法国 / 瑞典 电力市场政策追踪")

metric_cols = st.columns(4)
metric_cols[0].metric("总条数", total)
metric_cols[1].metric("CRE (法国)", counts.get("CRE (法国)", 0))
metric_cols[2].metric("Ei (瑞典)", counts.get("Ei (瑞典)", 0))
metric_cols[3].metric("ACER (欧盟)", counts.get("ACER (欧盟)", 0))

st.divider()

# ---------- 侧边栏：筛选 ----------
with st.sidebar:
    st.header("筛选")
    all_sources = list(counts.keys())
    selected_sources = st.multiselect("来源", options=all_sources, default=all_sources)
    search_text = st.text_input("搜索标题关键词", placeholder="例如：tarif、capacity、nätavgift...")
    st.caption(f"数据库位置：{db.DB_PATH}")

# ---------- 主体：新闻列表（按来源分栏） ----------
if not selected_sources:
    st.info("请在左侧至少选择一个来源。")
else:
    columns = st.columns(len(selected_sources))
    for col, source in zip(columns, selected_sources):
        with col:
            st.subheader(source)
            items = db.fetch_all(conn, source=source, search=search_text or None)
            if not items:
                st.caption("暂无匹配结果")
            for it in items:
                date_txt = it["published"] or "日期未知"
                st.markdown(
                    f"""<div class="news-card">
                        <span class="news-date">{date_txt}</span>
                        <a href="{it['url']}" target="_blank">{it['title']}</a>
                    </div>""",
                    unsafe_allow_html=True,
                )

conn.close()
