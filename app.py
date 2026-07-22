"""
Streamlit 展示页面。

本地运行：
    streamlit run app.py

部署：推到 GitHub 仓库后，去 https://share.streamlit.io 用同一个GitHub账号登录，
选这个仓库、入口文件填 app.py，几分钟就能拿到公开链接。
"""
from __future__ import annotations

import re
from collections import Counter

import streamlit as st

from scraper import db

st.set_page_config(
    page_title="European Power Policy Monitor",
    page_icon="⚡",
    layout="wide",
)

# 每个数据源归属哪个国家/地区，用于按国家分栏展示
COUNTRY_MAP = {
    "CRE": "🇫🇷 France",
    "Ei": "🇸🇪 Sweden",
    "Svenska kraftnät": "🇸🇪 Sweden",
    "ACER": "🇪🇺 EU",
    "European Commission DG Energy": "🇪🇺 EU",
    "RTE": "🇫🇷 France",
    "RTE Publications": "🇫🇷 France",
    "ENTSO-E": "🇪🇺 EU",
    "Nord Pool": "🇪🇺 EU",
}
COUNTRY_ORDER = ["🇪🇺 EU", "🇫🇷 France", "🇸🇪 Sweden"]

# 关键词分类：标题里出现下面任一关键词，就归到对应分类（不用AI，纯字符串匹配）
CATEGORY_KEYWORDS = {
    "Capacity Market": ["capacity", "capacité"],
    "Grid / Network": ["grid", "réseau", "network", "nät", "transmission", "infrastructure"],
    "Tariffs / Pricing": ["tarif", "price", "pricing", "prix", "pris"],
    "Renewables": ["renewable", "solar", "wind", "éolien", "solaire", "vind", "sol"],
    "Auction / Consultation": ["auction", "consultation", "appel d'offres", "samråd"],
    "Gas": ["gas", "gaz"],
    "Market Report": ["report", "rapport", "bulletin", "observatoire"],
}

# 提取关键词时要过滤掉的常见虚词（英/法/瑞典语），避免"the"、"la"、"och"这类词占榜
STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "its", "are", "was",
    "will", "into", "have", "has", "des", "les", "sur", "pour", "avec", "dans",
    "une", "aux", "och", "att", "för", "från", "med", "som", "till", "vid",
    "sin", "sitt", "commission", "european", "news",
}


def extract_top_keywords(titles: list[str], top_n: int = 5) -> list[str]:
    words = []
    for title in titles:
        for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", title.lower()):
            if w not in STOPWORDS:
                words.append(w)
    return [w for w, _ in Counter(words).most_common(top_n)]


def match_categories(title: str) -> list[str]:
    title_lower = title.lower()
    return [
        cat for cat, keywords in CATEGORY_KEYWORDS.items()
        if any(kw in title_lower for kw in keywords)
    ]


conn = db.get_connection()
counts = db.count_by_source(conn)
total = sum(counts.values())
all_sources = list(counts.keys())

# 按国家汇总条数
country_counts: dict[str, int] = {}
for source, cnt in counts.items():
    country = COUNTRY_MAP.get(source, source)
    country_counts[country] = country_counts.get(country, 0) + cnt

# ---------- 一点自定义样式 ----------
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
    .source-tag {
        display: inline-block;
        font-size: 11px;
        color: #5b8def;
        background: #5b8def22;
        border-radius: 999px;
        padding: 1px 8px;
        margin-bottom: 6px;
        margin-right: 4px;
    }
    .category-tag {
        display: inline-block;
        font-size: 11px;
        color: #22c55e;
        background: #22c55e22;
        border-radius: 999px;
        padding: 1px 8px;
        margin-bottom: 6px;
    }
    .intel-box {
        background: #151b28;
        border: 1px solid #232b3d;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 20px;
    }
    .keyword-chip {
        display: inline-block;
        background: #232b3d;
        color: #e8ecf5;
        border-radius: 999px;
        padding: 3px 12px;
        margin: 2px 4px 2px 0;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ---------- 顶部标题 ----------
st.title("⚡ European Power Policy Monitor")
st.caption("EU · France · Sweden — Electricity Market Policy Tracker")

# ---------- Today's Intelligence 模块 ----------
all_titles = [row["title"] for row in db.fetch_all(conn)]
top_keywords = extract_top_keywords(all_titles)

with st.container():
    st.markdown('<div class="intel-box">', unsafe_allow_html=True)
    intel_cols = st.columns([1, 1, 1, 2])
    intel_cols[0].metric("总条数", total)
    intel_cols[1].metric("覆盖地区", len(country_counts))
    intel_cols[2].metric("数据来源数", len(all_sources))
    with intel_cols[3]:
        st.caption("热门关键词")
        if top_keywords:
            chips = "".join(f'<span class="keyword-chip">{kw}</span>' for kw in top_keywords)
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.caption("暂无数据")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ---------- 侧边栏：多层次竖列筛选（地区 → 来源 → 分类） ----------
with st.sidebar:
    st.header("筛选")

    # 第一层 + 第二层：地区展开后勾选具体来源，竖着排列
    st.subheader("地区 / 来源")
    selected_sources: list[str] = []
    available_countries = [c for c in COUNTRY_ORDER if c in country_counts]
    for country in available_countries:
        sources_in_country = [s for s in all_sources if COUNTRY_MAP.get(s, s) == country]
        with st.expander(f"{country} ({country_counts.get(country, 0)})", expanded=True):
            for source in sources_in_country:
                checked = st.checkbox(
                    f"{source} ({counts.get(source, 0)})",
                    value=True,
                    key=f"src_{source}",
                )
                if checked:
                    selected_sources.append(source)

    st.divider()

    # 第三层：分类筛选（竖着的复选框列表）
    st.subheader("分类")
    selected_categories = []
    for cat in CATEGORY_KEYWORDS:
        if st.checkbox(cat, value=True, key=f"cat_{cat}"):
            selected_categories.append(cat)

    st.divider()
    search_text = st.text_input("搜索标题关键词", placeholder="例如：tarif、capacity、nätavgift...")
    st.caption(f"数据库位置：{db.DB_PATH}")

# ---------- 主体：按国家分栏，每栏内按来源分组，再按分类过滤 ----------
selected_countries = [c for c in available_countries
                      if any(COUNTRY_MAP.get(s, s) == c for s in selected_sources)]

if not selected_sources:
    st.info("请在左侧至少选择一个来源。")
else:
    columns = st.columns(len(selected_countries)) if selected_countries else []
    for col, country in zip(columns, selected_countries):
        with col:
            st.subheader(country)
            sources_in_country = [s for s in selected_sources if COUNTRY_MAP.get(s, s) == country]
            shown_any = False
            for source in sources_in_country:
                items = db.fetch_all(conn, source=source, search=search_text or None)
                for it in items:
                    item_categories = match_categories(it["title"])
                    # 如果这条新闻匹配到了分类，但没有一个分类被勾选，就跳过
                    if item_categories and not any(c in selected_categories for c in item_categories):
                        continue
                    shown_any = True
                    date_txt = it["published"] or "日期未知"
                    cat_tags = "".join(
                        f'<span class="category-tag">{c}</span>' for c in item_categories
                    )
                    st.markdown(
                        f"""<div class="news-card">
                            <span class="source-tag">{source}</span>{cat_tags}
                            <span class="news-date">{date_txt}</span>
                            <a href="{it['url']}" target="_blank">{it['title']}</a>
                        </div>""",
                        unsafe_allow_html=True,
                    )
            if not shown_any:
                st.caption("暂无匹配结果")

conn.close()