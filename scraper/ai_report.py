"""
用 Google Gemini（免费额度）生成每日更新的"过去7天"市场政策周报。

需要环境变量 GEMINI_API_KEY（去 https://aistudio.google.com/apikey 免费申请）。
没有设置这个环境变量的话会跳过，不影响其他抓取流程。

设计思路：
- AI只负责"叙述分析"部分（不要求它逐字复述原文链接，避免AI编造/记错网址）
- 每条新闻真实的来源和链接，由代码自己拼接成"参考来源"列表附在报告最后，
  保证链接100%准确，不依赖AI的记忆
"""
from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, List, Optional

from .regions import get_country

# Google免费额度里可用的模型经常调整（2026年4月起老版本陆续收窄成付费专用），
# 与其写死一个具体型号名，不如按顺序尝试几个候选，哪个能用就用哪个，
# 这样以后Google再调整免费模型列表，也不用每次都回来改代码。
CANDIDATE_MODELS = [
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash",
]


def _group_by_region(items: List[Dict]) -> Dict[str, List[Dict]]:
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for it in items:
        region = get_country(it["source"])
        grouped[region].append(it)
    return grouped


def _build_prompt(grouped: Dict[str, List[Dict]]) -> str:
    sections = []
    for region, items in grouped.items():
        lines = [f"- [{it['source']}] {it.get('published') or '日期未知'} {it['title']}" for it in items]
        sections.append(f"### {region}\n" + "\n".join(lines))
    joined = "\n\n".join(sections)

    return f"""你是一位专注欧洲电力市场的分析师。以下是过去7天欧盟/法国/瑞典电力监管机构和电网运营商发布的新闻标题，按地区分组：

{joined}

请用中文写一份结构化的"每周电力市场政策简报"，要求：
1. 开头一段总览（2-3句话），概括本周整体趋势
2. 按地区分节（欧盟 / 法国 / 瑞典），每节总结2-4条最值得关注的政策动向或市场信号，
   提炼共性主题，不需要逐条复述所有新闻
3. 面向关注电价预测的专业人士，语言简洁、突出对市场/价格可能有影响的信息
4. 不要编造原文没有的具体数字或链接
5. 直接输出正文，不要加"以下是简报"这类开场白
"""


def _format_references(grouped: Dict[str, List[Dict]]) -> str:
    """代码自己拼接参考来源列表，保证链接准确，不依赖AI复述。"""
    lines = ["\n\n---\n\n## 本周参考来源\n"]
    for region, items in grouped.items():
        lines.append(f"\n**{region}**")
        for it in items:
            date_txt = it.get("published") or "日期未知"
            lines.append(f"- [{date_txt}] [{it['source']}] [{it['title']}]({it['url']})")
    return "\n".join(lines)


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
    prompt = _build_prompt(grouped)

    client = genai.Client(api_key=api_key)
    analysis = None
    for model_name in CANDIDATE_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            analysis = (response.text or "").strip()
            if analysis:
                print(f"[ai_report] 使用模型 {model_name} 生成成功")
                break
        except Exception as e:
            print(f"[ai_report] 模型 {model_name} 调用失败: {e}，尝试下一个候选模型...")
            continue

    if not analysis:
        print("[ai_report] 所有候选模型都失败了，本次跳过报告生成")
        return None

    return analysis + _format_references(grouped)