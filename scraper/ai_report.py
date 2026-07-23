"""
用 Google Gemini（免费额度）生成每日更新的"过去7天"市场政策周报。

需要环境变量 GEMINI_API_KEY（去 https://aistudio.google.com/apikey 免费申请）。
没有设置这个环境变量的话会跳过，不影响其他抓取流程。

结构设计（按实际效果确定的最终版本）：
1. 整体概览：纯事实性总结本周发生了什么，2-4句话，不做延伸分析
2. 分地区分析：每个地区单独调用AI，基于新闻正文内容做深度解读，
   格式是"2-3个加粗小标题 + 每个小标题下面一段解释"，不用[编号]引用标注
3. 本周参考来源：统一放在报告最后一个区块，按地区分小节列出

每条新闻的来源名、链接都是代码自己拼接的，不依赖AI复述，保证准确。
"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .regions import get_country, COUNTRY_ORDER

CANDIDATE_MODELS = [
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash",
]

BUSINESS_CONTEXT = """
背景信息：本报告服务对象是中广核欧洲能源公司，一家发电商（主要资产为风电）。
目前售电主要依赖平衡责任商（BRP）代理，正在筹备转向自主参与电力交易
（自己承担平衡责任、参与日前/日内现货市场及辅助服务市场）。

据此，判断新闻业务相关性时，请按以下优先级：

【高相关性，值得重点展开】
- 平衡责任与不平衡结算规则（费率、容忍度、罚则变化）
- 日前/日内现货市场设计（撮合机制、报价规则、出清方式变化）
- 辅助服务市场、容量市场的准入规则（新的收益渠道）
- 风电/可再生能源专属的市场准入、PPA、绿证机制
- 跨境产能分配与市场耦合规则（Flow-Based等，影响价差）

【低相关性，一笔带过即可，不用展开分析】
- 终端消费者/工业用户的电价补贴、关税优惠
- 偏宏观的长期战略规划文件（除非包含近期生效的具体规则）
- 与风电资产、自主交易业务无直接关联的新闻
"""

MAX_ARTICLE_CHARS = 2500
FETCH_TIMEOUT = 15


def _group_by_region(items: List[Dict]) -> Dict[str, List[Dict]]:
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for it in items:
        region = get_country(it["source"])
        grouped[region].append(it)
    return grouped


def _ordered_regions(grouped: Dict[str, List[Dict]]) -> List[str]:
    ordered = [r for r in COUNTRY_ORDER if r in grouped]
    ordered += [r for r in grouped if r not in COUNTRY_ORDER]
    return ordered


def _fetch_article_text(url: str) -> Optional[str]:
    if url.lower().endswith(".pdf"):
        return None
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        container = soup.find("article") or soup.find("main") or soup.body
        if not container:
            return None
        text = container.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:MAX_ARTICLE_CHARS] if text else None
    except Exception:
        return None


def _entry_block(it: Dict) -> str:
    date_txt = it.get("published") or "日期未知"
    content = it.get("_article_text")
    body = f"正文摘录：{content}" if content else "（未能获取正文，仅有标题）"
    return f"[{it['source']}] {date_txt} 《{it['title']}》\n{body}"


def _build_overview_prompt(all_items: List[Dict]) -> str:
    joined = "\n\n".join(_entry_block(it) for it in all_items)
    return f"""以下是过去7天欧盟/法国/瑞典电力市场监管机构和电网运营商发布的新闻：

{joined}

请写一段"整体概览"，要求：
1. 第一句话必须是一句高度概括、指向性明确的总起句，点出本周电力市场政策/监管动态
   聚焦在哪几个主题方向上，例如"本周欧洲电力市场政策与监管动态聚焦于XX、XX以及XX"
   这种句式，把本周内容归纳成2-4个关键词/主题短语
2. 第一句话之后，再展开具体讲了哪些内容，纯事实性总结，不做延伸分析、不做判断和预测
3. 总共3-5句话，覆盖本周最主要的几个动向即可，不需要逐条提及
4. 结构上先讲欧盟层面的政策动态，再讲各国层面的动态，
   类似"欧盟层面...；国家层面，法国...，瑞典..."这种先欧洲后国家的句式
5. 聚焦在政策/市场动态本身是什么，不用刻意点出是哪个机构、谁提出、谁提议
6. 如果本周有跟"平衡责任/自主交易/辅助服务市场/风电资产"直接相关的重大动态，
   可以在这句总起句或后续描述里适当体现，但不用展开分析，只是概览层面的侧重
7. 面向关注电价预测的专业人士，语言简洁
8. 直接输出正文，不要加"以下是概览"这类开场白，不要分点，就是一段连续的话
"""


def _build_region_prompt(region: str, items: List[Dict]) -> str:
    joined = "\n\n".join(_entry_block(it) for it in items)
    return f"""你是一位专注欧洲电力市场的分析师。{BUSINESS_CONTEXT} 以下是{region}地区过去7天的电力市场政策/监管新闻：

{joined}

请基于以上内容，写{region}地区的电力市场政策分析，格式要求（严格遵守）：
- 从上面的新闻里选出最值得关注的2-4条（业务相关性高的优先选，业务相关性低的可以不选），
  每条一个条目
- 每个条目先用**加粗的短标题**概括这个主题（8-15字左右，例如"**跨国容量计算与阻塞管理规则升级**"），
  单独一行
- 标题下面紧跟一段话（2-3句）展开解释，基于正文内容做实质分析——重点说清楚这对公司
  未来自主交易/平衡责任/辅助服务收益的具体影响（如果这条新闻跟这些不直接相关，
  正常做政策解读即可，不用生硬联系业务），给出你自己的解读判断，不要只是转述标题
- 如果某条新闻只有标题没有正文，基于标题谨慎推测即可，不要编造正文没有提到的具体数字或细节
- 【严格禁止】不要在结尾罗列"参考来源"、编号列表、链接或任何形式的来源清单——
  这部分已经在上面的表格里体现了，你如果写了会导致重复显示
- 语言简洁专业
- 直接输出内容，不要加"以下是分析"这类开场白，不要在结尾加任何来源/参考相关的文字
"""


def _format_references_section(grouped: Dict[str, List[Dict]], region_order: List[str]) -> str:
    lines = ["## 本周参考来源\n"]
    for region in region_order:
        lines.append(f"\n**{region}**")
        for it in grouped[region]:
            date_txt = it.get("published") or "日期未知"
            lines.append(f"- [{date_txt}] [{it['source']}] [{it['title']}]({it['url']})")
    return "\n".join(lines)


def _call_gemini(client, prompt: str) -> Optional[str]:
    for model_name in CANDIDATE_MODELS:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            text = (response.text or "").strip()
            if text:
                return text
        except Exception as e:
            print(f"[ai_report]   模型 {model_name} 调用失败: {e}，尝试下一个候选模型...")
            continue
    return None

def _strip_trailing_references(text: str) -> str:
    """防御性清理：如果AI没听话，自己在结尾加了一份来源列表/编号引用，
    这里用启发式规则把这部分切掉，避免和代码自动生成的来源列表重复。"""
    import re
    # 匹配"参考来源"、"来源："这类标题开头的尾部区块，直接切掉这部分及其后面的内容
    match = re.search(r"\n\s*(参考来源|来源[:：]|References?)[:：]?\s*\n", text)
    if match:
        text = text[:match.start()]
    return text.strip()

def generate_weekly_report(items: List[Dict]) -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ai_report] 未设置 GEMINI_API_KEY，跳过报告生成")
        return None
    if not items:
        print("[ai_report] 最近7天没有新闻，跳过报告生成")
        return None
    try:
        from google import genai
    except ImportError:
        print("[ai_report] 未安装 google-genai 包，运行: pip install google-genai")
        return None

    grouped = _group_by_region(items)
    region_order = _ordered_regions(grouped)
    all_items = [it for region in region_order for it in grouped[region]]

    print(f"[ai_report] 正在抓取全部 {len(all_items)} 条新闻的正文...")
    for it in all_items:
        it["_article_text"] = _fetch_article_text(it["url"])
    got_text_count = sum(1 for it in all_items if it.get("_article_text"))
    print(f"[ai_report]   成功抓到正文 {got_text_count}/{len(all_items)} 条")

    client = genai.Client(api_key=api_key)

    print("[ai_report] 生成整体概览...")
    overview = _call_gemini(client, _build_overview_prompt(all_items))

    report_parts = []
    if overview:
        report_parts.append(f"## 整体概览\n\n{overview}")

    any_region_ok = False
    for region in region_order:
        region_items = grouped[region]
        print(f"[ai_report] 生成 {region} 地区分析...")
        analysis = _call_gemini(client, _build_region_prompt(region, region_items))
        if analysis:
            analysis = _strip_trailing_references(analysis)
            report_parts.append(f"## {region}\n\n{analysis}")
            any_region_ok = True
        else:
            print(f"[ai_report]   {region} 的AI分析生成失败，跳过")

    if not any_region_ok:
        print("[ai_report] 所有地区分析都失败了，本次跳过报告生成")
        return None

    report_parts.append(_format_references_section(grouped, region_order))
    return "\n\n---\n\n".join(report_parts)