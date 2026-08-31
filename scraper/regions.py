"""
统一管理"数据源属于哪个地区"这件事。
之前ACER出过bug就是因为这个映射在app.py和抓取脚本里各写一份、不同步，
现在统一放这一个文件，app.py和后台脚本都从这里导入，只需要维护一处。
"""

COUNTRY_MAP = {
    "CRE": "🇫🇷 France",
    "RTE": "🇫🇷 France",
    "RTE Publications": "🇫🇷 France",
    "RTE Services": "🇫🇷 France",
    "Ei": "🇸🇪 Sweden",
    "Svenska kraftnät": "🇸🇪 Sweden",
    "Nord Pool": "🇸🇪 Sweden",
    "ACER": "🇪🇺 EU",
    "European Commission DG Energy": "🇪🇺 EU",
    "ENTSO-E": "🇪🇺 EU",
    "EDF OA": "🇫🇷 France"
}

COUNTRY_ORDER = ["🇪🇺 EU", "🇫🇷 France", "🇸🇪 Sweden"]


def get_country(source: str) -> str:
    return COUNTRY_MAP.get(source, source)