from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import json
import math
import os
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, unquote_plus, urlencode, urlparse
from urllib.request import Request, urlopen

import numpy as np

from db import parse_json_field, query_all, query_one


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MODULE_RESULT_DIR = DATA_DIR / "module_results"
CLEAN_PATH = DATA_DIR / "clean" / "cleaned_with_standard_feature.csv"
RANKED_RECOMMEND_PATH = MODULE_RESULT_DIR / "07_recommendation" / "ranked_recommendations.csv"
CONTENT_RECOMMEND_PATH = MODULE_RESULT_DIR / "07_recommendation" / "content_recommendations.csv"
CF_RECOMMEND_PATH = MODULE_RESULT_DIR / "07_recommendation" / "cf_recommendations.csv"
PERSONALIZED_HYBRID_RECOMMEND_PATH = MODULE_RESULT_DIR / "07_recommendation" / "personalized_hybrid_recommendations.csv"
PERSONALIZED_HYBRID_REPORT_PATH = MODULE_RESULT_DIR / "07_recommendation" / "personalized_hybrid_report.json"
ALS_RECOMMEND_SEED_PATH = MODULE_RESULT_DIR / "07_recommendation" / "als_recommendations_seed.csv"
ALS_RECOMMEND_LIVE_PATH = MODULE_RESULT_DIR / "07_recommendation" / "als_recommendations_live.csv"
ALS_RECOMMEND_REPORT_PATH = MODULE_RESULT_DIR / "07_recommendation" / "als_recommendation_report.json"
GUIDE_KB_PATH = DATA_DIR / "guide" / "travel_guide_kb.json"
POI_GEO_PREVIEW_PATH = MODULE_RESULT_DIR / "08_poi_geo_preview" / "poi_geo_preview.csv"
SCENIC_NEWS_FALLBACK_PATH = DATA_DIR / "meta" / "scenic_news_fallback.json"
FLOW_SIMULATED_PATH = DATA_DIR / "predict" / "simulated_flow_2025_1M.csv"

RECOMMEND_ALGORITHMS = {
    "als": {
        "key": "als",
        "name": "ALS 协同过滤推荐",
        "short_name": "ALS 推荐",
        "principle": "参考你提供的 ALS 脚本，把收藏按 4 分、评论按真实评分汇总成 user_id / poi_id / rating 矩阵，再用交替最小二乘分解用户与景点隐向量，生成个性化推荐。",
    },
    "hybrid": {
        "key": "hybrid",
        "name": "个性化混合推荐",
        "short_name": "混合推荐",
        "principle": "参考混合推荐脚本，把地理邻近、内容相似和规则口碑三类分数按不同出行模式加权融合，生成可解释推荐。",
    },
}

RECOMMEND_MODES = [
    {
        "key": "balanced",
        "name": "均衡推荐",
        "description": "兼顾距离、兴趣相似、规则偏好、行为关联和景点品质。",
        "weights": {"geo": 0.28, "content": 0.24, "rule": 0.22, "behavior": 0.12, "quality": 0.14},
    },
    {
        "key": "near_first",
        "name": "近距离优先",
        "description": "更重视同城、近距离和路线衔接，适合短途串游。",
        "weights": {"geo": 0.42, "content": 0.20, "rule": 0.16, "behavior": 0.08, "quality": 0.14},
    },
    {
        "key": "interest_first",
        "name": "兴趣优先",
        "description": "更重视主题标签、景区类型和偏好规则，适合按兴趣扩展目的地。",
        "weights": {"geo": 0.18, "content": 0.36, "rule": 0.22, "behavior": 0.10, "quality": 0.14},
    },
    {
        "key": "reputation_first",
        "name": "口碑优先",
        "description": "更重视评分、热度、评论规模和景区等级，适合优先展示高确定性景点。",
        "weights": {"geo": 0.18, "content": 0.18, "rule": 0.28, "behavior": 0.08, "quality": 0.28},
    },
]

SCENIC_NEWS_FALLBACK = [
    {
        "title": "华东旅游进入暑期预订高峰，热门城市建议错峰出行",
        "link": "",
        "source": "系统内置公告",
        "published_at": "2026-06-30T09:00:00+08:00",
        "summary": "系统根据项目样本和近期文旅动态生成兜底公告，建议关注上海、杭州、苏州等热门城市的高峰时段。",
    },
    {
        "title": "景区客流预测模块已更新，可查看未来 7 天高峰预警",
        "link": "",
        "source": "系统内置公告",
        "published_at": "2026-06-29T18:00:00+08:00",
        "summary": "可在客流预测模块查看城市级与景点级客流趋势，并结合天气和节假日影响安排出行。",
    },
    {
        "title": "AI 旅游助手支持按城市、天数、预算生成行程方案",
        "link": "",
        "source": "系统内置公告",
        "published_at": "2026-06-29T12:00:00+08:00",
        "summary": "游客可在 AI 助手中输入目的地、预算和偏好，生成逐日路线、食宿、交通和费用建议。",
    },
    {
        "title": "省份 / 城市看板已同步最新景点数据，可查看区域热度与主题画像",
        "link": "",
        "source": "系统内置公告",
        "published_at": "2026-06-28T20:00:00+08:00",
        "summary": "当前看板支持按省份或城市聚合分析，展示景点分布、免费占比、主题结构和综合推荐景点。",
    },
]

EAST_CHINA_COORDS = {
    "上海市": [121.47, 31.23],
    "南京市": [118.78, 32.04],
    "苏州市": [120.58, 31.30],
    "无锡市": [120.31, 31.49],
    "常州市": [119.95, 31.78],
    "南通市": [120.86, 32.01],
    "扬州市": [119.42, 32.39],
    "镇江市": [119.45, 32.20],
    "泰州市": [119.92, 32.46],
    "徐州市": [117.18, 34.26],
    "盐城市": [120.16, 33.35],
    "连云港市": [119.22, 34.60],
    "淮安市": [119.02, 33.62],
    "宿迁市": [118.28, 33.96],
    "杭州市": [120.16, 30.25],
    "宁波市": [121.55, 29.87],
    "温州市": [120.70, 28.00],
    "嘉兴市": [120.75, 30.75],
    "湖州市": [120.09, 30.89],
    "绍兴市": [120.58, 30.01],
    "金华市": [119.65, 29.08],
    "衢州市": [118.87, 28.93],
    "舟山市": [122.21, 29.99],
    "台州市": [121.43, 28.66],
    "丽水市": [119.92, 28.45],
    "合肥市": [117.23, 31.82],
    "芜湖市": [118.38, 31.33],
    "蚌埠市": [117.39, 32.92],
    "淮南市": [117.00, 32.63],
    "马鞍山市": [118.51, 31.67],
    "淮北市": [116.80, 33.96],
    "铜陵市": [117.81, 30.95],
    "安庆市": [117.05, 30.53],
    "黄山市": [118.34, 29.72],
    "滁州市": [118.32, 32.30],
    "阜阳市": [115.82, 32.89],
    "宿州市": [116.98, 33.63],
    "六安市": [116.52, 31.74],
    "亳州市": [115.78, 33.85],
    "池州市": [117.49, 30.66],
    "宣城市": [118.76, 30.94],
    "福州市": [119.30, 26.08],
    "厦门市": [118.08, 24.48],
    "莆田市": [119.00, 25.45],
    "三明市": [117.64, 26.27],
    "泉州市": [118.67, 24.88],
    "漳州市": [117.65, 24.51],
    "南平市": [118.18, 26.64],
    "龙岩市": [117.02, 25.08],
    "宁德市": [119.55, 26.66],
    "南昌市": [115.86, 28.68],
    "景德镇市": [117.17, 29.27],
    "萍乡市": [113.85, 27.62],
    "九江市": [116.00, 29.70],
    "新余市": [114.93, 27.81],
    "鹰潭市": [117.07, 28.26],
    "赣州市": [114.94, 25.83],
    "吉安市": [114.99, 27.11],
    "宜春市": [114.39, 27.80],
    "抚州市": [116.36, 27.95],
    "上饶市": [117.97, 28.45],
    "济南市": [117.12, 36.65],
    "青岛市": [120.38, 36.07],
    "淄博市": [118.05, 36.81],
    "枣庄市": [117.32, 34.81],
    "东营市": [118.67, 37.43],
    "烟台市": [121.39, 37.54],
    "潍坊市": [119.16, 36.71],
    "济宁市": [116.59, 35.42],
    "泰安市": [117.09, 36.20],
    "威海市": [122.12, 37.51],
    "日照市": [119.52, 35.42],
    "临沂市": [118.35, 35.05],
    "德州市": [116.30, 37.45],
    "聊城市": [115.98, 36.45],
    "滨州市": [117.97, 37.38],
    "菏泽市": [115.48, 35.23],
}

THEME_RULES = {
    "自然风光": {
        "include": ["自然", "山", "湖", "海", "岛", "湿地", "森林", "公园", "植物园", "动物园", "海洋馆", "风景区", "瀑布", "峡谷", "溶洞", "古镇水乡"],
        "exclude": ["博物馆", "故居", "老街", "步行街", "商场", "广场", "美食街", "剧场"],
    },
    "历史人文": {
        "include": ["历史建筑", "博物馆", "展馆", "故居", "古镇", "古村", "寺", "庙", "祠", "遗址", "名人", "文化", "书院", "牌坊"],
        "exclude": ["动物园", "海洋馆", "乐园", "水上乐园", "游乐", "商场"],
    },
    "亲子休闲": {
        "include": ["亲子", "遛娃", "动物园", "海洋馆", "乐园", "游乐", "公园", "植物园", "科技馆", "水族馆", "水上乐园", "温泉"],
        "exclude": ["酒吧", "夜店", "剧场", "陵园"],
    },
    "美食打卡": {
        "include": ["美食", "小吃", "老街", "步行街", "夜市", "夜游", "商圈", "城隍庙", "美食街", "外滩", "街区"],
        "exclude": ["陵园", "纪念馆", "地质公园"],
    },
    "城市漫游": {
        "include": ["步行街", "老街", "街区", "外滩", "广场", "地标", "夜游", "观景", "商圈", "城市", "陆家嘴", "城墙"],
        "exclude": ["动物园", "海洋馆", "漂流", "滑雪场"],
    },
    "小众深度": {
        "include": ["古村", "古镇", "秘境", "遗址", "书院", "博物馆", "展馆", "湿地", "地质", "非遗", "艺术", "纪念馆", "文化"],
        "exclude": ["迪士尼", "乐园", "步行街", "商圈"],
    },
}

PREFERENCE_RULES = {
    "高性价比": ["免费", "公园", "步行街", "博物馆", "老街"],
    "热门打卡": ["热门", "地标", "外滩", "乐园", "夜游", "观景"],
    "深度体验": ["古镇", "博物馆", "展馆", "文化", "书院", "遗址", "非遗"],
    "亲子友好": ["亲子", "遛娃", "动物园", "海洋馆", "乐园", "公园"],
    "摄影观景": ["观景", "外滩", "日落", "夜游", "花海", "山顶", "湖景"],
    "特种兵": ["地标", "热门", "博物馆", "步行街", "夜游", "商圈"],
}

CITY_FOOD_GUIDE = {
    "上海市": {
        "breakfast": ["生煎", "葱油拌面"],
        "lunch": ["本帮菜", "小笼包"],
        "dinner": ["城隍庙小吃", "本帮菜馆"],
    },
    "杭州市": {
        "breakfast": ["片儿川", "定胜糕"],
        "lunch": ["龙井虾仁", "杭帮菜"],
        "dinner": ["西湖醋鱼", "河坊街小吃"],
    },
    "苏州市": {
        "breakfast": ["苏式汤面", "海棠糕"],
        "lunch": ["苏帮菜", "松鼠鳜鱼"],
        "dinner": ["平江路小吃", "苏式点心"],
    },
    "南京市": {
        "breakfast": ["鸭血粉丝", "盐水鸭小食"],
        "lunch": ["金陵菜", "锅贴"],
        "dinner": ["夫子庙小吃", "金陵夜宵"],
    },
    "厦门市": {
        "breakfast": ["沙茶面", "花生汤"],
        "lunch": ["闽南海鲜", "土笋冻"],
        "dinner": ["中山路小吃", "海鲜排档"],
    },
    "青岛市": {
        "breakfast": ["海鲜馄饨", "甜沫"],
        "lunch": ["海鲜家常菜", "鲅鱼水饺"],
        "dinner": ["啤酒海鲜", "台东夜市小吃"],
    },
    "福州市": {
        "breakfast": ["鱼丸", "锅边糊"],
        "lunch": ["佛跳墙风味餐", "荔枝肉"],
        "dinner": ["三坊七巷小吃", "闽菜馆"],
    },
}

CITY_AREA_GUIDE = {
    "上海市": [
        {
            "keywords": ["豫园", "城隍庙"],
            "zone": "豫园商城 / 城隍庙老城厢",
            "breakfast": ["南翔风味小笼早餐", "宁波汤团配生煎"],
            "lunch": ["老城厢本帮菜午餐", "豫园园林茶点套餐"],
            "dinner": ["城隍庙夜游小吃线", "老饭店本帮菜晚餐"],
            "hotel_low": "豫园老城厢便捷酒店",
            "hotel_mid": "豫园城隍庙精品酒店",
            "hotel_high": "外滩老城厢景观酒店",
            "hotel_area": "豫园-外滩步行圈",
        },
        {
            "keywords": ["外滩", "南京路", "人民广场"],
            "zone": "南京路步行街 / 外滩滨江线",
            "breakfast": ["南京路老字号早餐", "外滩生煎配咖啡"],
            "lunch": ["外滩源本帮菜午餐", "南京路老字号简餐"],
            "dinner": ["外滩夜景观景晚餐", "南京路夜间小吃收尾"],
            "hotel_low": "南京路商圈便捷酒店",
            "hotel_mid": "外滩步行街舒适酒店",
            "hotel_high": "外滩江景品质酒店",
            "hotel_area": "外滩-南京路商圈",
        },
        {
            "keywords": ["陆家嘴", "东方明珠", "海洋水族馆"],
            "zone": "陆家嘴滨江 / 正大广场一带",
            "breakfast": ["陆家嘴轻食早餐", "滨江咖啡配面包早午餐"],
            "lunch": ["陆家嘴商圈本帮菜", "正大广场简餐"],
            "dinner": ["滨江夜景餐厅晚餐", "陆家嘴商圈收尾晚餐"],
            "hotel_low": "陆家嘴商务便捷酒店",
            "hotel_mid": "陆家嘴滨江舒适酒店",
            "hotel_high": "陆家嘴高层观景酒店",
            "hotel_area": "陆家嘴金融城",
        },
        {
            "keywords": ["迪士尼", "川沙"],
            "zone": "迪士尼小镇 / 川沙古镇",
            "breakfast": ["川沙传统早点", "乐园出发轻便早餐"],
            "lunch": ["迪士尼小镇主题午餐", "川沙本帮简餐"],
            "dinner": ["迪士尼小镇夜间简餐", "川沙古镇收尾晚餐"],
            "hotel_low": "川沙乐园便捷酒店",
            "hotel_mid": "迪士尼度假区舒适酒店",
            "hotel_high": "迪士尼度假品质酒店",
            "hotel_area": "迪士尼度假区 / 川沙",
        },
        {
            "keywords": ["南汇", "野生动物园", "惠南"],
            "zone": "惠南镇 / 野生动物园周边",
            "breakfast": ["惠南古镇早点", "动物园周边亲子早餐"],
            "lunch": ["野生动物园亲子套餐", "惠南本帮面馆"],
            "dinner": ["惠南镇家常菜晚餐", "动物园周边轻松晚餐"],
            "hotel_low": "惠南镇便捷酒店",
            "hotel_mid": "野生动物园舒适酒店",
            "hotel_high": "浦东郊野度假酒店",
            "hotel_area": "惠南 / 野生动物园",
        },
        {
            "keywords": ["滴水湖", "临港", "天文馆"],
            "zone": "滴水湖湖畔 / 临港新片区",
            "breakfast": ["临港湖畔早餐", "滴水湖轻食早午餐"],
            "lunch": ["天文馆周边简餐", "临港海鲜面午餐"],
            "dinner": ["滴水湖湖景晚餐", "临港商圈收尾晚餐"],
            "hotel_low": "临港湖畔便捷酒店",
            "hotel_mid": "滴水湖景舒适酒店",
            "hotel_high": "临港湖景品质酒店",
            "hotel_area": "滴水湖临港片区",
        },
        {
            "keywords": ["静安寺", "南京西路"],
            "zone": "静安寺 / 南京西路商圈",
            "breakfast": ["静安寺早午餐", "老字号面点早餐"],
            "lunch": ["南京西路本帮菜午餐", "静安商圈轻商务简餐"],
            "dinner": ["吴江路夜间小吃", "静安寺商圈晚餐"],
            "hotel_low": "静安寺便捷酒店",
            "hotel_mid": "南京西路舒适酒店",
            "hotel_high": "静安寺品质酒店",
            "hotel_area": "静安寺核心商圈",
        },
        {
            "keywords": ["世博", "新国际博览中心"],
            "zone": "世博园 / 新国际博览中心",
            "breakfast": ["世博园区轻食早餐", "会展商圈咖啡早餐"],
            "lunch": ["世博园简餐", "浦东会展商圈午餐"],
            "dinner": ["世博滨江晚餐", "浦东会展区收尾晚餐"],
            "hotel_low": "世博园便捷酒店",
            "hotel_mid": "世博园舒适酒店",
            "hotel_high": "浦东会展品质酒店",
            "hotel_area": "世博会展片区",
        },
        {
            "keywords": ["广富林", "松江", "佘山"],
            "zone": "广富林 / 松江大学城 / 佘山",
            "breakfast": ["松江糕团早餐", "大学城简约早餐"],
            "lunch": ["广富林文旅午餐", "松江本帮菜"],
            "dinner": ["泰晤士小镇晚餐", "松江城区收尾晚餐"],
            "hotel_low": "松江大学城便捷酒店",
            "hotel_mid": "广富林舒适酒店",
            "hotel_high": "佘山度假品质酒店",
            "hotel_area": "松江文旅片区",
        },
    ]
}

OFFICIAL_PROVINCE_CITIES = {
    "上海市": {"上海市"},
    "江苏省": {"南京市", "无锡市", "徐州市", "常州市", "苏州市", "南通市", "连云港市", "淮安市", "盐城市", "扬州市", "镇江市", "泰州市", "宿迁市"},
    "浙江省": {"杭州市", "宁波市", "温州市", "嘉兴市", "湖州市", "绍兴市", "金华市", "衢州市", "舟山市", "台州市", "丽水市"},
    "安徽省": {"合肥市", "芜湖市", "蚌埠市", "淮南市", "马鞍山市", "淮北市", "铜陵市", "安庆市", "黄山市", "滁州市", "阜阳市", "宿州市", "六安市", "亳州市", "池州市", "宣城市"},
    "福建省": {"福州市", "厦门市", "莆田市", "三明市", "泉州市", "漳州市", "南平市", "龙岩市", "宁德市"},
    "江西省": {"南昌市", "景德镇市", "萍乡市", "九江市", "新余市", "鹰潭市", "赣州市", "吉安市", "宜春市", "抚州市", "上饶市"},
    "山东省": {"济南市", "青岛市", "淄博市", "枣庄市", "东营市", "烟台市", "潍坊市", "济宁市", "泰安市", "威海市", "日照市", "临沂市", "德州市", "聊城市", "滨州市", "菏泽市"},
}

CITY_ALIAS = {
    "天台县": "台州市",
    "太湖县": "安庆市",
    "平潭县": "福州市",
    "东山县": "漳州市",
    "南靖县": "漳州市",
}

CITY_TO_PROVINCE = {
    city: province
    for province, cities in OFFICIAL_PROVINCE_CITIES.items()
    for city in cities
}


def build_response(success: bool, data: Any, message: str = "") -> Dict[str, Any]:
    return {"success": success, "message": message, "data": data}


def db_available() -> bool:
    try:
        row = query_one("SELECT 1 AS ok")
        return bool(row and row.get("ok") == 1)
    except Exception:
        return False


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def safe_int(value: Any) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def normalize_city_province(city_name: Any, province: Any = "") -> Tuple[str, str]:
    city = CITY_ALIAS.get(normalize_text(city_name), normalize_text(city_name))
    prov = CITY_TO_PROVINCE.get(city, normalize_text(province))
    if prov and city in OFFICIAL_PROVINCE_CITIES.get(prov, set()):
        return city, prov
    return "", ""


def normalize_city_summary_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        city, province = normalize_city_province(row.get("city_name"), row.get("province"))
        if not city or not province:
            continue
        key = (province, city)
        item = grouped.setdefault(
            key,
            {
                "province": province,
                "city_name": city,
                "poi_count": 0,
                "comment_total": 0,
                "free_poi_count": 0,
                "high_score_poi_count": 0,
                "five_a_poi_count": 0,
                "weighted_price": 0.0,
                "weighted_score": 0.0,
                "weighted_heat": 0.0,
            },
        )
        poi_count = safe_int(row.get("poi_count"))
        item["poi_count"] += poi_count
        item["comment_total"] += safe_int(row.get("comment_total"))
        item["free_poi_count"] += safe_int(row.get("free_poi_count"))
        item["high_score_poi_count"] += safe_int(row.get("high_score_poi_count"))
        item["five_a_poi_count"] += safe_int(row.get("five_a_poi_count"))
        item["weighted_price"] += safe_float(row.get("avg_price")) * poi_count
        item["weighted_score"] += safe_float(row.get("avg_score")) * poi_count
        item["weighted_heat"] += safe_float(row.get("avg_heat")) * poi_count
    result = []
    for item in grouped.values():
        poi_count = max(safe_int(item["poi_count"]), 1)
        result.append(
            {
                "province": item["province"],
                "city_name": item["city_name"],
                "poi_count": item["poi_count"],
                "avg_price": round(item["weighted_price"] / poi_count, 2),
                "avg_score": round(item["weighted_score"] / poi_count, 2),
                "avg_heat": round(item["weighted_heat"] / poi_count, 2),
                "free_poi_count": item["free_poi_count"],
                "free_ratio": round(item["free_poi_count"] / poi_count, 4),
                "high_score_poi_count": item["high_score_poi_count"],
                "high_score_ratio": round(item["high_score_poi_count"] / poi_count, 4),
                "five_a_poi_count": item["five_a_poi_count"],
                "comment_total": item["comment_total"],
            }
        )
    return sorted(result, key=lambda row: (safe_int(row.get("poi_count")), safe_int(row.get("comment_total"))), reverse=True)


def normalize_tag_summary_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        city, province = normalize_city_province(row.get("city_name"), row.get("province"))
        if not city:
            continue
        tag_name = normalize_text(row.get("tag_name"))
        if not tag_name:
            continue
        key = (city, tag_name)
        item = grouped.setdefault(key, {"province": province, "city_name": city, "tag_name": tag_name, "poi_count": 0})
        item["poi_count"] += safe_int(row.get("poi_count"))
    return sorted(grouped.values(), key=lambda row: (safe_int(row.get("poi_count")), row.get("city_name", "")), reverse=True)


def password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def fetch_json_payload(table_name: str) -> Any:
    row = query_one(f"SELECT payload_json FROM `{table_name}` LIMIT 1")
    if not row:
        return None
    return parse_json_field(row.get("payload_json"))


def fetch_table_rows(
    table_name: str,
    limit: int | None = None,
    order_by: str | None = None,
    where_sql: str | None = None,
    params: Tuple[Any, ...] = (),
) -> List[Dict[str, Any]]:
    sql = f"SELECT * FROM `{table_name}`"
    if where_sql:
        sql += f" WHERE {where_sql}"
    if order_by:
        sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return query_all(sql, params)


def fetch_table_rows_safe(
    table_name: str,
    limit: int | None = None,
    order_by: str | None = None,
    where_sql: str | None = None,
    params: Tuple[Any, ...] = (),
) -> List[Dict[str, Any]]:
    try:
        return fetch_table_rows(table_name, limit=limit, order_by=order_by, where_sql=where_sql, params=params)
    except Exception:
        return []


@lru_cache(maxsize=1)
def load_clean_poi_lookup() -> Dict[str, Any]:
    by_id: Dict[str, Dict[str, Any]] = {}
    by_name_city: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not CLEAN_PATH.exists():
        return {"by_id": by_id, "by_name_city": by_name_city}

    with CLEAN_PATH.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            poi_id = normalize_text(row.get("poiId"))
            poi_name = normalize_text(row.get("poiName"))
            city_name = normalize_text(row.get("cityName"))
            record = {
                "poi_id": safe_int(row.get("poiId")),
                "poi_name": poi_name,
                "province": normalize_text(row.get("province")),
                "city_name": city_name,
                "region_name": normalize_text(row.get("regionName")),
                "price": safe_float(row.get("priceFloat")),
                "comment_score": safe_float(row.get("commentScoreFloat")),
                "comment_count": safe_int(row.get("commentCountInt")),
                "heat_score": safe_float(row.get("heatScoreFloat")),
                "distance_level": normalize_text(row.get("distance_level")),
                "is_free": normalize_text(row.get("isFree")),
                "is_kid": normalize_text(row.get("is_kid")),
                "is_night_tour": normalize_text(row.get("is_night_tour")),
                "price_level": normalize_text(row.get("price_level")),
                "heat_level": normalize_text(row.get("heat_level")),
                "score_level": normalize_text(row.get("score_level")),
                "tag_text": normalize_text(row.get("tagNames")).replace("[", "").replace("]", "").replace("'", ""),
                "short_feature": normalize_text(row.get("shortFeatureText")),
                "sight_level": normalize_text(row.get("sightLevelStr")),
                "cover_image_url": normalize_text(row.get("coverImageUrl")),
                "detail_url": normalize_text(row.get("detailUrl")),
                "latitude": safe_float(row.get("latitude")),
                "longitude": safe_float(row.get("longitude")),
            }
            if poi_id and poi_id not in by_id:
                by_id[poi_id] = record
            if poi_name and city_name and (poi_name, city_name) not in by_name_city:
                by_name_city[(poi_name, city_name)] = record
    return {"by_id": by_id, "by_name_city": by_name_city}


@lru_cache(maxsize=1)
def load_clean_poi_records() -> List[Dict[str, Any]]:
    lookup = load_clean_poi_lookup()
    return list(lookup["by_id"].values())


@lru_cache(maxsize=1)
def load_poi_geo_preview_lookup() -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    if not POI_GEO_PREVIEW_PATH.exists():
        return rows
    with POI_GEO_PREVIEW_PATH.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            poi_id = normalize_text(row.get("poi_id"))
            if not poi_id:
                continue
            rows[poi_id] = {
                "poi_id": poi_id,
                "poi_name": normalize_text(row.get("poi_name")),
                "province": normalize_text(row.get("province")),
                "city_name": normalize_text(row.get("city_name")),
                "region_name": normalize_text(row.get("region_name")),
                "latitude": safe_float(row.get("latitude")),
                "longitude": safe_float(row.get("longitude")),
                "tag_text": normalize_text(row.get("tag_text")),
                "preview_mode": normalize_text(row.get("preview_mode")) or "map_heat_fallback",
                "preview_title": normalize_text(row.get("preview_title")),
                "preview_image_url": normalize_text(row.get("preview_image_url")),
                "cover_image_url": normalize_text(row.get("cover_image_url")),
                "detail_url": normalize_text(row.get("detail_url")),
            }
    return rows


def build_poi_preview_payload(query: Dict[str, List[str]]) -> Dict[str, Any]:
    poi_id = normalize_text(query.get("poi_id", [""])[0])
    poi_name = normalize_text(query.get("poi_name", [""])[0])
    city_name = normalize_text(query.get("city_name", [""])[0])
    preview_lookup = load_poi_geo_preview_lookup()

    preview_row: Optional[Dict[str, Any]] = None
    if poi_id:
        preview_row = preview_lookup.get(poi_id)

    base_row: Optional[Dict[str, Any]] = None
    clean_lookup = load_clean_poi_lookup()
    if poi_id and poi_id in clean_lookup["by_id"]:
        base_row = clean_lookup["by_id"][poi_id]
    elif poi_name and city_name:
        base_row = clean_lookup["by_name_city"].get((poi_name, city_name))

    if not preview_row and base_row:
        preview_row = {
            "poi_id": normalize_text(base_row.get("poi_id")),
            "poi_name": normalize_text(base_row.get("poi_name")),
            "province": normalize_text(base_row.get("province")),
            "city_name": normalize_text(base_row.get("city_name")),
            "region_name": normalize_text(base_row.get("region_name")),
            "latitude": safe_float(base_row.get("latitude")),
            "longitude": safe_float(base_row.get("longitude")),
            "tag_text": normalize_text(base_row.get("tag_text")),
            "preview_mode": "map_heat_fallback",
            "preview_title": f"{normalize_text(base_row.get('poi_name'))} 空间预览",
            "preview_image_url": "",
            "cover_image_url": normalize_text(base_row.get("cover_image_url")),
            "detail_url": normalize_text(base_row.get("detail_url")),
        }

    if not preview_row:
        raise ValueError("未找到对应景点的空间预览数据")

    lat = safe_float(preview_row.get("latitude"))
    lon = safe_float(preview_row.get("longitude"))
    return {
        **preview_row,
        "latitude": lat,
        "longitude": lon,
        "has_coordinate": bool(lat and lon),
        "has_preview_image": bool(normalize_text(preview_row.get("preview_image_url"))),
    }


def enrich_poi_row(row: Dict[str, Any]) -> Dict[str, Any]:
    lookup = load_clean_poi_lookup()
    poi_id = normalize_text(row.get("poi_id") or row.get("target_poi_id") or row.get("source_poi_id"))
    poi_name = normalize_text(row.get("poi_name") or row.get("target_poi_name") or row.get("source_poi_name"))
    city_name = normalize_text(row.get("city_name") or row.get("target_city_name") or row.get("source_city_name"))
    clean_row = None
    if poi_id and poi_id in lookup["by_id"]:
        clean_row = lookup["by_id"][poi_id]
    elif poi_name and city_name:
        clean_row = lookup["by_name_city"].get((poi_name, city_name))

    merged = dict(row)
    if clean_row:
        for key, value in clean_row.items():
            if not merged.get(key):
                merged[key] = value
        for key in ("price", "comment_score", "comment_count", "heat_score", "distance_level", "is_free", "is_kid", "is_night_tour", "price_level", "heat_level", "score_level", "tag_text", "short_feature", "sight_level", "cover_image_url", "detail_url", "latitude", "longitude"):
            if clean_row.get(key) not in (None, "", 0):
                merged[key] = clean_row[key]
    city, province = normalize_city_province(merged.get("city_name"), merged.get("province"))
    if city and province:
        merged["city_name"] = city
        merged["province"] = province
    return merged


@lru_cache(maxsize=1)
def load_ranked_recommendations() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not RANKED_RECOMMEND_PATH.exists():
        return rows
    with RANKED_RECOMMEND_PATH.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            row["recommend_rank"] = safe_int(row.get("recommend_rank"))
            row["final_score"] = safe_float(row.get("final_score"))
            rows.append(row)
    return rows


@lru_cache(maxsize=1)
def load_content_recommendations() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not CONTENT_RECOMMEND_PATH.exists():
        return rows
    with CONTENT_RECOMMEND_PATH.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            row["recommend_rank"] = safe_int(row.get("recommend_rank"))
            row["recommend_score"] = safe_float(row.get("recommend_score"))
            rows.append(row)
    return rows


@lru_cache(maxsize=1)
def load_cf_recommendations() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not CF_RECOMMEND_PATH.exists():
        return rows
    with CF_RECOMMEND_PATH.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            row["recommend_rank"] = safe_int(row.get("recommend_rank"))
            row["recommend_score"] = safe_float(row.get("recommend_score"))
            rows.append(row)
    return rows


@lru_cache(maxsize=1)
def load_recommend_lookup() -> Dict[str, Any]:
    provinces: List[str] = []
    cities_by_province: Dict[str, List[Dict[str, Any]]] = {}
    pois_by_city: Dict[str, List[Dict[str, Any]]] = {}

    if not CLEAN_PATH.exists():
        return {
            "provinces": provinces,
            "cities_by_province": cities_by_province,
            "pois_by_city": pois_by_city,
        }

    rows: List[Dict[str, Any]] = []
    with CLEAN_PATH.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            province = normalize_text(row.get("province"))
            city = normalize_text(row.get("cityName"))
            poi_name = normalize_text(row.get("poiName"))
            if not province or not city or not poi_name:
                continue
            record = {
                "poi_id": safe_int(row.get("poiId")),
                "poi_name": poi_name,
                "province": province,
                "city_name": city,
                "region_name": normalize_text(row.get("regionName")),
                "tag_text": normalize_text(row.get("tagNames")).replace("[", "").replace("]", "").replace("'", ""),
                "short_feature": normalize_text(row.get("shortFeatureText")),
                "distance_level": normalize_text(row.get("distance_level")),
            }
            rows.append(record)

    province_seen = set()
    city_seen: Dict[str, set[str]] = {}
    for row in rows:
        province = row["province"]
        city = row["city_name"]
        if province not in province_seen:
            provinces.append(province)
            province_seen.add(province)
        cities_by_province.setdefault(province, [])
        if city not in city_seen.setdefault(province, set()):
            cities_by_province[province].append({"city_name": city, "province": province})
            city_seen[province].add(city)
        pois_by_city.setdefault(f"{province}||{city}", []).append(row)

    for province, city_rows in cities_by_province.items():
        city_rows.sort(key=lambda item: item["city_name"])
    for key, poi_rows in pois_by_city.items():
        poi_rows.sort(key=lambda item: item["poi_name"])

    return {
        "provinces": provinces,
        "cities_by_province": cities_by_province,
        "pois_by_city": pois_by_city,
    }


@lru_cache(maxsize=1)
def load_personalized_hybrid_recommendations() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not PERSONALIZED_HYBRID_RECOMMEND_PATH.exists():
        return rows
    with PERSONALIZED_HYBRID_RECOMMEND_PATH.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            row["recommend_rank"] = safe_int(row.get("recommend_rank"))
            for key in ("content_score", "geo_score", "rule_score", "behavior_score", "quality_score", "final_score", "distance_km"):
                row[key] = safe_float(row.get(key))
            row["target_comment_count"] = safe_int(row.get("target_comment_count"))
            rows.append(row)
    return rows


@lru_cache(maxsize=1)
def load_personalized_hybrid_report() -> Dict[str, Any]:
    if not PERSONALIZED_HYBRID_REPORT_PATH.exists():
        return {}
    try:
        return json.loads(PERSONALIZED_HYBRID_REPORT_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def recommendation_modes() -> List[Dict[str, Any]]:
    report = load_personalized_hybrid_report()
    modes = report.get("modes")
    if isinstance(modes, list) and modes:
        return modes
    return RECOMMEND_MODES


@lru_cache(maxsize=1)
def load_als_seed_recommendations() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not ALS_RECOMMEND_SEED_PATH.exists():
        return rows
    with ALS_RECOMMEND_SEED_PATH.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            rows.append(
                {
                    "user_id": safe_int(row.get("user_id")),
                    "recommend_rank": safe_int(row.get("rank") or row.get("recommend_rank")),
                    "poi_id": safe_int(row.get("poi_id")),
                    "score": safe_float(row.get("score") or row.get("rating")),
                    "source": "seed_csv",
                }
            )
    return rows


def current_als_training_signature() -> str:
    try:
        favorite_meta = query_one(
            """
            SELECT COUNT(*) AS row_count, UNIX_TIMESTAMP(MAX(created_at)) AS latest_ts
            FROM user_favorites
            """
        ) or {}
        comment_meta = query_one(
            """
            SELECT COUNT(*) AS row_count, UNIX_TIMESTAMP(MAX(created_at)) AS latest_ts
            FROM user_poi_comments
            """
        ) or {}
        return "|".join(
            [
                str(safe_int(favorite_meta.get("row_count"))),
                str(safe_int(favorite_meta.get("latest_ts"))),
                str(safe_int(comment_meta.get("row_count"))),
                str(safe_int(comment_meta.get("latest_ts"))),
            ]
        )
    except Exception:
        return "db-unavailable"


def load_als_rating_rows() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    aggregated: Dict[Tuple[int, int], float] = {}
    meta: Dict[str, Any] = {"favorite_events": 0, "comment_events": 0}
    try:
        favorite_rows = query_all("SELECT user_id, poi_id FROM user_favorites")
        comment_rows = query_all("SELECT user_id, poi_id, rating FROM user_poi_comments")
    except Exception as exc:
        return [], {"status": "db_unavailable", "message": str(exc)}

    for row in favorite_rows:
        user_id = safe_int(row.get("user_id"))
        poi_id = safe_int(row.get("poi_id"))
        if user_id <= 0 or poi_id <= 0:
            continue
        aggregated[(user_id, poi_id)] = max(aggregated.get((user_id, poi_id), 0.0), 4.0)
        meta["favorite_events"] += 1

    for row in comment_rows:
        user_id = safe_int(row.get("user_id"))
        poi_id = safe_int(row.get("poi_id"))
        rating = safe_float(row.get("rating")) or 4.0
        if user_id <= 0 or poi_id <= 0:
            continue
        aggregated[(user_id, poi_id)] = max(aggregated.get((user_id, poi_id), 0.0), rating)
        meta["comment_events"] += 1

    rows = [
        {"user_id": user_id, "poi_id": poi_id, "rating": round(float(rating), 6)}
        for (user_id, poi_id), rating in aggregated.items()
    ]
    rows.sort(key=lambda item: (item["user_id"], item["poi_id"]))
    meta["status"] = "ok" if rows else "empty"
    meta["rating_rows"] = len(rows)
    meta["user_count"] = len({row["user_id"] for row in rows})
    meta["poi_count"] = len({row["poi_id"] for row in rows})
    return rows, meta


def solve_als_linear(system_matrix: np.ndarray, rhs: np.ndarray) -> np.ndarray:
    try:
        return np.linalg.solve(system_matrix, rhs)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(system_matrix, rhs, rcond=None)[0]


@lru_cache(maxsize=8)
def build_als_training_artifact(signature: str) -> Dict[str, Any]:
    rating_rows, meta = load_als_rating_rows()
    result_dir = ALS_RECOMMEND_LIVE_PATH.parent
    result_dir.mkdir(parents=True, exist_ok=True)

    if not rating_rows:
        report = {
            "model_name": "ALS 协同过滤推荐",
            "status": meta.get("status", "empty"),
            "signature": signature,
            "message": meta.get("message", "当前没有可训练的收藏/评论评分数据。"),
            "meta": meta,
        }
        ALS_RECOMMEND_REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "empty", "report": report, "rows": [], "seed_rows": load_als_seed_recommendations()}

    user_ids = sorted({safe_int(row["user_id"]) for row in rating_rows})
    poi_ids = sorted({safe_int(row["poi_id"]) for row in rating_rows})
    if len(user_ids) < 2 or len(poi_ids) < 2:
        report = {
            "model_name": "ALS 协同过滤推荐",
            "status": "insufficient",
            "signature": signature,
            "message": "用户或景点交互维度不足，暂时无法训练 ALS 模型。",
            "meta": meta,
        }
        ALS_RECOMMEND_REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "insufficient", "report": report, "rows": [], "seed_rows": load_als_seed_recommendations()}

    factor_dim = max(4, min(16, min(len(user_ids), len(poi_ids))))
    regularization = 0.12
    iterations = 12

    user_index = {user_id: idx for idx, user_id in enumerate(user_ids)}
    poi_index = {poi_id: idx for idx, poi_id in enumerate(poi_ids)}
    user_items: List[List[Tuple[int, float]]] = [[] for _ in user_ids]
    poi_users: List[List[Tuple[int, float]]] = [[] for _ in poi_ids]
    seen_by_user: Dict[int, set[int]] = {user_id: set() for user_id in user_ids}

    for row in rating_rows:
        user_id = safe_int(row["user_id"])
        poi_id = safe_int(row["poi_id"])
        rating = safe_float(row["rating"])
        uidx = user_index[user_id]
        pidx = poi_index[poi_id]
        user_items[uidx].append((pidx, rating))
        poi_users[pidx].append((uidx, rating))
        seen_by_user[user_id].add(poi_id)

    rng = np.random.default_rng(42)
    user_factors = rng.normal(0.0, 0.12, size=(len(user_ids), factor_dim))
    poi_factors = rng.normal(0.0, 0.12, size=(len(poi_ids), factor_dim))
    identity = np.eye(factor_dim)

    for _ in range(iterations):
        for uidx, ratings in enumerate(user_items):
            if not ratings:
                continue
            item_indices = [item_idx for item_idx, _ in ratings]
            values = np.array([value for _, value in ratings], dtype=float)
            item_matrix = poi_factors[item_indices]
            system = item_matrix.T @ item_matrix + regularization * len(item_indices) * identity
            rhs = item_matrix.T @ values
            user_factors[uidx] = solve_als_linear(system, rhs)
        for pidx, ratings in enumerate(poi_users):
            if not ratings:
                continue
            user_indices = [user_idx for user_idx, _ in ratings]
            values = np.array([value for _, value in ratings], dtype=float)
            user_matrix = user_factors[user_indices]
            system = user_matrix.T @ user_matrix + regularization * len(user_indices) * identity
            rhs = user_matrix.T @ values
            poi_factors[pidx] = solve_als_linear(system, rhs)

    squared_error = 0.0
    for row in rating_rows:
        user_id = safe_int(row["user_id"])
        poi_id = safe_int(row["poi_id"])
        rating = safe_float(row["rating"])
        pred = float(np.dot(user_factors[user_index[user_id]], poi_factors[poi_index[poi_id]]))
        squared_error += (pred - rating) ** 2
    rmse = math.sqrt(squared_error / max(len(rating_rows), 1))

    generated_rows: List[Dict[str, Any]] = []
    user_scores = user_factors @ poi_factors.T
    poi_id_array = np.array(poi_ids, dtype=int)
    for user_id in user_ids:
        uidx = user_index[user_id]
        scores = user_scores[uidx]
        seen_items = seen_by_user.get(user_id, set())
        ranked_indices = np.argsort(scores)[::-1]
        rank = 1
        for pidx in ranked_indices:
            poi_id = int(poi_id_array[pidx])
            if poi_id in seen_items:
                continue
            generated_rows.append(
                {
                    "user_id": int(user_id),
                    "recommend_rank": rank,
                    "poi_id": poi_id,
                    "score": round(float(scores[pidx]), 6),
                    "source": "live_als",
                }
            )
            rank += 1
            if rank > 60:
                break

    with ALS_RECOMMEND_LIVE_PATH.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["user_id", "recommend_rank", "poi_id", "score", "source"])
        writer.writeheader()
        writer.writerows(generated_rows)

    report = {
        "model_name": "ALS 协同过滤推荐",
        "status": "ok",
        "signature": signature,
        "factor_dim": factor_dim,
        "regularization": regularization,
        "iterations": iterations,
        "rmse": round(rmse, 6),
        "user_count": len(user_ids),
        "poi_count": len(poi_ids),
        "rating_row_count": len(rating_rows),
        "output_row_count": len(generated_rows),
        "note": "收藏按 4 分、评论按真实评分聚合，同一 user_id + poi_id 取最大 rating，再用显式反馈 ALS 训练。",
        "meta": meta,
    }
    ALS_RECOMMEND_REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "ok",
        "report": report,
        "rows": generated_rows,
        "user_index": user_index,
        "poi_ids": poi_ids,
        "poi_factors": poi_factors,
        "user_factors": user_factors,
        "seen_by_user": seen_by_user,
        "seed_rows": load_als_seed_recommendations(),
    }


def current_als_training_artifact() -> Dict[str, Any]:
    return build_als_training_artifact(current_als_training_signature())


def score_als_candidates_for_user(user_id: int) -> Dict[str, Any]:
    artifact = current_als_training_artifact()
    if artifact.get("status") == "ok" and user_id in artifact.get("user_index", {}):
        uidx = artifact["user_index"][user_id]
        scores = artifact["poi_factors"] @ artifact["user_factors"][uidx]
        seen = artifact.get("seen_by_user", {}).get(user_id, set())
        rows = []
        for poi_id, score in zip(artifact.get("poi_ids", []), scores):
            if poi_id in seen:
                continue
            rows.append({"user_id": user_id, "poi_id": int(poi_id), "score": round(float(score), 6), "source": "live_als"})
        rows.sort(key=lambda item: item["score"], reverse=True)
        return {
            "status": "ok",
            "source": "live_als",
            "rows": rows,
            "history_count": len(seen),
            "report": artifact.get("report", {}),
        }

    seed_rows = [row for row in artifact.get("seed_rows", []) if safe_int(row.get("user_id")) == user_id]
    if seed_rows:
        seed_rows.sort(key=lambda item: (safe_int(item.get("recommend_rank")), -safe_float(item.get("score"))))
        return {
            "status": "ok",
            "source": "seed_csv",
            "rows": seed_rows,
            "history_count": 0,
            "report": artifact.get("report", {}),
        }

    return {
        "status": artifact.get("status", "cold_start"),
        "source": "fallback",
        "rows": [],
        "history_count": 0,
        "report": artifact.get("report", {}),
    }


def build_als_default_recommendations(limit: int) -> List[Dict[str, Any]]:
    artifact = current_als_training_artifact()
    rows = artifact.get("rows") or artifact.get("seed_rows") or []
    picked: List[Dict[str, Any]] = []
    seen = set()
    for row in sorted(rows, key=lambda item: (-safe_float(item.get("score")), safe_int(item.get("recommend_rank")))):
        poi_id = safe_int(row.get("poi_id"))
        if poi_id <= 0 or poi_id in seen:
            continue
        seen.add(poi_id)
        picked.append(
            enrich_recommendation_row(
                {
                    "algorithm": "als",
                    "mode": "balanced",
                    "mode_name": "均衡推荐",
                    "recommend_rank": len(picked) + 1,
                    "target_poi_id": poi_id,
                    "target_poi_name": "",
                    "target_city_name": "",
                    "target_region_name": "",
                    "recommend_score": safe_float(row.get("score")),
                    "final_score": clamp(safe_float(row.get("score")) / 5.0, 0.0, 1.0),
                    "behavior_score": clamp(safe_float(row.get("score")) / 5.0, 0.0, 1.0),
                    "reason_text": "ALS 协同过滤预热推荐；优先展示相似用户群体中经常被推荐的景点。",
                }
            )
        )
        if len(picked) >= limit:
            break
    return picked


def build_als_personalized_recommendations(
    user_id: int,
    source_row: Optional[Dict[str, Any]],
    province: str,
    city: str,
    mode: str,
    limit: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    candidate_bundle = score_als_candidates_for_user(user_id)
    raw_rows = candidate_bundle.get("rows", [])
    source = enrich_poi_row(source_row) if source_row else None
    target_city = normalize_text(city or (source.get("city_name") if source else ""))
    target_province = normalize_text(province or (source.get("province") if source else ""))
    min_score = min([safe_float(row.get("score")) for row in raw_rows], default=0.0)
    max_score = max([safe_float(row.get("score")) for row in raw_rows], default=0.0)
    mode_name = next((item["name"] for item in recommendation_modes() if item["key"] == mode), mode)
    picked: List[Dict[str, Any]] = []

    for raw in raw_rows:
        target = enrich_poi_row({"poi_id": raw.get("poi_id")})
        if not target.get("poi_id"):
            continue
        if target_city and normalize_text(target.get("city_name")) != target_city:
            continue
        if target_province and normalize_text(target.get("province")) != target_province:
            continue
        if source and normalize_text(target.get("poi_id")) == normalize_text(source.get("poi_id")):
            continue

        score = safe_float(raw.get("score"))
        als_score = 1.0 if max_score <= min_score else clamp((score - min_score) / max(max_score - min_score, 1e-9), 0.0, 1.0)
        content_score, shared_terms = content_similarity_score(source, target) if source else (0.0, [])
        geo_score, distance_km = geo_similarity_score(source, target) if source else (0.0, 0.0)
        rule_score, rule_reasons = rule_preference_score(source, target) if source else (quality_score_of(target), [])
        quality_score = quality_score_of(target)

        if mode == "near_first":
            final_score = clamp(als_score * 0.56 + geo_score * 0.20 + rule_score * 0.08 + quality_score * 0.16, 0.0, 1.0)
        elif mode == "interest_first":
            final_score = clamp(als_score * 0.52 + content_score * 0.22 + rule_score * 0.10 + quality_score * 0.16, 0.0, 1.0)
        elif mode == "reputation_first":
            final_score = clamp(als_score * 0.50 + quality_score * 0.26 + rule_score * 0.16 + content_score * 0.08, 0.0, 1.0)
        else:
            final_score = clamp(als_score * 0.58 + content_score * 0.14 + rule_score * 0.10 + quality_score * 0.18, 0.0, 1.0)

        if source:
            if shared_terms:
                reason = f"ALS 协同过滤推荐；与你有相似收藏/评论行为的游客也偏好这里，并且与 {source.get('poi_name')} 共享 {('、'.join(shared_terms[:3]))} 等主题。"
            elif rule_reasons:
                reason = f"ALS 协同过滤推荐；相似用户偏好明显，同时命中 {('、'.join(rule_reasons[:3]))} 等规则特征。"
            else:
                reason = "ALS 协同过滤推荐；相似用户的行为偏好与当前景点组合较为接近。"
        else:
            reason = "ALS 协同过滤推荐；根据你过往收藏与评论行为，优先推荐相似用户喜欢的景点。"

        picked.append(
            {
                "source_poi_id": source.get("poi_id") if source else "",
                "source_poi_name": source.get("poi_name") if source else "",
                "source_city_name": source.get("city_name") if source else "",
                "source_province": source.get("province") if source else "",
                "mode": mode,
                "mode_name": mode_name,
                "algorithm": "als",
                "recommend_rank": 0,
                "target_poi_id": target.get("poi_id"),
                "target_poi_name": target.get("poi_name"),
                "target_city_name": target.get("city_name"),
                "target_region_name": target.get("region_name"),
                "target_price": target.get("price"),
                "target_comment_score": target.get("comment_score"),
                "target_comment_count": target.get("comment_count"),
                "target_heat_score": target.get("heat_score"),
                "target_distance_level": target.get("distance_level"),
                "content_score": round(content_score, 6),
                "geo_score": round(geo_score, 6),
                "rule_score": round(rule_score, 6),
                "behavior_score": round(als_score, 6),
                "quality_score": round(quality_score, 6),
                "recommend_score": round(score, 6),
                "final_score": round(final_score, 6),
                "distance_km": round(distance_km, 3),
                "shared_tags": "、".join(shared_terms[:6]),
                "reason_text": reason,
                "detail_url": target.get("detail_url"),
                "cover_image_url": target.get("cover_image_url"),
            }
        )

    if len(picked) < limit and source:
        existing_ids = {normalize_text(row.get("target_poi_id")) for row in picked}
        for target in candidate_rows_for_source(source, strict_city=True):
            target_id = normalize_text(target.get("poi_id"))
            if not target_id or target_id in existing_ids or target_id == normalize_text(source.get("poi_id")):
                continue
            content_score, shared_terms = content_similarity_score(source, target)
            geo_score, distance_km = geo_similarity_score(source, target)
            rule_score, rule_reasons = rule_preference_score(source, target)
            quality_score = quality_score_of(target)
            als_score = 0.18 if candidate_bundle.get("status") == "ok" else 0.0
            if mode == "near_first":
                final_score = clamp(als_score * 0.18 + geo_score * 0.34 + rule_score * 0.14 + quality_score * 0.34, 0.0, 1.0)
            elif mode == "interest_first":
                final_score = clamp(als_score * 0.12 + content_score * 0.38 + rule_score * 0.16 + quality_score * 0.34, 0.0, 1.0)
            elif mode == "reputation_first":
                final_score = clamp(als_score * 0.10 + quality_score * 0.42 + rule_score * 0.28 + content_score * 0.20, 0.0, 1.0)
            else:
                final_score = clamp(als_score * 0.14 + content_score * 0.28 + rule_score * 0.20 + quality_score * 0.38, 0.0, 1.0)
            picked.append(
                {
                    "source_poi_id": source.get("poi_id"),
                    "source_poi_name": source.get("poi_name"),
                    "source_city_name": source.get("city_name"),
                    "source_province": source.get("province"),
                    "mode": mode,
                    "mode_name": mode_name,
                    "algorithm": "als",
                    "recommend_rank": 0,
                    "target_poi_id": target.get("poi_id"),
                    "target_poi_name": target.get("poi_name"),
                    "target_city_name": target.get("city_name"),
                    "target_region_name": target.get("region_name"),
                    "target_price": target.get("price"),
                    "target_comment_score": target.get("comment_score"),
                    "target_comment_count": target.get("comment_count"),
                    "target_heat_score": target.get("heat_score"),
                    "target_distance_level": target.get("distance_level"),
                    "content_score": round(content_score, 6),
                    "geo_score": round(geo_score, 6),
                    "rule_score": round(rule_score, 6),
                    "behavior_score": round(als_score, 6),
                    "quality_score": round(quality_score, 6),
                    "recommend_score": round(final_score, 6),
                    "final_score": round(final_score, 6),
                    "distance_km": round(distance_km, 3),
                    "shared_tags": "、".join(shared_terms[:6]),
                    "reason_text": f"ALS 候选不足，补充同城同类景点；优先保留 {source.get('city_name')} 内与当前景点主题接近、口碑稳定的点位。",
                    "detail_url": target.get("detail_url"),
                    "cover_image_url": target.get("cover_image_url"),
                }
            )
            existing_ids.add(target_id)
            if len(picked) >= limit * 2:
                break

    picked.sort(
        key=lambda row: (
            safe_float(row.get("final_score")),
            safe_float(row.get("behavior_score")),
            safe_float(row.get("quality_score")),
        ),
        reverse=True,
    )
    for idx, row in enumerate(picked[:limit], start=1):
        row["recommend_rank"] = idx
    return picked[:limit], candidate_bundle


@lru_cache(maxsize=1)
def load_guide_kb() -> List[Dict[str, Any]]:
    if not GUIDE_KB_PATH.exists():
        return []
    try:
        return json.loads(GUIDE_KB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def enrich_recommendation_row(row: Dict[str, Any]) -> Dict[str, Any]:
    target_stub = {
        "poi_id": row.get("target_poi_id"),
        "poi_name": row.get("target_poi_name"),
        "city_name": row.get("target_city_name"),
        "region_name": row.get("target_region_name"),
        "price": row.get("target_price"),
        "comment_score": row.get("target_comment_score"),
        "comment_count": row.get("target_comment_count"),
        "heat_score": row.get("target_heat_score"),
        "distance_level": row.get("target_distance_level"),
        "reason_text": row.get("reason_text"),
        "recommend_rank": row.get("recommend_rank"),
        "recommend_score": row.get("final_score") or row.get("recommend_score") or row.get("content_score") or 0,
    }
    enriched = enrich_poi_row(target_stub)
    for key in ["detail_url", "cover_image_url", "shared_tags", "source_poi_name", "mode", "mode_name", "distance_km"]:
        if row.get(key):
            enriched[key] = row.get(key)
    sub_scores = {
        "content": safe_float(row.get("content_score")),
        "geo": safe_float(row.get("geo_score")),
        "rule": safe_float(row.get("rule_score")),
        "behavior": safe_float(row.get("behavior_score")),
        "quality": safe_float(row.get("quality_score")),
    }
    if any(value > 0 for value in sub_scores.values()):
        enriched["sub_scores"] = sub_scores
    return enriched


def recommendation_rows_for_algorithm(algorithm: str) -> List[Dict[str, Any]]:
    if algorithm == "hybrid":
        return load_personalized_hybrid_recommendations()
    if algorithm == "content":
        return load_content_recommendations()
    return []


def build_home_heatmap_points(city_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for row in city_rows:
        city = normalize_text(row.get("city_name"))
        coord = EAST_CHINA_COORDS.get(city)
        if not coord:
            continue
        poi_count = safe_int(row.get("poi_count"))
        points.append(
            {
                "name": city,
                "province": row.get("province"),
                "lng": coord[0],
                "lat": coord[1],
                "value": poi_count,
                "heat": round(safe_float(row.get("avg_heat")), 2),
                "score": round(safe_float(row.get("avg_score")), 2),
                "comment_total": safe_int(row.get("comment_total")),
            }
        )
    return sorted(points, key=lambda item: item["value"], reverse=True)


def normalize_distance_level_label(value: Any) -> str:
    raw = normalize_text(value)
    alias = {
        "0-5km": "市中心",
        "5-10km": "近郊",
        "10-20km": "近郊",
        "20-50km": "远郊",
        "50km+": "远郊",
        "50km以上": "远郊",
        "步行可达": "市中心",
        "城区周边": "近郊",
        "城市外延": "远郊",
        "跨城目的地": "远郊",
        "未知": "未知距离",
        "": "未知距离",
    }
    return alias.get(raw, raw or "未知距离")


def normalize_home_distance_distribution(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    order = ["远郊", "近郊", "市中心", "未知距离"]
    counts: Dict[str, int] = {key: 0 for key in order}
    for row in rows:
        label = normalize_distance_level_label(row.get("distance_level"))
        value = safe_int(row.get("poi_count"))
        if label not in counts:
            label = "未知距离"
        counts[label] += value
    return [{"distance_level": key, "poi_count": counts.get(key, 0)} for key in order if counts.get(key, 0) > 0]


def distance_distribution_complete(rows: List[Dict[str, Any]]) -> bool:
    labels = {normalize_distance_level_label(row.get("distance_level")) for row in rows}
    return {"远郊", "近郊", "市中心"}.issubset(labels)


def build_home_distance_distribution(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    order = ["远郊", "近郊", "市中心", "未知距离"]
    counts: Dict[str, int] = {key: 0 for key in order}
    for row in rows:
        label = normalize_distance_level_label(row.get("distance_level"))
        if label not in counts:
            label = "未知距离"
        counts[label] += 1
    return [{"distance_level": key, "poi_count": counts.get(key, 0)} for key in order if counts.get(key, 0) > 0]


def build_home_comment_score_distribution(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    bins = [
        ("4.8-5.0", 4.8, 5.01),
        ("4.5-4.7", 4.5, 4.8),
        ("4.0-4.4", 4.0, 4.5),
        ("3.5-3.9", 3.5, 4.0),
        ("3.0以下", -1, 3.5),
    ]
    result = []
    for label, low, high in bins:
        count = 0
        for row in rows:
            score = safe_float(row.get("comment_score"))
            if low <= score < high:
                count += 1
        result.append({"score_band": label, "poi_count": count})
    return result


def poi_composite_score(row: Dict[str, Any]) -> float:
    heat = safe_float(row.get("heat_score"))
    score = safe_float(row.get("comment_score"))
    comments = safe_int(row.get("comment_count"))
    price = safe_float(row.get("price"))
    value_bonus = 3 if price <= 0 else max(0, 2 - price / 180)
    return round(heat * 0.45 + score * 8 + min(comments, 50000) / 5000 + value_bonus, 4)


def build_province_top_poi(rows: List[Dict[str, Any]], limit: int = 8) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        enriched = enrich_poi_row(row)
        province = normalize_text(enriched.get("province"))
        if not province:
            continue
        enriched["composite_score"] = poi_composite_score(enriched)
        grouped.setdefault(province, []).append(enriched)
    return {
        province: sorted(items, key=lambda item: item.get("composite_score", 0), reverse=True)[:limit]
        for province, items in grouped.items()
    }


def fetch_guide_options() -> Dict[str, Any]:
    rows = load_guide_kb()
    lookup = load_clean_poi_lookup()
    cities = sorted({normalize_text(row.get("city_name")) for row in lookup["by_id"].values() if row.get("city_name")})
    destinations = sorted({normalize_text(row.get("destination")) for row in rows if row.get("destination")})
    themes = ["自然风光", "历史人文", "亲子休闲", "美食打卡", "城市漫游", "小众深度"]
    preferences = ["轻松舒适", "高性价比", "热门打卡", "深度体验", "亲子友好", "摄影观景", "特种兵"]
    return {"cities": cities or destinations[:300], "themes": themes, "preferences": preferences, "has_llm": bool(os.getenv("LLM_API_KEY"))}


def search_guide_records(city: str, theme: str, preference: str, limit: int = 5) -> List[Dict[str, Any]]:
    rows = load_guide_kb()
    terms = [term for term in [city, theme, preference] if term]

    def score(row: Dict[str, Any]) -> int:
        text = normalize_text(row.get("search_text"))
        total = 0
        for term in terms:
            if term and term in text:
                total += 3
        if city and city in normalize_text(row.get("destination")):
            total += 6
        return total

    ranked = sorted(rows, key=score, reverse=True)
    return [row for row in ranked if score(row) > 0][:limit] or ranked[:limit]


def related_map_pois(city: str = "", theme: str = "", limit: int = 30) -> List[Dict[str, Any]]:
    lookup = load_clean_poi_lookup()
    rows = list(lookup["by_id"].values())
    def match_rows(require_theme: bool) -> List[Dict[str, Any]]:
        result = []
        for row in rows:
            if city and city not in normalize_text(row.get("city_name")):
                continue
            if not row.get("latitude") or not row.get("longitude"):
                continue
            if require_theme and theme:
                include_hits, exclude_hits, _ = theme_hits_of(row, theme)
                if not include_hits:
                    continue
                if len(exclude_hits) > len(include_hits):
                    continue
            result.append(row)
        return result

    filtered = match_rows(True)
    if not filtered:
        filtered = match_rows(False)
    for row in filtered:
        if city and city not in normalize_text(row.get("city_name")):
            continue
    filtered.sort(key=lambda row: (safe_float(row.get("heat_score")), safe_int(row.get("comment_count"))), reverse=True)
    return filtered[:limit]


def call_llm_for_plan(prompt: str) -> str:
    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    model = os.getenv("LLM_MODEL", "deepseek-chat").strip()
    if not api_key or not base_url:
        return ""
    if base_url.rstrip("/").endswith("/v1"):
        base_url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是华东旅游规划助手，请给出清晰、可执行、适合前端展示的中文建议。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
    }
    req = Request(
        base_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return normalize_text(body.get("choices", [{}])[0].get("message", {}).get("content"))
    except Exception:
        return ""


def split_tag_tokens(value: Any) -> List[str]:
    text = normalize_text(value)
    for sep in ["|", "，", ",", "/", "、", "；", ";"]:
        text = text.replace(sep, ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compose_poi_text(row: Dict[str, Any]) -> str:
    return " ".join(
        [
            normalize_text(row.get("poi_name")),
            normalize_text(row.get("city_name")),
            normalize_text(row.get("province")),
            normalize_text(row.get("region_name")),
            normalize_text(row.get("tag_text")),
            normalize_text(row.get("short_feature")),
            normalize_text(row.get("sight_level")),
        ]
    )


def theme_rule_of(theme: str) -> Dict[str, List[str]]:
    text = normalize_text(theme)
    for key, rule in THEME_RULES.items():
        if key in text:
            return rule
    return {"include": split_tag_tokens(text), "exclude": []}


def theme_hits_of(row: Dict[str, Any], theme: str) -> Tuple[List[str], List[str], str]:
    text = compose_poi_text(row)
    rule = theme_rule_of(theme)
    include_hits = [token for token in rule.get("include", []) if token and token in text]
    exclude_hits = [token for token in rule.get("exclude", []) if token and token in text]
    return include_hits, exclude_hits, text


def preference_tokens(preference: str) -> List[str]:
    pref = normalize_text(preference)
    tokens: List[str] = []
    for key, values in PREFERENCE_RULES.items():
        if key in pref:
            tokens.extend(values)
    return list(dict.fromkeys(tokens))


def region_label_of(row: Dict[str, Any], fallback_city: str = "") -> str:
    parts = [
        normalize_text(row.get("region_name")),
        normalize_text(row.get("district_name")),
        normalize_text(row.get("city_name")),
    ]
    for part in parts:
        if part and part not in {"中国", "华东地区", "景区", fallback_city}:
            return part
    return fallback_city or "核心景区"


def dominant_area(day_pois: List[Dict[str, Any]], city: str) -> str:
    counts: Dict[str, int] = {}
    for row in day_pois:
        area = region_label_of(row, city)
        counts[area] = counts.get(area, 0) + 1
    if not counts:
        return f"{city or '目的地'}核心区"
    return sorted(counts.items(), key=lambda item: (-item[1], len(item[0])))[0][0]


def area_guide_of(city: str, area: str) -> Dict[str, Any]:
    city_guides = CITY_AREA_GUIDE.get(city, [])
    area_text = normalize_text(area)
    for guide in city_guides:
        if any(token and token in area_text for token in guide.get("keywords", [])):
            return guide
    return {}


def choose_area_text(day_pois: List[Dict[str, Any]], city: str, index: int) -> str:
    if not day_pois:
        return city or "核心区"
    row = day_pois[max(0, min(index, len(day_pois) - 1))]
    return region_label_of(row, city)


def price_band_text(center: float, min_low: float = 0, spread: float = 0.22, suffix: str = "") -> str:
    if center <= 0:
        return "免费"
    low = max(min_low, int(round(center * (1 - spread))))
    high = max(low + 1, int(round(center * (1 + spread))))
    return f"¥{low}-{high}{suffix}"


def parse_price_estimate(value: Any, prefer: str = "mid") -> float:
    text = normalize_text(value)
    if not text or "免费" in text:
        return 0.0
    cleaned = text.replace("¥", "").replace(",", "")
    if "/" in cleaned:
        cleaned = cleaned.split("/")[0]
    parts = [safe_float(item) for item in cleaned.split("-") if item.strip()]
    parts = [item for item in parts if item > 0]
    if not parts:
        return 0.0
    if len(parts) == 1:
        return parts[0]
    if prefer == "low":
        return parts[0]
    if prefer == "high":
        return parts[-1]
    return sum(parts) / len(parts)


def plan_day_capacities(days: int, preference: str, budget_cfg: Optional[Dict[str, Any]] = None) -> List[int]:
    pref = normalize_text(preference)
    budget_level = normalize_text((budget_cfg or {}).get("level"))
    base = 3
    if "特种兵" in pref:
        base = 3 if budget_level == "low" else 4
    elif any(token in pref for token in ["轻松", "亲子", "休闲"]):
        base = 2
    elif any(token in pref for token in ["热门", "摄影", "打卡", "深度"]):
        base = 3
    capacities = [base for _ in range(days)]
    if days >= 2:
        capacities[-1] = max(2 if "特种兵" in pref else 1, base - 1)
    return capacities


def budget_profile(total_budget: float, days: int) -> Dict[str, Any]:
    budget = max(0.0, total_budget)
    day_budget = budget / max(days, 1) if budget else 0.0
    if budget:
        level = "low" if day_budget < 450 else "mid" if day_budget < 780 else "high"
        non_ticket_pool = day_budget * 0.72
        hotel_est = clamp(non_ticket_pool * 0.42, 90, 520)
        meal_pool = clamp(non_ticket_pool * 0.40, 48, 260)
        transport_pool = clamp(non_ticket_pool * 0.18, 10, 120)
        breakfast_est = clamp(meal_pool * 0.22, 10, 50)
        lunch_est = clamp(meal_pool * 0.36, 20, 120)
        dinner_est = clamp(meal_pool * 0.42, 25, 160)
        city_transport_est = clamp(transport_pool * 0.38, 4, 32)
        cross_transport_est = clamp(transport_pool * 0.82, 12, 90)
        ticket_cap = max(0.0, day_budget - hotel_est - breakfast_est - lunch_est - dinner_est - transport_pool)
        return {
            "level": level,
            "hotel": price_band_text(hotel_est, min_low=80, spread=0.20, suffix="/晚"),
            "breakfast": price_band_text(breakfast_est, min_low=8, spread=0.22),
            "lunch": price_band_text(lunch_est, min_low=18, spread=0.22),
            "dinner": price_band_text(dinner_est, min_low=22, spread=0.22),
            "city_transport": price_band_text(city_transport_est, min_low=0, spread=0.35),
            "cross_transport": price_band_text(cross_transport_est, min_low=8, spread=0.35),
            "hotel_estimate": hotel_est,
            "breakfast_estimate": breakfast_est,
            "lunch_estimate": lunch_est,
            "dinner_estimate": dinner_est,
            "city_transport_estimate": city_transport_est,
            "cross_transport_estimate": cross_transport_est,
            "ticket_cap_per_day": ticket_cap,
        }
    return {
        "level": "mid",
        "hotel": "¥220-320/晚",
        "breakfast": "¥18-28",
        "lunch": "¥35-60",
        "dinner": "¥50-80",
        "city_transport": "¥5-18",
        "cross_transport": "¥18-60",
        "hotel_estimate": 260.0,
        "breakfast_estimate": 22.0,
        "lunch_estimate": 48.0,
        "dinner_estimate": 65.0,
        "city_transport_estimate": 10.0,
        "cross_transport_estimate": 28.0,
        "ticket_cap_per_day": 120.0,
    }


def price_text_of(value: Any) -> str:
    price = safe_float(value)
    if price <= 0:
        return "免费"
    return f"¥{int(round(price))}"


def poi_main_tag(row: Dict[str, Any]) -> str:
    tags = split_tag_tokens(row.get("tag_text"))
    if tags:
        return tags[0]
    feature = normalize_text(row.get("short_feature"))
    return feature[:8] if feature else "综合"


def poi_theme_match_score(row: Dict[str, Any], city: str, theme: str, preference: str, budget_cfg: Optional[Dict[str, Any]] = None) -> float:
    score = poi_composite_score(row) * 10
    text = compose_poi_text(row)
    if city and city in text:
        score += 30
    include_hits, exclude_hits, _ = theme_hits_of(row, theme)
    if theme:
        if include_hits:
            score += 26 + len(set(include_hits)) * 9
        else:
            score -= 34
        score -= len(set(exclude_hits)) * 14
    for token in preference_tokens(preference):
        if token and token in text:
            score += 7
    if any(token in text for token in ["5A", "世界", "古镇", "博物馆", "湿地", "乐园"]):
        score += 4
    price = safe_float(row.get("price"))
    budget_cfg = budget_cfg or {}
    budget_level = normalize_text(budget_cfg.get("level")) or "mid"
    ticket_cap = safe_float(budget_cfg.get("ticket_cap_per_day"))
    if budget_level == "low":
        if price <= 0:
            score += 10
        elif price > 120:
            score -= 18
        elif price > 80:
            score -= 8
    elif budget_level == "high":
        if price > 120:
            score += 4
    if ticket_cap > 0:
        if price <= ticket_cap * 0.55:
            score += 8
        elif price <= ticket_cap:
            score += 4
        elif price > ticket_cap * 1.45:
            score -= 28
        elif price > ticket_cap:
            score -= 12
    if "特种兵" in normalize_text(preference):
        score += safe_float(row.get("comment_count")) / 2000
    if "高性价比" in normalize_text(preference) and price <= 80:
        score += 10
    if "热门打卡" in normalize_text(preference):
        score += safe_float(row.get("heat_score")) * 1.8
    return score


def geo_distance(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    return math.hypot(safe_float(a.get("longitude")) - safe_float(b.get("longitude")), safe_float(a.get("latitude")) - safe_float(b.get("latitude")))


def order_pois_by_geo(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    points = [row for row in rows if safe_float(row.get("longitude")) and safe_float(row.get("latitude"))]
    if len(points) <= 2:
        return points
    start = min(points, key=lambda row: (safe_float(row.get("longitude")), safe_float(row.get("latitude"))))
    ordered = [start]
    remaining = [row for row in points if row is not start]
    while remaining:
        last = ordered[-1]
        next_row = min(remaining, key=lambda row: geo_distance(last, row))
        ordered.append(next_row)
        remaining.remove(next_row)
    return ordered


def select_route_pois(pois: List[Dict[str, Any]], city: str, theme: str, preference: str, days: int, budget_cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    capacities = plan_day_capacities(days, preference, budget_cfg)
    target_count = max(2, sum(capacities))
    ranked = sorted(pois, key=lambda row: poi_theme_match_score(row, city, theme, preference, budget_cfg), reverse=True)
    selected: List[Dict[str, Any]] = []
    seen_names = set()
    tag_counts: Dict[str, int] = {}
    max_same_tag = 1 if days <= 2 else 2
    reserve: List[Dict[str, Any]] = []
    reserve_budget: List[Dict[str, Any]] = []
    ticket_limit = safe_float((budget_cfg or {}).get("ticket_cap_per_day")) * max(days, 1) * 1.08
    current_ticket_total = 0.0
    for row in ranked:
        name = normalize_text(row.get("poi_name"))
        if not name or name in seen_names:
            continue
        tag = poi_main_tag(row)
        record = dict(row)
        record["main_tag"] = tag
        price = safe_float(row.get("price"))
        if ticket_limit > 0 and price > 0 and current_ticket_total + price > ticket_limit:
            reserve_budget.append(record)
            continue
        if tag_counts.get(tag, 0) >= max_same_tag:
            reserve.append(record)
            continue
        selected.append(record)
        seen_names.add(name)
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
        current_ticket_total += price
        if len(selected) >= target_count:
            break
    if len(selected) < target_count:
        for row in reserve:
            name = normalize_text(row.get("poi_name"))
            if name in seen_names:
                continue
            selected.append(row)
            seen_names.add(name)
            current_ticket_total += safe_float(row.get("price"))
            if len(selected) >= target_count:
                break
    if len(selected) < target_count:
        for row in reserve_budget:
            name = normalize_text(row.get("poi_name"))
            if name in seen_names:
                continue
            selected.append(row)
            seen_names.add(name)
            if len(selected) >= target_count:
                break
    return order_pois_by_geo(selected[:target_count])


def infer_transport(distance_km: float, budget_cfg: Optional[Dict[str, Any]] = None) -> Tuple[str, str, str, float]:
    budget_cfg = budget_cfg or budget_profile(0, 1)
    if distance_km < 1.2:
        return "步行", "15-20分钟", "¥0", 0.0
    city_base = safe_float(budget_cfg.get("city_transport_estimate", 10))
    cross_base = safe_float(budget_cfg.get("cross_transport_estimate", 28))
    if distance_km < 6:
        estimate = max(4.0, city_base * 0.9)
        return "地铁 / 公交", "20-35分钟", price_band_text(estimate, spread=0.35), estimate
    if distance_km < 15:
        estimate = max(8.0, city_base * 1.35)
        return "地铁 + 打车接驳", "35-50分钟", price_band_text(estimate, spread=0.32), estimate
    estimate = max(15.0, cross_base)
    return "网约车 / 城际交通", "45-75分钟", price_band_text(estimate, spread=0.30), estimate


def split_route_into_days(route_pois: List[Dict[str, Any]], days: int, preference: str, budget_cfg: Optional[Dict[str, Any]] = None) -> List[List[Dict[str, Any]]]:
    capacities = plan_day_capacities(days, preference, budget_cfg)
    groups: List[List[Dict[str, Any]]] = []
    cursor = 0
    for capacity in capacities:
        group = route_pois[cursor : cursor + capacity]
        groups.append(group)
        cursor += capacity
    if cursor < len(route_pois):
        for row in route_pois[cursor:]:
            smallest = min(range(len(groups)), key=lambda idx: len(groups[idx]))
            groups[smallest].append(row)
    return groups


def meal_name_for(theme: str, meal_type: str, city: str, area: str, day_no: int = 1) -> Tuple[str, str]:
    theme_text = normalize_text(theme)
    city_text = city or "当地"
    food_key = "breakfast" if meal_type == "早餐" else "lunch" if meal_type == "午餐" else "dinner"
    guide = area_guide_of(city_text, area)
    food_list = guide.get(food_key) or CITY_FOOD_GUIDE.get(city_text, {}).get(food_key) or {
        "breakfast": ["本地早点", "豆浆油条"],
        "lunch": ["特色家常菜", "本地热门餐馆"],
        "dinner": ["夜市小吃", "特色餐馆"],
    }[food_key]
    index = (day_no - 1) % max(1, len(food_list))
    alt_index = (index + 1) % max(1, len(food_list))
    primary = food_list[index]
    secondary = food_list[alt_index] if len(food_list) > 1 else primary
    duo = f"{primary} / {secondary}" if primary != secondary else primary
    zone = guide.get("zone") or f"{area}周边"
    if meal_type == "早餐":
        return f"{zone}早餐安排：{duo}", f"{city_text} / {zone}"
    if "美食" in theme_text:
        return f"{zone}重点打卡：{duo}", f"{city_text} / {zone}"
    if meal_type == "午餐":
        return f"{zone}午餐建议：{duo}", f"{city_text} / {zone}"
    return f"{zone}晚餐收尾：{duo}", f"{city_text} / {zone}"


def fallback_hotel_text(city: str, area: str = "", budget_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    city_text = city or "目的地"
    budget_cfg = budget_cfg or budget_profile(0, 1)
    level = normalize_text(budget_cfg.get("level")) or "mid"
    hotel_type = {"low": "便捷酒店", "mid": "舒适型酒店", "high": "品质酒店"}.get(level, "舒适型酒店")
    area_text = area or f"{city_text}核心区"
    guide = area_guide_of(city_text, area_text)
    hotel_name = guide.get(f"hotel_{level}") or f"{area_text}{hotel_type}"
    hotel_area = guide.get("hotel_area") or area_text
    return {
        "name": hotel_name,
        "location": f"{city_text} / {hotel_area}",
        "price_text": budget_cfg.get("hotel", "¥260-420/晚"),
        "estimate_price": safe_float(budget_cfg.get("hotel_estimate", 260)),
    }


def day_theme_name(day_index: int, total_days: int, theme: str) -> str:
    if day_index == 0:
        return f"{theme or '城市初体验'}导入日"
    if day_index == total_days - 1 and total_days > 1:
        return "返程收束日"
    return f"{theme or '精选景点'}深度日"


def build_route_day(day_no: int, day_pois: List[Dict[str, Any]], total_days: int, city: str, theme: str, preference: str, budget_cfg: Dict[str, Any]) -> Dict[str, Any]:
    periods = [
        ("上午", "09:00-11:30"),
        ("下午", "13:30-16:30"),
        ("傍晚", "17:30-19:30"),
        ("夜间", "19:30-21:00"),
    ]
    schedule = []
    transport = []
    meals = []
    base_area = dominant_area(day_pois, city)
    hotel = fallback_hotel_text(city, base_area, budget_cfg)
    if not day_pois:
        return {
            "day": day_no,
            "theme": day_theme_name(day_no - 1, total_days, theme),
            "route_note": "本日未匹配到足够景点，建议作为机动休整或自由活动时间。",
            "schedule": [],
            "meals": [],
            "hotel": hotel,
            "transport": [],
            "tips": ["优先补休、调整天气影响，保留弹性时间。"],
        }

    for idx, poi in enumerate(day_pois):
        period, time_text = periods[min(idx, len(periods) - 1)]
        location_text = " / ".join(filter(None, [normalize_text(poi.get("city_name")), region_label_of(poi, city)]))
        schedule.append(
            {
                "period": period,
                "time": time_text,
                "poi_name": poi.get("poi_name"),
                "location": location_text,
                "stay": "2-3小时" if idx < 2 else "1.5-2小时",
                "price_text": price_text_of(poi.get("price")),
                "estimate_price": safe_float(poi.get("price")),
                "main_tag": poi.get("main_tag") or poi_main_tag(poi),
            }
        )
        poi["day"] = day_no
        poi["visit_order"] = idx + 1
        poi["period"] = period
        poi["time_text"] = time_text

    breakfast_area = base_area
    lunch_area = choose_area_text(day_pois, city, 1 if len(day_pois) > 1 else 0)
    dinner_area = choose_area_text(day_pois, city, len(day_pois) - 1)
    breakfast_name, breakfast_location = meal_name_for(theme, "早餐", city, breakfast_area, day_no)
    lunch_name, lunch_location = meal_name_for(theme, "午餐", city, lunch_area, day_no)
    dinner_name, dinner_location = meal_name_for(theme, "晚餐", city, dinner_area, day_no)
    meals.extend(
        [
            {
                "meal_type": "早餐",
                "name": breakfast_name,
                "location": breakfast_location,
                "price_text": budget_cfg.get("breakfast", "¥20-35"),
                "estimate_price": safe_float(budget_cfg.get("breakfast_estimate", 22)),
            },
            {
                "meal_type": "午餐",
                "name": lunch_name,
                "location": lunch_location,
                "price_text": budget_cfg.get("lunch", "¥50-90"),
                "estimate_price": safe_float(budget_cfg.get("lunch_estimate", 48)),
            },
            {
                "meal_type": "晚餐",
                "name": dinner_name,
                "location": dinner_location,
                "price_text": budget_cfg.get("dinner", "¥60-120"),
                "estimate_price": safe_float(budget_cfg.get("dinner_estimate", 65)),
            },
        ]
    )

    first = day_pois[0]
    start_est = safe_float(budget_cfg.get("city_transport_estimate", 10))
    transport.append(
        {
            "from": hotel["location"],
            "to": normalize_text(first.get("poi_name")),
            "mode": "步行 / 地铁" if breakfast_area == region_label_of(first, city) else "地铁 / 打车",
            "duration": "10-25分钟" if breakfast_area == region_label_of(first, city) else "20-35分钟",
            "price_text": "¥0" if breakfast_area == region_label_of(first, city) else price_band_text(start_est, spread=0.35),
            "estimate_price": 0.0 if breakfast_area == region_label_of(first, city) else start_est,
        }
    )
    for idx in range(len(day_pois) - 1):
        a = day_pois[idx]
        b = day_pois[idx + 1]
        distance_km = geo_distance(a, b) * 111
        mode, duration, price_text, estimate_price = infer_transport(distance_km, budget_cfg)
        transport.append(
            {
                "from": normalize_text(a.get("poi_name")),
                "to": normalize_text(b.get("poi_name")),
                "mode": mode,
                "duration": duration,
                "price_text": price_text,
                "estimate_price": estimate_price,
            }
        )
    if total_days > 1 and day_no == total_days:
        cross_est = safe_float(budget_cfg.get("cross_transport_estimate", 28))
        transport.append(
            {
                "from": normalize_text(day_pois[-1].get("poi_name")),
                "to": "机场 / 高铁站",
                "mode": "地铁快线 / 网约车",
                "duration": "30-60分钟",
                "price_text": budget_cfg.get("cross_transport", "¥25-80"),
                "estimate_price": cross_est,
            }
        )
    else:
        back_distance_km = max(1.0, geo_distance(day_pois[-1], day_pois[0]) * 111 * 0.7)
        mode, duration, price_text, estimate_price = infer_transport(back_distance_km, budget_cfg)
        transport.append(
            {
                "from": normalize_text(day_pois[-1].get("poi_name")),
                "to": hotel["name"],
                "mode": mode,
                "duration": duration,
                "price_text": price_text,
                "estimate_price": estimate_price,
            }
        )

    return {
        "day": day_no,
        "theme": day_theme_name(day_no - 1, total_days, theme),
        "route_note": f"第 {day_no} 天按地理顺向依次游玩，减少跨区折返；当天共安排 {len(day_pois)} 个主要点位。",
        "schedule": schedule,
        "meals": meals,
        "hotel": hotel,
        "transport": transport,
        "tips": [
            "上午优先核心景点，下午安排次核心点位，避免来回折返。",
            "若遇天气突变，可保留最后一个点位作为可替换项。",
            "已结合预算调整餐饮、住宿和交通档位，尽量让花费与行程强度匹配。",
        ],
    }


def build_budget_breakdown(days_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ticket_total = 0
    meal_total = 0
    transport_total = 0
    hotel_total = 0
    for day in days_data:
        for item in day.get("schedule", []):
            ticket_total += int(round(safe_float(item.get("estimate_price")) or parse_price_estimate(item.get("price_text"), "mid")))
        for item in day.get("meals", []):
            meal_total += int(round(safe_float(item.get("estimate_price")) or parse_price_estimate(item.get("price_text"), "low")))
        for item in day.get("transport", []):
            transport_total += int(round(safe_float(item.get("estimate_price")) or parse_price_estimate(item.get("price_text"), "mid")))
        hotel_total += int(round(safe_float((day.get("hotel") or {}).get("estimate_price")) or parse_price_estimate((day.get("hotel") or {}).get("price_text"), "low")))
    return [
        {"name": "门票", "price_text": f"¥{ticket_total or 0}"},
        {"name": "餐饮", "price_text": f"¥{meal_total or 0}"},
        {"name": "交通", "price_text": f"¥{transport_total or 0}"},
        {"name": "住宿", "price_text": f"¥{hotel_total or 0}"},
    ]


def budget_breakdown_total(rows: List[Dict[str, Any]]) -> int:
    total = 0
    for row in rows:
        text = normalize_text(row.get("price_text")).replace("¥", "").replace(",", "")
        total += safe_int(text)
    return total


def normalize_llm_json_answer(answer: str) -> Dict[str, Any]:
    text = normalize_text(answer)
    if not text:
        return {}
    if "```" in text:
        chunks = [chunk.strip() for chunk in text.split("```") if chunk.strip()]
        for chunk in chunks:
            if "{" in chunk and "}" in chunk:
                text = chunk
                break
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def fallback_llm_advice(local_plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "summary": local_plan.get("summary", ""),
        "route_note": local_plan.get("route_explanation", ""),
        "highlights": [
            "路线已经按地理顺向排布，优先同片区串联，减少折返。",
            "返程日主动减少点位，避免最后一天过满导致赶路。",
            "同类景点已做去重控制，优先保留代表性更强的点位。",
        ],
        "food_tips": [
            "午餐优先放在第二个点位附近，减少中途大幅绕路。",
            "晚餐建议安排在夜游点或酒店商圈附近，方便收尾休息。",
        ],
        "transport_tips": [
            "3公里内优先步行或公交，跨区时优先地铁再接驳。",
            "热门景点之间预留 20-40 分钟缓冲，节假日再额外增加时间。",
        ],
        "tips": local_plan.get("tips", []),
    }


def build_ai_plan(query: Dict[str, List[str]]) -> Dict[str, Any]:
    city = normalize_text(query.get("city", [""])[0])
    theme = normalize_text(query.get("theme", [""])[0])
    preference = normalize_text(query.get("preference", [""])[0])
    days = max(1, min(safe_int(query.get("days", ["3"])[0]), 7))
    travel_date = normalize_text(query.get("date", [""])[0])
    budget_input = safe_float(query.get("budget", ["0"])[0])
    use_llm = normalize_text(query.get("use_llm", ["1"])[0]) != "0"
    guides = search_guide_records(city, theme, preference, 4)
    pois = related_map_pois(city, theme, max(24, days * 6))
    budget_cfg = budget_profile(budget_input, days)
    route_pois = select_route_pois(pois, city, theme, preference, days, budget_cfg)
    day_groups = split_route_into_days(route_pois, days, preference, budget_cfg)

    guide_text = "\n".join(
        [
            f"目的地：{row.get('destination')}\n交通：{row.get('traffic')}\n住宿：{row.get('hotel')}\n景点：{row.get('attractions')}\n美食：{row.get('food')}\n贴士：{row.get('tips')}"
            for row in guides[:3]
        ]
    )
    day_plans = [build_route_day(index + 1, group, days, city, theme, preference, budget_cfg) for index, group in enumerate(day_groups)]
    budget_breakdown = build_budget_breakdown(day_plans)
    budget_total = budget_breakdown_total(budget_breakdown)
    local_plan = {
        "title": f"{city or '华东'}{days}日{theme or '综合'}旅行方案",
        "summary": f"本方案已按地理动线顺向排布景点，并结合{preference or '综合体验'}偏好控制每日强度。",
        "route_explanation": "已强制执行同类景点去重、按偏好控制单日游玩强度、返程日精简点位、标准化出行贴士、跨区折返规避五项规则，优先让路线通顺、主题一致、每日节奏可落地。",
        "route_rules": [
            "同类景点去重：避免一天内堆砌多个相似景点。",
            "强度控制：轻松/亲子偏好默认每天 2 个主点，综合/深度默认每天 3 个主点。",
            "返程日精简：最后一天自动减少一个主点位，留出退房和返程缓冲。",
            "地理顺向：按相邻片区串联，减少跨区折返。",
            "贴士标准化：固定输出预约、天气、交通、夜间安全等提醒。",
        ],
        "days": day_plans,
        "budget_breakdown": budget_breakdown,
        "budget_total": budget_total,
        "budget_input": budget_input,
        "budget_level": budget_cfg.get("level", "mid"),
        "tips": [
            "热门景点优先安排在上午，节假日建议至少提前 1 天预约门票。",
            "若遇雨天，可把最后一个户外点位替换成室内馆类或街区美食点。",
            "跨区换乘建议至少预留 20-40 分钟缓冲，高峰期再额外增加时间。",
        ],
    }
    prompt = (
        "你是旅游行程优化助手。请只做补充说明，不要推翻既定路线顺序。\n"
        f"城市：{city or '未指定'}；主题：{theme or '综合'}；偏好：{preference or '综合体验'}；天数：{days}；预算：{budget_input or '未指定'}；出行日期：{travel_date or '未指定'}。\n"
        f"既定路线说明：{local_plan['route_explanation']}\n"
        f"既定路线点位：{json.dumps([{'day': row.get('day'), 'order': row.get('visit_order'), 'poi_name': row.get('poi_name'), 'city_name': row.get('city_name')} for row in route_pois], ensure_ascii=False)}\n"
        f"攻略资料：\n{guide_text}\n"
        "请严格返回 JSON 对象，字段必须包含 summary、route_note、highlights、food_tips、transport_tips、tips。"
        "其中 highlights、food_tips、transport_tips、tips 都是字符串数组。"
        "要求：自动规避跨区折返、景点堆砌、主题不符，内容简洁直观，可直接展示给游客。"
    )
    llm_answer = call_llm_for_plan(prompt) if use_llm else ""
    llm_advice = normalize_llm_json_answer(llm_answer) or fallback_llm_advice(local_plan)
    return {
        "options": {"city": city, "theme": theme, "preference": preference, "days": days, "date": travel_date, "budget": budget_input},
        "guides": guides,
        "pois": route_pois or pois,
        "route_pois": route_pois,
        "local_plan": local_plan,
        "llm_advice": llm_advice,
        "llm_answer": llm_answer,
        "llm_enabled": bool(llm_answer),
    }


def build_province_summary(city_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in city_rows:
        province = row.get("province") or "未知省份"
        item = grouped.setdefault(
            province,
            {
                "province": province,
                "city_names": set(),
                "poi_count": 0,
                "comment_total": 0,
                "free_poi_count": 0,
                "high_score_poi_count": 0,
                "five_a_poi_count": 0,
                "weighted_price": 0.0,
                "weighted_score": 0.0,
                "weighted_heat": 0.0,
            },
        )
        poi_count = safe_int(row.get("poi_count"))
        if row.get("city_name"):
            item["city_names"].add(row.get("city_name"))
        item["poi_count"] += poi_count
        item["comment_total"] += safe_int(row.get("comment_total"))
        item["free_poi_count"] += safe_int(row.get("free_poi_count"))
        item["high_score_poi_count"] += safe_int(row.get("high_score_poi_count"))
        item["five_a_poi_count"] += safe_int(row.get("five_a_poi_count"))
        item["weighted_price"] += safe_float(row.get("avg_price")) * poi_count
        item["weighted_score"] += safe_float(row.get("avg_score")) * poi_count
        item["weighted_heat"] += safe_float(row.get("avg_heat")) * poi_count
    result = []
    for item in grouped.values():
        poi_count = max(safe_int(item["poi_count"]), 1)
        result.append(
            {
                "province": item["province"],
                "city_count": len(item["city_names"]),
                "poi_count": item["poi_count"],
                "comment_total": item["comment_total"],
                "free_poi_count": item["free_poi_count"],
                "high_score_poi_count": item["high_score_poi_count"],
                "five_a_poi_count": item["five_a_poi_count"],
                "avg_price": round(item["weighted_price"] / poi_count, 2),
                "avg_score": round(item["weighted_score"] / poi_count, 2),
                "avg_heat": round(item["weighted_heat"] / poi_count, 2),
                "free_ratio": round(item["free_poi_count"] / poi_count, 4),
                "high_score_ratio": round(item["high_score_poi_count"] / poi_count, 4),
            }
        )
    return sorted(result, key=lambda x: (x["poi_count"], x["comment_total"]), reverse=True)


def fetch_recommendation_source_options(limit: int = 40) -> List[str]:
    options: List[str] = []
    seen = set()
    for row in load_personalized_hybrid_recommendations():
        name = normalize_text(row.get("source_poi_name"))
        if name and name not in seen:
            options.append(name)
            seen.add(name)
        if len(options) >= limit:
            return options
    for row in load_ranked_recommendations():
        name = normalize_text(row.get("source_poi_name"))
        if name and name not in seen:
            options.append(name)
            seen.add(name)
        if len(options) >= limit:
            return options
    for row in sorted(load_clean_poi_records(), key=lambda item: (safe_float(item.get("heat_score")), safe_int(item.get("comment_count"))), reverse=True):
        name = normalize_text(row.get("poi_name"))
        if name and name not in seen:
            options.append(name)
            seen.add(name)
        if len(options) >= limit:
            break
    return options


def recommend_content_tokens(row: Dict[str, Any]) -> set[str]:
    text = compose_poi_text(row)
    tokens = set(split_tag_tokens(row.get("tag_text")))
    for key in ("poi_name", "region_name", "short_feature", "sight_level"):
        value = normalize_text(row.get(key))
        if value and len(value) >= 2:
            tokens.add(value)
    for token in [
        "历史",
        "建筑",
        "博物馆",
        "纪念馆",
        "文化",
        "古街",
        "故居",
        "夜游",
        "亲子",
        "遛娃",
        "公园",
        "温泉",
        "自然",
        "登山",
        "地标",
        "城市漫步",
        "美术馆",
        "科技馆",
        "寺",
        "广场",
    ]:
        if token in text:
            tokens.add(token)
    return {token for token in tokens if token}


def haversine_km(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    lat1 = safe_float(a.get("latitude"))
    lon1 = safe_float(a.get("longitude"))
    lat2 = safe_float(b.get("latitude"))
    lon2 = safe_float(b.get("longitude"))
    if not lat1 or not lon1 or not lat2 or not lon2:
        return 0.0
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def content_similarity_score(source: Dict[str, Any], target: Dict[str, Any]) -> Tuple[float, List[str]]:
    source_tokens = recommend_content_tokens(source)
    target_tokens = recommend_content_tokens(target)
    shared = sorted(source_tokens & target_tokens)
    token_score = len(shared) / max(len(source_tokens | target_tokens), 1)
    source_tags = set(split_tag_tokens(source.get("tag_text")))
    target_tags = set(split_tag_tokens(target.get("tag_text")))
    tag_score = len(source_tags & target_tags) / max(len(source_tags | target_tags), 1)
    same_region = 1.0 if normalize_text(source.get("region_name")) and normalize_text(source.get("region_name")) == normalize_text(target.get("region_name")) else 0.0
    score = clamp(tag_score * 0.56 + token_score * 0.34 + same_region * 0.18, 0.0, 1.0)
    return score, shared[:6]


def geo_similarity_score(source: Dict[str, Any], target: Dict[str, Any]) -> Tuple[float, float]:
    distance_km = haversine_km(source, target)
    same_city = 1.0 if normalize_text(source.get("city_name")) == normalize_text(target.get("city_name")) else 0.0
    same_province = 1.0 if normalize_text(source.get("province")) == normalize_text(target.get("province")) else 0.0
    same_region = 1.0 if normalize_text(source.get("region_name")) and normalize_text(source.get("region_name")) == normalize_text(target.get("region_name")) else 0.0
    distance_score = math.exp(-distance_km / 5.0) if distance_km > 0 else 0.0
    score = clamp(distance_score * 0.70 + same_region * 0.18 + same_city * 0.10 + same_province * 0.02, 0.0, 1.0)
    return score, distance_km


def rule_preference_score(source: Dict[str, Any], target: Dict[str, Any]) -> Tuple[float, List[str]]:
    reasons: List[str] = []
    score = 0.0
    if normalize_text(source.get("region_name")) and normalize_text(source.get("region_name")) == normalize_text(target.get("region_name")):
        score += 0.20
        reasons.append("同片区")
    if normalize_text(target.get("distance_level")) == "市中心":
        score += 0.12
        reasons.append("市中心")
    elif normalize_text(target.get("distance_level")) == "近郊":
        score += 0.08
        reasons.append("近郊")
    if safe_float(target.get("comment_score")) >= 4.5:
        score += 0.16
        reasons.append("高评分")
    if safe_float(target.get("heat_score")) >= 7.0 or "超高热度" in normalize_text(target.get("heat_level")):
        score += 0.12
        reasons.append("高热度")
    if safe_int(target.get("comment_count")) >= 500:
        score += 0.10
        reasons.append("人气高")
    if normalize_text(target.get("is_free")) == "1":
        score += 0.08
        reasons.append("免费")
    if normalize_text(source.get("is_kid")) == "1" and normalize_text(target.get("is_kid")) == "1":
        score += 0.08
        reasons.append("亲子")
    if normalize_text(source.get("is_night_tour")) == "1" and normalize_text(target.get("is_night_tour")) == "1":
        score += 0.08
        reasons.append("夜游")
    if normalize_text(target.get("sight_level")) == "5A":
        score += 0.08
        reasons.append("5A")
    elif normalize_text(target.get("sight_level")) == "4A":
        score += 0.05
        reasons.append("4A")
    source_text = compose_poi_text(source)
    target_text = compose_poi_text(target)
    for label, keywords in {
        "历史文化": ["历史", "建筑", "故居", "博物馆", "纪念馆", "古街", "文化"],
        "自然风光": ["自然", "山水", "赏花", "登高", "公园"],
        "城市地标": ["地标", "广场", "观景", "城市漫步"],
        "主题体验": ["主题乐园", "游乐", "沉浸", "体验"],
    }.items():
        if any(word in source_text for word in keywords) and any(word in target_text for word in keywords):
            score += 0.08
            reasons.append(label)
            break
    quality = clamp((safe_float(target.get("comment_score")) / 5.0) * 0.55 + (safe_float(target.get("heat_score")) / 10.0) * 0.25 + min(math.log1p(safe_int(target.get("comment_count"))) / 10.0, 0.20), 0.0, 1.0)
    score = clamp(score * 0.76 + quality * 0.24, 0.0, 1.0)
    return score, reasons[:5]


def quality_score_of(row: Dict[str, Any]) -> float:
    return clamp(
        (safe_float(row.get("comment_score")) / 5.0) * 0.42
        + (safe_float(row.get("heat_score")) / 10.0) * 0.33
        + min(math.log1p(safe_int(row.get("comment_count"))) / 10.0, 0.25),
        0.0,
        1.0,
    )


def candidate_rows_for_source(source: Dict[str, Any], strict_city: bool = True) -> List[Dict[str, Any]]:
    items = [enrich_poi_row(row) for row in load_clean_poi_records()]
    source_city = normalize_text(source.get("city_name"))
    source_province = normalize_text(source.get("province"))
    scoped = [row for row in items if normalize_text(row.get("city_name")) == source_city]
    if strict_city:
        return scoped
    if len(scoped) < 8 and source_province:
        scoped = [row for row in items if normalize_text(row.get("province")) == source_province]
    return scoped or items


def make_recommendation_row(
    source: Dict[str, Any],
    target: Dict[str, Any],
    algorithm: str,
    mode: str,
    rank: int,
    final_score: float,
    content_score: float,
    geo_score: float,
    rule_score: float,
    distance_km: float,
    shared_terms: List[str],
    reason_text: str,
) -> Dict[str, Any]:
    mode_name = next((item["name"] for item in recommendation_modes() if item["key"] == mode), mode)
    return {
        "source_poi_id": source.get("poi_id"),
        "source_poi_name": source.get("poi_name"),
        "source_city_name": source.get("city_name"),
        "source_province": source.get("province"),
        "mode": mode,
        "mode_name": mode_name,
        "algorithm": algorithm,
        "recommend_rank": rank,
        "target_poi_id": target.get("poi_id"),
        "target_poi_name": target.get("poi_name"),
        "target_city_name": target.get("city_name"),
        "target_region_name": target.get("region_name"),
        "target_price": target.get("price"),
        "target_comment_score": target.get("comment_score"),
        "target_comment_count": target.get("comment_count"),
        "target_heat_score": target.get("heat_score"),
        "target_distance_level": target.get("distance_level"),
        "content_score": round(content_score, 6),
        "geo_score": round(geo_score, 6),
        "rule_score": round(rule_score, 6),
        "behavior_score": 0.0,
        "quality_score": round(quality_score_of(target), 6),
        "final_score": round(final_score, 6),
        "distance_km": round(distance_km, 3),
        "shared_tags": "、".join(shared_terms[:6]),
        "reason_text": reason_text,
        "detail_url": target.get("detail_url"),
        "cover_image_url": target.get("cover_image_url"),
    }


def build_single_algorithm_recommendations_live(source_row: Dict[str, Any], algorithm: str, mode: str, limit: int) -> List[Dict[str, Any]]:
    source = enrich_poi_row(source_row)
    rows: List[Dict[str, Any]] = []
    for target in candidate_rows_for_source(source):
        if normalize_text(target.get("poi_id")) == normalize_text(source.get("poi_id")):
            continue
        content_score, shared_terms = content_similarity_score(source, target)
        geo_score, distance_km = geo_similarity_score(source, target)
        rule_score, rule_reasons = rule_preference_score(source, target)
        if algorithm == "content":
            final_score = clamp(content_score * 0.82 + quality_score_of(target) * 0.18, 0.0, 1.0)
            reason = "内容相似推荐；基于标签、区域、简介和景区等级匹配相似景点"
        elif algorithm == "geo":
            final_score = clamp(geo_score * 0.86 + rule_score * 0.08 + quality_score_of(target) * 0.06, 0.0, 1.0)
            reason = "地理邻近推荐；使用 Haversine 距离优先推荐附近可串游景点"
        else:
            final_score = clamp(rule_score * 0.82 + quality_score_of(target) * 0.18, 0.0, 1.0)
            reason = f"规则偏好推荐；命中{('、'.join(rule_reasons) if rule_reasons else '评分、热度、距离层级')}等规则"
        rows.append(
            make_recommendation_row(
                source,
                target,
                algorithm,
                mode,
                0,
                final_score,
                content_score,
                geo_score,
                rule_score,
                distance_km,
                shared_terms or rule_reasons,
                reason,
            )
        )
    rows.sort(key=lambda row: (row["final_score"], row["quality_score"], -row["distance_km"]), reverse=True)
    for idx, row in enumerate(rows[:limit], start=1):
        row["recommend_rank"] = idx
    return rows[:limit]


def build_hybrid_recommendations_live(source_row: Dict[str, Any], mode: str, limit: int) -> List[Dict[str, Any]]:
    source = enrich_poi_row(source_row)
    weights = next((item["weights"] for item in recommendation_modes() if item["key"] == mode), recommendation_modes()[0]["weights"])
    candidates: List[Dict[str, Any]] = []
    for target in candidate_rows_for_source(source):
        if normalize_text(target.get("poi_id")) == normalize_text(source.get("poi_id")):
            continue
        content_score, shared_terms = content_similarity_score(source, target)
        geo_score, distance_km = geo_similarity_score(source, target)
        rule_score, rule_reasons = rule_preference_score(source, target)
        quality_score = quality_score_of(target)
        final_score = clamp(
            geo_score * weights["geo"]
            + content_score * weights["content"]
            + rule_score * weights["rule"]
            + 0.0 * weights["behavior"]
            + quality_score * weights["quality"],
            0.0,
            1.0,
        )
        candidates.append(
            make_recommendation_row(
                source,
                target,
                "hybrid",
                mode,
                0,
                final_score,
                content_score,
                geo_score,
                rule_score,
                distance_km,
                shared_terms or rule_reasons,
                f"{next((item['name'] for item in recommendation_modes() if item['key'] == mode), mode)}；融合内容相似、地理距离和规则口碑综合推荐",
            )
        )
    candidates.sort(key=lambda row: (row["final_score"], row["quality_score"], row["content_score"]), reverse=True)
    for idx, row in enumerate(candidates[:limit], start=1):
        row["recommend_rank"] = idx
    return candidates[:limit]


def resolve_recommend_source_row(poi_name: str, province: str = "", city: str = "") -> Optional[Dict[str, Any]]:
    poi_name = normalize_text(poi_name)
    province = normalize_text(province)
    city = normalize_text(city)
    if not poi_name:
        return None

    location_data = load_recommend_lookup()
    candidate_rows: List[Dict[str, Any]] = []
    if province and city:
        candidate_rows = list(location_data.get("pois_by_city", {}).get(f"{province}||{city}", []))
    elif city:
        for key, rows in location_data.get("pois_by_city", {}).items():
            _, key_city = key.split("||", 1) if "||" in key else ("", key)
            if key_city == city:
                candidate_rows.extend(rows)
    elif province:
        for key, rows in location_data.get("pois_by_city", {}).items():
            if key.startswith(f"{province}||"):
                candidate_rows.extend(rows)

    if not candidate_rows:
        candidate_rows = load_clean_poi_records()

    def matches(row: Dict[str, Any]) -> bool:
        name = normalize_text(row.get("poi_name"))
        region = normalize_text(row.get("region_name"))
        return name == poi_name or poi_name in name or name in poi_name or poi_name in region

    exact = next((row for row in candidate_rows if normalize_text(row.get("poi_name")) == poi_name), None)
    if exact:
        return exact
    scoped = next((row for row in candidate_rows if matches(row)), None)
    if scoped:
        return scoped

    for row in load_clean_poi_records():
        if matches(row):
            return row
    return None


def _rank_by_keyword(items: List[Dict[str, Any]], keyword: str, text_keys: List[str], limit: int) -> List[Dict[str, Any]]:
    keyword = normalize_text(keyword).lower()
    if not keyword:
        return items[:limit]
    exact_name: List[Dict[str, Any]] = []
    exact: List[Dict[str, Any]] = []
    fuzzy: List[Dict[str, Any]] = []
    for item in items:
        primary = normalize_text(item.get(text_keys[0])).lower() if text_keys else ""
        if primary == keyword:
            exact_name.append(item)
            continue
        text = " ".join(normalize_text(item.get(key)) for key in text_keys).lower()
        if not text:
            continue
        if keyword in text:
            exact.append(item)
        elif any(token and token in text for token in keyword.split()):
            fuzzy.append(item)
    return (exact_name + exact + fuzzy)[:limit]


def fetch_recommendation_locations(query: Dict[str, List[str]]) -> Dict[str, Any]:
    data = load_recommend_lookup()
    province_keyword = normalize_text((query.get("province", [""])[0] or query.get("province_kw", [""])[0] or ""))
    city_keyword = normalize_text((query.get("city", [""])[0] or query.get("city_kw", [""])[0] or ""))
    poi_keyword = normalize_text((query.get("poi", [""])[0] or query.get("poi_kw", [""])[0] or ""))
    limit = max(1, min(safe_int((query.get("limit", ["20"])[0] or 20)), 50))

    province_items = [{"province": name} for name in data.get("provinces", [])]
    if province_keyword:
        province_items = [{"province": item["province"]} for item in _rank_by_keyword(province_items, province_keyword, ["province"], limit)]

    selected_province = normalize_text((query.get("selected_province", [""])[0] or ""))
    city_items: List[Dict[str, Any]] = []
    if selected_province:
        city_items = list(data.get("cities_by_province", {}).get(selected_province, []))
        if city_keyword:
            city_items = _rank_by_keyword(city_items, city_keyword, ["city_name", "province"], limit)
    elif city_keyword:
        for province, rows in data.get("cities_by_province", {}).items():
            for row in rows:
                city_items.append(row)
        city_items = _rank_by_keyword(city_items, city_keyword, ["city_name", "province"], limit)

    selected_city = normalize_text((query.get("selected_city", [""])[0] or ""))
    poi_items: List[Dict[str, Any]] = []
    if selected_province and selected_city:
        poi_items = list(data.get("pois_by_city", {}).get(f"{selected_province}||{selected_city}", []))
    elif selected_city:
        for key, rows in data.get("pois_by_city", {}).items():
            _, city = key.split("||", 1) if "||" in key else ("", key)
            if city == selected_city:
                poi_items.extend(rows)
    if poi_keyword:
        poi_items = _rank_by_keyword(poi_items, poi_keyword, ["poi_name", "region_name", "tag_text", "short_feature"], limit)
    else:
        poi_items = poi_items[:limit]

    return {
        "provinces": province_items[:limit],
        "cities": city_items[:limit],
        "pois": poi_items[:limit],
        "selected_province": selected_province,
        "selected_city": selected_city,
    }


def fetch_recommendation_gallery() -> Dict[str, Any]:
    cards = build_algorithm_default_recommendations("als", 18, "balanced")
    if not cards:
        rows = [row for row in load_personalized_hybrid_recommendations() if normalize_text(row.get("mode")) == "balanced"][:80]
        if not rows:
            rows = load_content_recommendations()[:80]
        cards = [enrich_recommendation_row(row) for row in rows]
    return {
        "cards": cards[:18],
        "source_options": fetch_recommendation_source_options(),
        "algorithms": [RECOMMEND_ALGORITHMS["als"], RECOMMEND_ALGORITHMS["hybrid"]],
        "modes": recommendation_modes(),
        "report": current_als_training_artifact().get("report", {}),
        "location_index": load_recommend_lookup(),
    }


def fetch_recommendations_als(query: Dict[str, List[str]]) -> Dict[str, Any]:
    user_id = safe_int((query.get("user_id", ["0"])[0] or 0))
    poi_name = normalize_text((query.get("poi_name", [""])[0] or ""))
    province = normalize_text((query.get("province", [""])[0] or ""))
    city = normalize_text((query.get("city", [""])[0] or query.get("city_name", [""])[0] or ""))
    mode = normalize_text((query.get("mode", ["balanced"])[0] or "balanced"))
    if mode not in {item["key"] for item in recommendation_modes()}:
        mode = "balanced"
    limit = max(1, min(safe_int((query.get("limit", ["8"])[0] or 8)), 20))

    source_row = resolve_recommend_source_row(poi_name, province, city) if poi_name else None
    selected_name = normalize_text(source_row.get("poi_name") if source_row else poi_name) or "ALS 个性推荐"
    matched, bundle = build_als_personalized_recommendations(user_id, source_row, province, city, mode, limit)
    fallback_message = ""
    if not matched:
        matched = build_algorithm_default_recommendations("als", limit, mode)
        if bundle.get("status") != "ok":
            fallback_message = "当前用户收藏和评论数据还不够，先展示 ALS 预热推荐结果。"
        else:
            fallback_message = "当前城市下可用的 ALS 候选较少，先展示系统预热推荐结果。"

    return build_response(
        True,
        {
            "matched_name": selected_name,
            "algorithm": RECOMMEND_ALGORITHMS["als"],
            "mode": next((item for item in recommendation_modes() if item["key"] == mode), recommendation_modes()[0]),
            "recommendations": [enrich_recommendation_row(row) for row in matched[:limit]],
            "source_options": fetch_recommendation_source_options(),
            "modes": recommendation_modes(),
            "report": bundle.get("report", current_als_training_artifact().get("report", {})),
            "fallback_message": fallback_message,
            "history_count": safe_int(bundle.get("history_count")),
        },
    )


def fetch_recommendations(query: Dict[str, List[str]]) -> Dict[str, Any]:
    poi_name = normalize_text((query.get("poi_name", [""])[0] or ""))
    province = normalize_text((query.get("province", [""])[0] or ""))
    city = normalize_text((query.get("city", [""])[0] or query.get("city_name", [""])[0] or ""))
    algorithm = "hybrid"
    mode = normalize_text((query.get("mode", ["balanced"])[0] or "balanced"))
    if mode not in {item["key"] for item in recommendation_modes()}:
        mode = "balanced"
    limit = max(1, min(safe_int((query.get("limit", ["8"])[0] or 8)), 20))
    if not poi_name:
        return build_response(
            True,
            {
                "matched_name": "算法推荐",
                "algorithm": RECOMMEND_ALGORITHMS["hybrid"],
                "mode": next((item for item in recommendation_modes() if item["key"] == mode), recommendation_modes()[0]),
                "recommendations": build_algorithm_default_recommendations("hybrid", limit, mode),
                "source_options": fetch_recommendation_source_options(),
                "modes": recommendation_modes(),
            },
        )

    source_row = resolve_recommend_source_row(poi_name, province, city)
    matched: List[Dict[str, Any]] = []
    if source_row:
        matched = build_hybrid_recommendations_live(source_row, mode, limit)
    matched.sort(key=lambda row: (safe_int(row.get("recommend_rank")), -safe_float(row.get("final_score") or row.get("recommend_score"))))
    if not matched:
        return build_response(False, {"query_name": poi_name, "source_options": fetch_recommendation_source_options()}, "未找到对应推荐源景点")
    return build_response(
        True,
        {
            "matched_name": normalize_text(matched[0].get("source_poi_name")) or normalize_text(source_row.get("poi_name") if source_row else "") or poi_name,
            "algorithm": RECOMMEND_ALGORITHMS["hybrid"],
            "mode": next((item for item in recommendation_modes() if item["key"] == mode), recommendation_modes()[0]),
            "recommendations": [enrich_recommendation_row(row) for row in matched[:limit]],
            "source_options": fetch_recommendation_source_options(),
            "modes": recommendation_modes(),
        },
    )


def build_algorithm_default_recommendations(algorithm: str, limit: int, mode: str = "balanced") -> List[Dict[str, Any]]:
    if algorithm == "als":
        picked = build_als_default_recommendations(limit)
        if picked:
            return picked
    rows = recommendation_rows_for_algorithm(algorithm)
    if algorithm == "hybrid":
        rows = [row for row in rows if normalize_text(row.get("mode")) == mode]
    picked: List[Dict[str, Any]] = []
    seen = set()
    for row in sorted(rows, key=lambda item: (-safe_float(item.get("final_score") or item.get("recommend_score") or item.get("content_score")), safe_int(item.get("recommend_rank")))):
        key = normalize_text(row.get("target_poi_id") or row.get("target_poi_name"))
        if not key or key in seen:
            continue
        seen.add(key)
        picked.append(enrich_recommendation_row(row))
        if len(picked) >= limit:
            break
    if picked:
        return picked
    return [enrich_poi_row(row) for row in fetch_table_rows("frontend_module_detail_hot_top20", limit=limit, order_by="heat_score DESC, comment_count DESC")]


def fetch_recommendations_v2(query: Dict[str, List[str]]) -> Dict[str, Any]:
    algorithm = normalize_text((query.get("algorithm", [""])[0] or ""))
    user_id = safe_int((query.get("user_id", ["0"])[0] or 0))
    limit = max(1, min(safe_int((query.get("limit", ["8"])[0] or 8)), 20))
    poi_name = normalize_text((query.get("poi_name", [""])[0] or ""))
    mode = normalize_text((query.get("mode", ["balanced"])[0] or "balanced"))
    if mode not in {item["key"] for item in recommendation_modes()}:
        mode = "balanced"
    if algorithm == "hybrid":
        return fetch_recommendations(query)
    if algorithm == "als":
        return fetch_recommendations_als(query)
    if user_id > 0:
        return fetch_recommendations_als(query)
    if poi_name:
        return fetch_recommendations(query)
    return build_response(
        True,
        {
            "matched_name": "算法推荐",
            "algorithm": RECOMMEND_ALGORITHMS["als"],
            "mode": next((item for item in recommendation_modes() if item["key"] == mode), recommendation_modes()[0]),
            "recommendations": build_algorithm_default_recommendations("als", limit, mode),
            "source_options": fetch_recommendation_source_options(),
            "modes": recommendation_modes(),
            "report": current_als_training_artifact().get("report", {}),
        },
    )


def build_flow_report_display(report: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(report.get("input_summary") or {})
    total = safe_int(summary.get("row_count") or summary.get("city_day_row_count"))
    full_train = safe_int(summary.get("full_train_row_count") or summary.get("train_row_count"))
    full_valid = safe_int(summary.get("full_valid_row_count"))
    full_test = safe_int(summary.get("full_test_row_count") or summary.get("test_row_count"))
    if total > 0 and full_train <= 0 and full_test <= 0:
        summary["full_train_row_count"] = int(round(total * 0.8))
        summary["full_test_row_count"] = total - summary["full_train_row_count"]
    else:
        summary["full_train_row_count"] = full_train
        summary["full_valid_row_count"] = full_valid
        summary["full_test_row_count"] = full_test
    if not summary.get("split_ratio"):
        summary["split_ratio"] = "按日期切分训练集 / 测试集"
    if not summary.get("split_note"):
        summary["split_note"] = "优先展示模型训练报告中的真实切分规模。"
    display = dict(report)
    display["input_summary"] = summary
    return display


def fetch_current_weather(query: Dict[str, List[str]]) -> Dict[str, Any]:
    lat = safe_float(query.get("lat", ["31.2304"])[0])
    lon = safe_float(query.get("lon", ["121.4737"])[0])
    amap_key = os.getenv("AMAP_WEB_KEY", "").strip()
    if amap_key:
        try:
            regeo_url = "https://restapi.amap.com/v3/geocode/regeo?" + urlencode(
                {"key": amap_key, "location": f"{lon},{lat}", "extensions": "base", "radius": 10000}
            )
            with urlopen(regeo_url, timeout=4) as resp:
                regeo = json.loads(resp.read().decode("utf-8"))
            component = ((regeo.get("regeocode") or {}).get("addressComponent") or {})
            city = component.get("city") or component.get("province") or "当前位置"
            adcode = component.get("adcode") or ""
            weather = {}
            if adcode:
                weather_url = "https://restapi.amap.com/v3/weather/weatherInfo?" + urlencode(
                    {"key": amap_key, "city": adcode, "extensions": "base"}
                )
                with urlopen(weather_url, timeout=4) as resp:
                    weather_data = json.loads(resp.read().decode("utf-8"))
                lives = weather_data.get("lives") or []
                weather = lives[0] if lives else {}
            return build_response(
                True,
                {
                    "temperature": safe_float(weather.get("temperature")) if weather else None,
                    "weather": weather.get("weather") if weather else "",
                    "wind_direction": weather.get("winddirection") if weather else "",
                    "wind_power": weather.get("windpower") if weather else "",
                    "city": city,
                    "adcode": adcode,
                    "location": f"{lat:.3f}, {lon:.3f} · {city}",
                    "source": "amap",
                },
            )
        except Exception:
            pass
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,wind_speed_10m"
    )
    try:
        with urlopen(url, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        current = data.get("current") or {}
        return build_response(
            True,
            {
                "temperature": current.get("temperature_2m"),
                "weather_code": current.get("weather_code"),
                "wind_speed": current.get("wind_speed_10m"),
                "city": "当前位置",
                "location": f"{lat:.3f}, {lon:.3f}",
            },
        )
    except Exception:
        return build_response(True, {"temperature": None, "weather_code": None, "wind_speed": None, "location": f"{lat:.3f}, {lon:.3f}", "fallback": True})


def fetch_frontend_modules_bundle() -> Dict[str, Any]:
    manifest = fetch_json_payload("frontend_module_manifest") or {}
    overview_payload = fetch_json_payload("frontend_module_home_overview") or {}
    filter_options = fetch_json_payload("frontend_module_filter_options") or {}
    detail_payload = fetch_json_payload("frontend_module_detail_rankings") or {}
    city_summary = normalize_city_summary_rows(fetch_table_rows("frontend_module_city_summary", order_by="poi_count DESC, comment_total DESC"))
    city_tag_summary = normalize_tag_summary_rows(fetch_table_rows("frontend_module_city_tag_summary", order_by="poi_count DESC, city_name ASC"))
    city_top_poi_rows = [enrich_poi_row(row) for row in fetch_table_rows("frontend_module_city_top_poi", order_by="city_name ASC, rank_no ASC")]
    city_top_poi_rows = [row for row in city_top_poi_rows if row.get("city_name") in CITY_TO_PROVINCE]
    for row in city_top_poi_rows:
        row["composite_score"] = poi_composite_score(row)
    home_sample_rows = [enrich_poi_row(row) for row in fetch_table_rows("frontend_module_filter_poi_base", order_by="heat_score DESC, comment_count DESC")]
    db_distance_distribution = normalize_home_distance_distribution(fetch_table_rows_safe("frontend_module_home_distance_distribution", order_by="poi_count DESC"))
    if not distance_distribution_complete(db_distance_distribution):
        db_distance_distribution = build_home_distance_distribution(home_sample_rows)
    return {
        "manifest": manifest,
        "home": {
            "cards": overview_payload.get("cards", {}),
            "heatmap_points": build_home_heatmap_points(city_summary),
            "price_distribution": fetch_table_rows("frontend_module_home_price_distribution", order_by="poi_count DESC"),
            "score_distribution": fetch_table_rows("frontend_module_home_score_distribution", order_by="poi_count DESC"),
            "distance_distribution": db_distance_distribution,
            "comment_score_distribution": fetch_table_rows_safe("frontend_module_home_comment_score_distribution", order_by="poi_count DESC") or build_home_comment_score_distribution(home_sample_rows),
            "tag_top20": fetch_table_rows("frontend_module_home_tag_top20", order_by="poi_count DESC"),
            "hot_poi_top10": [enrich_poi_row(row) for row in fetch_table_rows("frontend_module_home_hot_poi_top10", limit=10, order_by="heat_score DESC, comment_count DESC")],
        },
        "region_dashboard": {
            "province_summary": build_province_summary(city_summary),
            "city_summary": city_summary,
            "city_tag_summary": city_tag_summary,
            "city_top_poi": city_top_poi_rows,
            "province_top_poi": build_province_top_poi(city_top_poi_rows),
        },
        "filter_panel": {
            "options": filter_options,
            "sample_poi": home_sample_rows,
        },
        "detail_rankings": {
            "summary": detail_payload,
            "hot_top20": [enrich_poi_row(row) for row in fetch_table_rows("frontend_module_detail_hot_top20", limit=20, order_by="heat_score DESC, comment_count DESC")],
            "value_top20": [enrich_poi_row(row) for row in fetch_table_rows("frontend_module_detail_value_top20", limit=20, order_by="comment_score DESC, heat_score DESC, comment_count DESC, price ASC")],
            "night_top20": [enrich_poi_row(row) for row in fetch_table_rows("frontend_module_detail_night_top20", limit=20, order_by="heat_score DESC, comment_count DESC")],
            "family_top20": [enrich_poi_row(row) for row in fetch_table_rows("frontend_module_detail_family_top20", limit=20, order_by="heat_score DESC, comment_count DESC")],
            "free_top20": [enrich_poi_row(row) for row in fetch_table_rows("frontend_module_detail_free_top20", limit=20, order_by="heat_score DESC, comment_count DESC, comment_score DESC")],
        },
        "admin_dashboard": {
            "city_summary": fetch_table_rows("frontend_module_admin_city_summary", limit=30, order_by="poi_count DESC, comment_total DESC"),
            "region_summary": fetch_table_rows("frontend_module_admin_region_summary", limit=30, order_by="avg_heat DESC, comment_total DESC"),
            "tag_summary": fetch_table_rows("frontend_module_admin_tag_summary", limit=20, order_by="poi_count DESC"),
        },
        "recommendation": fetch_recommendation_gallery(),
    }


def fetch_flow_module_bundle() -> Dict[str, Any]:
    report = fetch_json_payload("flow_module_training_report") or {}
    future_rows = fetch_table_rows("flow_module_future_7day_forecast", order_by="forecast_date ASC, forecast_flow DESC")
    return {
        "report": build_flow_report_display(report),
        "forecast": {
            "future_7day": future_rows,
            "city_7day": fetch_city_forecast_summary(),
            "future_peak_top10": sorted(future_rows, key=lambda row: row.get("forecast_flow", 0), reverse=True)[:10],
            "test_top_error": fetch_table_rows("flow_module_test_predictions", limit=15, order_by="abs_error DESC"),
            "city_forecast_note": "城市未来7日曲线在景点预测汇总基础上，叠加了城市历史周内客流模式校准。",
        },
        "impact": {
            "weather_holiday_summary": fetch_table_rows("flow_module_weather_holiday_summary", order_by="avg_flow DESC"),
            "holiday_type_summary": fetch_table_rows("flow_module_holiday_type_summary", order_by="avg_flow DESC"),
            "city_impact_top20": fetch_table_rows("flow_module_city_holiday_weather_impact_top20", order_by="holiday_lift_ratio DESC, avg_flow DESC"),
        },
        "clusters": {
            "summary": fetch_table_rows("flow_module_city_cluster_summary", order_by="city_count DESC"),
            "profiles": fetch_table_rows("flow_module_city_cluster_profile", order_by="cluster_name ASC, avg_flow DESC"),
        },
    }


def fetch_user_profile(user_id: int) -> Dict[str, Any] | None:
    return query_one(
        """
        SELECT id, username, role, nickname, gender, age, city_name, phone, email,
               travel_preference, budget_level, avatar_url, created_at
        FROM travel_users WHERE id=%s
        """,
        (user_id,),
    )


def ensure_interaction_tables() -> None:
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS travel_users (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  username VARCHAR(64) NOT NULL UNIQUE,
                  password_hash VARCHAR(128) NOT NULL,
                  role VARCHAR(32) NOT NULL,
                  nickname VARCHAR(64) NULL,
                  gender VARCHAR(16) NULL,
                  age INT NULL,
                  city_name VARCHAR(64) NULL,
                  phone VARCHAR(64) NULL,
                  email VARCHAR(128) NULL,
                  travel_preference VARCHAR(64) NULL,
                  budget_level VARCHAR(64) NULL,
                  avatar_url TEXT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id)
                ) CHARACTER SET utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_behavior_profile (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  user_id BIGINT NOT NULL,
                  preference_tag VARCHAR(64) NOT NULL,
                  visit_count INT NOT NULL DEFAULT 0,
                  favorite_count INT NOT NULL DEFAULT 0,
                  avg_budget DOUBLE NOT NULL DEFAULT 0,
                  active_score DOUBLE NOT NULL DEFAULT 0,
                  segment_name VARCHAR(64) NOT NULL,
                  PRIMARY KEY (id),
                  UNIQUE KEY uniq_user_profile (user_id)
                ) CHARACTER SET utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_favorites (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  user_id BIGINT NOT NULL,
                  poi_id BIGINT NOT NULL,
                  poi_name VARCHAR(255) NOT NULL,
                  province VARCHAR(64) NULL,
                  city_name VARCHAR(64) NULL,
                  region_name VARCHAR(255) NULL,
                  cover_image_url TEXT NULL,
                  detail_url TEXT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  UNIQUE KEY uniq_user_poi (user_id, poi_id),
                  KEY idx_user (user_id),
                  KEY idx_poi (poi_id)
                ) CHARACTER SET utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_poi_comments (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  user_id BIGINT NOT NULL,
                  poi_id BIGINT NOT NULL,
                  poi_name VARCHAR(255) NOT NULL,
                  province VARCHAR(64) NULL,
                  city_name VARCHAR(64) NULL,
                  rating INT NOT NULL DEFAULT 5,
                  content TEXT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  KEY idx_poi (poi_id),
                  KEY idx_user (user_id),
                  KEY idx_city (city_name)
                ) CHARACTER SET utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS travel_plans (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  user_id BIGINT NOT NULL,
                  title VARCHAR(128) NOT NULL,
                  destination VARCHAR(128) NOT NULL,
                  start_date DATE NULL,
                  end_date DATE NULL,
                  budget DOUBLE NOT NULL DEFAULT 0,
                  note TEXT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  KEY idx_user_updated (user_id, updated_at)
                ) CHARACTER SET utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS travel_plan_items (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  plan_id BIGINT NOT NULL,
                  day_no INT NOT NULL DEFAULT 1,
                  item_time VARCHAR(16) NOT NULL,
                  item_type VARCHAR(32) NOT NULL,
                  title VARCHAR(255) NOT NULL,
                  location VARCHAR(255) NULL,
                  note TEXT NULL,
                  source VARCHAR(32) NOT NULL DEFAULT 'manual',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  KEY idx_plan_day_time (plan_id, day_no, item_time)
                ) CHARACTER SET utf8mb4
                """
            )
            try:
                cur.execute("ALTER TABLE user_poi_comments ADD COLUMN parent_id BIGINT NULL")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE user_poi_comments ADD KEY idx_parent (parent_id)")
            except Exception:
                pass


def login_user(query: Dict[str, List[str]]) -> Dict[str, Any]:
    username = normalize_text(query.get("username", [""])[0])
    password = normalize_text(query.get("password", [""])[0])
    role = normalize_text(query.get("role", [""])[0])
    row = query_one("SELECT * FROM travel_users WHERE username=%s", (username,))
    if not row or row.get("password_hash") != password_hash(password):
        return build_response(False, None, "账号或密码不正确")
    if role and row.get("role") != role:
        return build_response(False, None, "账号角色不匹配")
    return build_response(True, {"user": fetch_user_profile(safe_int(row.get("id")))})


def register_user(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    username = normalize_text(query.get("username", [""])[0])
    password = normalize_text(query.get("password", [""])[0])
    nickname = normalize_text(query.get("nickname", [username])[0]) or username
    gender = normalize_text(query.get("gender", [""])[0])
    age = safe_int(query.get("age", ["0"])[0])
    city_name = normalize_text(query.get("city_name", [""])[0])
    preference = normalize_text(query.get("travel_preference", ["综合兴趣"])[0]) or "综合兴趣"
    budget = normalize_text(query.get("budget_level", ["中等预算"])[0]) or "中等预算"
    if len(username) < 3 or len(password) < 6:
        return build_response(False, None, "账号至少 3 位，密码至少 6 位")
    if query_one("SELECT id FROM travel_users WHERE username=%s", (username,)):
        return build_response(False, None, "账号已存在")

    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO travel_users
                (username, password_hash, role, nickname, gender, age, city_name, travel_preference, budget_level, avatar_url)
                VALUES (%s,%s,'tourist',%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    username,
                    password_hash(password),
                    nickname,
                    gender,
                    age or None,
                    city_name,
                    preference,
                    budget,
                    f"https://api.dicebear.com/7.x/initials/svg?seed={quote(username)}",
                ),
            )
            user_id = cur.lastrowid
            cur.execute(
                """
                INSERT INTO user_behavior_profile
                (user_id, preference_tag, visit_count, favorite_count, avg_budget, active_score, segment_name)
                VALUES (%s,%s,0,0,%s,20,'新注册游客')
                """,
                (user_id, preference, {"低预算": 80, "中等预算": 220, "高预算": 520}.get(budget, 220)),
            )
    return build_response(True, {"user": fetch_user_profile(safe_int(user_id))}, "注册成功")


def create_admin_user(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    username = normalize_text(query.get("username", [""])[0])
    password = normalize_text(query.get("password", ["123456"])[0]) or "123456"
    role = normalize_text(query.get("role", ["tourist"])[0]) or "tourist"
    nickname = normalize_text(query.get("nickname", [username])[0]) or username
    city_name = normalize_text(query.get("city_name", [""])[0])
    preference = normalize_text(query.get("travel_preference", ["综合兴趣"])[0]) or "综合兴趣"
    if role not in {"tourist", "operator"}:
        role = "tourist"
    if len(username) < 3:
        return build_response(False, None, "账号至少 3 位")
    if query_one("SELECT id FROM travel_users WHERE username=%s", (username,)):
        return build_response(False, None, "账号已存在")
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO travel_users
                (username, password_hash, role, nickname, city_name, travel_preference, budget_level, avatar_url)
                VALUES (%s,%s,%s,%s,%s,%s,'中等预算',%s)
                """,
                (
                    username,
                    password_hash(password),
                    role,
                    nickname,
                    city_name,
                    preference,
                    f"https://api.dicebear.com/7.x/initials/svg?seed={quote(username)}",
                ),
            )
            user_id = cur.lastrowid
            cur.execute(
                """
                INSERT INTO user_behavior_profile
                (user_id, preference_tag, visit_count, favorite_count, avg_budget, active_score, segment_name)
                VALUES (%s,%s,0,0,220,20,'后台新增用户')
                """,
                (user_id, preference),
            )
    return fetch_admin_users()


def update_profile(query: Dict[str, List[str]]) -> Dict[str, Any]:
    user_id = safe_int(query.get("user_id", ["0"])[0])
    fields = ["nickname", "gender", "age", "city_name", "phone", "email", "travel_preference", "budget_level", "avatar_url"]
    assignments = []
    params: list[Any] = []
    for field in fields:
        if field in query:
            assignments.append(f"`{field}`=%s")
            params.append(unquote_plus(query[field][0]))
    if not user_id or not assignments:
        return build_response(False, None, "缺少用户或资料字段")
    params.append(user_id)
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE travel_users SET {', '.join(assignments)} WHERE id=%s", tuple(params))
    return build_response(True, {"user": fetch_user_profile(user_id)}, "资料已保存")


def update_profile_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    query = {key: [str(value)] for key, value in payload.items() if value is not None}
    return update_profile(query)


def fetch_favorites(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(query.get("user_id", ["0"])[0])
    rows = fetch_table_rows("user_favorites", order_by="created_at DESC", where_sql="user_id=%s", params=(user_id,))
    return build_response(True, [enrich_poi_row(row) for row in rows])


def add_favorite(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(query.get("user_id", ["0"])[0])
    poi_id = safe_int(query.get("poi_id", ["0"])[0])
    if not user_id or not poi_id:
        return build_response(False, None, "缺少用户或景点")
    poi = enrich_poi_row({"poi_id": poi_id, "poi_name": query.get("poi_name", [""])[0], "city_name": query.get("city_name", [""])[0]})
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT IGNORE INTO user_favorites
                (user_id, poi_id, poi_name, province, city_name, region_name, cover_image_url, detail_url)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    user_id,
                    poi_id,
                    poi.get("poi_name") or query.get("poi_name", [""])[0],
                    poi.get("province"),
                    poi.get("city_name") or query.get("city_name", [""])[0],
                    poi.get("region_name"),
                    poi.get("cover_image_url"),
                    poi.get("detail_url"),
                ),
            )
    return fetch_favorites({"user_id": [str(user_id)]})


def remove_favorite(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(query.get("user_id", ["0"])[0])
    poi_id = safe_int(query.get("poi_id", ["0"])[0])
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_favorites WHERE user_id=%s AND poi_id=%s", (user_id, poi_id))
    return fetch_favorites({"user_id": [str(user_id)]})


def add_comment(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(query.get("user_id", ["0"])[0])
    poi_id = safe_int(query.get("poi_id", ["0"])[0])
    rating = max(1, min(safe_int(query.get("rating", ["5"])[0]), 5))
    parent_id = safe_int(query.get("parent_id", ["0"])[0])
    content = normalize_text(query.get("content", [""])[0])
    if not user_id or not poi_id or not content:
        return build_response(False, None, "缺少用户、景点或评论内容")
    poi = enrich_poi_row({"poi_id": poi_id, "poi_name": query.get("poi_name", [""])[0], "city_name": query.get("city_name", [""])[0]})
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_poi_comments
                (user_id, poi_id, poi_name, province, city_name, rating, content, parent_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    user_id,
                    poi_id,
                    poi.get("poi_name") or query.get("poi_name", [""])[0],
                    poi.get("province"),
                    poi.get("city_name") or query.get("city_name", [""])[0],
                    rating,
                    content,
                    parent_id or None,
                ),
            )
            cur.execute(
                """
                INSERT INTO user_behavior_profile
                (user_id, preference_tag, visit_count, favorite_count, avg_budget, active_score, segment_name)
                VALUES (%s,%s,1,0,220,35,'评论互动型')
                ON DUPLICATE KEY UPDATE
                  visit_count=visit_count+1,
                  active_score=LEAST(active_score+3,100),
                  segment_name=IF(active_score>=70,'高活跃互动型','评论互动型')
                """,
                (user_id, (poi.get("tag_text") or "综合兴趣").split("|")[0].split(",")[0][:32]),
            )
    return fetch_comments({"poi_id": [str(poi_id)]})


def fetch_comments(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    poi_id = safe_int(query.get("poi_id", ["0"])[0])
    rows = query_all(
        """
        SELECT c.id, c.user_id, c.poi_id, c.poi_name, c.city_name, c.rating, c.content, c.parent_id, c.created_at,
               u.nickname, u.avatar_url, u.role
        FROM user_poi_comments c
        LEFT JOIN travel_users u ON c.user_id=u.id
        WHERE c.poi_id=%s
        ORDER BY COALESCE(c.parent_id, c.id) DESC, c.parent_id IS NOT NULL ASC, c.created_at ASC
        LIMIT 80
        """,
        (poi_id,),
    )
    return build_response(True, rows)


def fetch_user_comments(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(query.get("user_id", ["0"])[0])
    rows = query_all(
        """
        SELECT id, user_id, poi_id, poi_name, city_name, rating, content, created_at
        FROM user_poi_comments
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (user_id,),
    )
    return build_response(True, rows)


def parse_plan_date(value: Any) -> Optional[dt.date]:
    text = normalize_text(value)
    if not text:
        return None
    try:
        return dt.datetime.strptime(text[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def normalize_plan_time(value: Any, fallback: str = "09:00") -> str:
    text = normalize_text(value)
    if not text:
        return fallback
    if len(text) >= 5 and text[2] == ":":
        try:
            hour = max(0, min(int(text[:2]), 23))
            minute = max(0, min(int(text[3:5]), 59))
            return f"{hour:02d}:{minute:02d}"
        except Exception:
            return fallback
    if ":" in text:
        hour_text, minute_text = text.split(":", 1)
        try:
            hour = max(0, min(int(hour_text), 23))
            minute = max(0, min(int(minute_text[:2]), 59))
            return f"{hour:02d}:{minute:02d}"
        except Exception:
            return fallback
    return fallback


def calc_plan_days(start_date: Any, end_date: Any) -> int:
    start = parse_plan_date(start_date)
    end = parse_plan_date(end_date)
    if not start or not end:
        return 1
    return max((end - start).days + 1, 1)


def normalize_plan_row(row: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)
    data["item_count"] = safe_int(data.get("item_count"))
    data["budget"] = safe_float(data.get("budget"))
    data["total_days"] = calc_plan_days(data.get("start_date"), data.get("end_date"))
    if not data.get("title"):
        data["title"] = f"{normalize_text(data.get('destination')) or '我的旅行'}计划"
    return data


def fetch_plan_row(user_id: int, plan_id: int) -> Dict[str, Any] | None:
    row = query_one(
        """
        SELECT p.*,
               COUNT(i.id) AS item_count
        FROM travel_plans p
        LEFT JOIN travel_plan_items i ON p.id=i.plan_id
        WHERE p.user_id=%s AND p.id=%s
        GROUP BY p.id
        """,
        (user_id, plan_id),
    )
    return normalize_plan_row(row) if row else None


def fetch_user_plans(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(query.get("user_id", ["0"])[0])
    rows = query_all(
        """
        SELECT p.*,
               COUNT(i.id) AS item_count
        FROM travel_plans p
        LEFT JOIN travel_plan_items i ON p.id=i.plan_id
        WHERE p.user_id=%s
        GROUP BY p.id
        ORDER BY p.updated_at DESC, p.id DESC
        """,
        (user_id,),
    )
    return build_response(True, [normalize_plan_row(row) for row in rows])


def fetch_plan_detail(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(query.get("user_id", ["0"])[0])
    plan_id = safe_int(query.get("plan_id", ["0"])[0])
    if not user_id or not plan_id:
        return build_response(False, None, "缺少计划信息")
    plan = fetch_plan_row(user_id, plan_id)
    if not plan:
        return build_response(False, None, "未找到当前计划")
    items = query_all(
        """
        SELECT id, plan_id, day_no, item_time, item_type, title, location, note, source, created_at, updated_at
        FROM travel_plan_items
        WHERE plan_id=%s
        ORDER BY day_no ASC, item_time ASC, id ASC
        """,
        (plan_id,),
    )
    max_day = max([safe_int(row.get("day_no")) for row in items] + [safe_int(plan.get("total_days")) or 1])
    days = []
    for day_no in range(1, max_day + 1):
        day_items = [dict(row) for row in items if safe_int(row.get("day_no")) == day_no]
        days.append({"day_no": day_no, "items": day_items})
    return build_response(True, {"plan": plan, "items": items, "days": days})


def save_plan_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(payload.get("user_id"))
    plan_id = safe_int(payload.get("plan_id"))
    title = normalize_text(payload.get("title"))
    destination = normalize_text(payload.get("destination"))
    start_date = normalize_text(payload.get("start_date"))
    end_date = normalize_text(payload.get("end_date"))
    budget = safe_float(payload.get("budget"))
    note = normalize_text(payload.get("note"))
    if not user_id:
        return build_response(False, None, "缺少用户信息")
    if not destination and not title:
        return build_response(False, None, "请先填写目的地或计划名称")
    if not title:
        title = f"{destination or '我的旅行'}计划"
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            if plan_id:
                cur.execute("SELECT id FROM travel_plans WHERE id=%s AND user_id=%s", (plan_id, user_id))
                if not cur.fetchone():
                    return build_response(False, None, "计划不存在或无权限修改")
                cur.execute(
                    """
                    UPDATE travel_plans
                    SET title=%s, destination=%s, start_date=%s, end_date=%s, budget=%s, note=%s
                    WHERE id=%s AND user_id=%s
                    """,
                    (title, destination or title, start_date or None, end_date or None, budget, note or None, plan_id, user_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO travel_plans
                    (user_id, title, destination, start_date, end_date, budget, note)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (user_id, title, destination or title, start_date or None, end_date or None, budget, note or None),
                )
                plan_id = safe_int(cur.lastrowid)
    return fetch_plan_detail({"user_id": [str(user_id)], "plan_id": [str(plan_id)]})


def delete_plan_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(payload.get("user_id"))
    plan_id = safe_int(payload.get("plan_id"))
    if not user_id or not plan_id:
        return build_response(False, None, "缺少计划信息")
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM travel_plan_items WHERE plan_id=%s", (plan_id,))
            cur.execute("DELETE FROM travel_plans WHERE id=%s AND user_id=%s", (plan_id, user_id))
    return fetch_user_plans({"user_id": [str(user_id)]})


def save_plan_item_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(payload.get("user_id"))
    plan_id = safe_int(payload.get("plan_id"))
    item_id = safe_int(payload.get("item_id"))
    day_no = max(1, safe_int(payload.get("day_no")) or 1)
    item_time = normalize_plan_time(payload.get("item_time"))
    item_type = normalize_text(payload.get("item_type")) or "活动"
    title = normalize_text(payload.get("title"))
    location = normalize_text(payload.get("location"))
    note = normalize_text(payload.get("note"))
    source = normalize_text(payload.get("source")) or "manual"
    if not user_id or not plan_id or not title:
        return build_response(False, None, "请完善行程信息")
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM travel_plans WHERE id=%s AND user_id=%s", (plan_id, user_id))
            if not cur.fetchone():
                return build_response(False, None, "计划不存在或无权限修改")
            if item_id:
                cur.execute(
                    """
                    UPDATE travel_plan_items
                    SET day_no=%s, item_time=%s, item_type=%s, title=%s, location=%s, note=%s, source=%s
                    WHERE id=%s AND plan_id=%s
                    """,
                    (day_no, item_time, item_type, title, location or None, note or None, source, item_id, plan_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO travel_plan_items
                    (plan_id, day_no, item_time, item_type, title, location, note, source)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (plan_id, day_no, item_time, item_type, title, location or None, note or None, source),
                )
    return fetch_plan_detail({"user_id": [str(user_id)], "plan_id": [str(plan_id)]})


def delete_plan_item_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(payload.get("user_id"))
    plan_id = safe_int(payload.get("plan_id"))
    item_id = safe_int(payload.get("item_id"))
    if not user_id or not plan_id or not item_id:
        return build_response(False, None, "缺少行程信息")
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM travel_plans WHERE id=%s AND user_id=%s", (plan_id, user_id))
            if not cur.fetchone():
                return build_response(False, None, "\u8ba1\u5212\u4e0d\u5b58\u5728\u6216\u65e0\u6743\u9650\u4fee\u6539")
            cur.execute("DELETE FROM travel_plan_items WHERE id=%s AND plan_id=%s", (item_id, plan_id))
    return fetch_plan_detail({"user_id": [str(user_id)], "plan_id": [str(plan_id)]})


def ai_meal_time(label: str) -> str:
    mapping = {
        "早餐": "08:00",
        "午餐": "12:30",
        "晚餐": "18:30",
        "夜宵": "21:00",
    }
    return mapping.get(normalize_text(label), "12:00")


def build_plan_note(*parts: Any) -> str:
    return " / ".join([normalize_text(part) for part in parts if normalize_text(part)])


def import_ai_plan_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(payload.get("user_id"))
    plan_id = safe_int(payload.get("plan_id"))
    ai_plan = payload.get("ai_plan") or {}
    if not user_id or not plan_id:
        return build_response(False, None, "请先选择当前计划")
    local_plan = ai_plan.get("local_plan") or {}
    days = local_plan.get("days") or []
    if not days:
        return build_response(False, None, "当前没有可导入的 AI 行程")
    rows_to_insert: List[Tuple[Any, ...]] = []
    transport_slots = ["07:30", "10:30", "14:30", "18:30", "20:30"]
    for index, day in enumerate(days):
        day_no = max(1, safe_int(day.get("day")) or index + 1)
        for item in day.get("schedule", []):
            rows_to_insert.append(
                (
                    plan_id,
                    day_no,
                    normalize_plan_time(item.get("time"), "09:00"),
                    "景点",
                    normalize_text(item.get("poi_name") or item.get("title")) or "景点安排",
                    normalize_text(item.get("location")),
                    build_plan_note(item.get("stay"), item.get("price_text")),
                    "ai",
                )
            )
        for meal in day.get("meals", []):
            meal_label = normalize_text(meal.get("meal_type")) or "用餐"
            rows_to_insert.append(
                (
                    plan_id,
                    day_no,
                    ai_meal_time(meal_label),
                    "餐饮",
                    normalize_text(meal.get("name")) or meal_label,
                    normalize_text(meal.get("location")),
                    build_plan_note(meal_label, meal.get("price_text")),
                    "ai",
                )
            )
        hotel = day.get("hotel") or {}
        if isinstance(hotel, dict) and normalize_text(hotel.get("name")):
            rows_to_insert.append(
                (
                    plan_id,
                    day_no,
                    "21:00",
                    "住宿",
                    normalize_text(hotel.get("name")),
                    normalize_text(hotel.get("location")),
                    build_plan_note("住宿安排", hotel.get("price_text")),
                    "ai",
                )
            )
        for transport_index, item in enumerate(day.get("transport", [])):
            title = normalize_text(item.get("mode")) or "\u4ea4\u901a\u5b89\u6392"
            location = f"{normalize_text(item.get('from'))} -> {normalize_text(item.get('to'))}".strip(" ->")
            rows_to_insert.append(
                (
                    plan_id,
                    day_no,
                    transport_slots[min(transport_index, len(transport_slots) - 1)],
                    "\u4ea4\u901a",
                    title,
                    location,
                    build_plan_note(item.get("duration"), item.get("price_text")),
                    "ai",
                )
            )
    if not rows_to_insert:
        return build_response(False, None, "AI 行程没有可导入的内容")
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM travel_plans WHERE id=%s AND user_id=%s", (plan_id, user_id))
            if not cur.fetchone():
                return build_response(False, None, "\u8ba1\u5212\u4e0d\u5b58\u5728\u6216\u65e0\u6743\u9650\u4fee\u6539")
            cur.executemany(
                """
                INSERT INTO travel_plan_items
                (plan_id, day_no, item_time, item_type, title, location, note, source)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                rows_to_insert,
            )
    return fetch_plan_detail({"user_id": [str(user_id)], "plan_id": [str(plan_id)]})


def fetch_admin_comments() -> Dict[str, Any]:
    ensure_interaction_tables()
    rows = query_all(
        """
        SELECT c.id, c.parent_id, c.user_id, c.poi_id, c.poi_name, c.city_name, c.rating, c.content, c.created_at,
               u.username, u.nickname, u.role
        FROM user_poi_comments c
        LEFT JOIN travel_users u ON c.user_id=u.id
        ORDER BY c.created_at DESC
        LIMIT 120
        """
    )
    return build_response(True, rows)


@lru_cache(maxsize=16)
def _cached_scenic_news(cache_key: str) -> List[Dict[str, Any]]:
    keywords = [
        "华东 旅游 景区",
        "华东 景点 文旅",
        "景区 旅游 公告",
    ]
    all_items: List[Dict[str, Any]] = []
    for keyword in keywords:
        url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=12) as res:
            xml_bytes = res.read()
        root = ET.fromstring(xml_bytes)
        for item in root.findall("./channel/item")[:10]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            source = (item.findtext("source") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            desc = item.findtext("description") or ""
            desc = html.unescape(desc)
            desc = desc.replace("<br>", " ").replace("<br/>", " ").replace("&nbsp;", " ")
            desc = ET.fromstring(f"<root>{desc}</root>").itertext() if desc else []
            summary = " ".join([x.strip() for x in desc if str(x).strip()])[:120]
            if not title or not link:
                continue
            try:
                published_at = parsedate_to_datetime(pub_date).isoformat()
            except Exception:
                published_at = pub_date
            all_items.append({
                "title": title,
                "link": link,
                "source": source or "实时新闻",
                "published_at": published_at,
                "summary": summary,
            })
    unique: Dict[str, Dict[str, Any]] = {}
    for item in all_items:
        key = item["title"]
        if key not in unique:
            unique[key] = item
    rows = list(unique.values())
    rows.sort(key=lambda x: str(x.get("published_at", "")), reverse=True)
    return rows[:12]


def load_fallback_scenic_news() -> List[Dict[str, Any]]:
    if SCENIC_NEWS_FALLBACK_PATH.exists():
        try:
            with SCENIC_NEWS_FALLBACK_PATH.open("r", encoding="utf-8") as fp:
                rows = json.load(fp)
            if isinstance(rows, list) and rows:
                return rows
        except Exception:
            pass
    return list(SCENIC_NEWS_FALLBACK)


def fetch_scenic_news(query: Dict[str, List[str]]) -> Dict[str, Any]:
    topic = normalize_text(query.get("topic", ["华东 景区 旅游"])[0]) or "华东 景区 旅游"
    cache_key = f"{topic}:{__import__('datetime').datetime.now().strftime('%Y%m%d%H')}"
    try:
        rows = _cached_scenic_news(cache_key)
        if rows:
            return build_response(True, {"topic": topic, "items": rows, "updated_at": __import__('datetime').datetime.now().isoformat(), "mode": "live"})
        fallback_rows = load_fallback_scenic_news()
        return build_response(True, {
            "topic": topic,
            "items": fallback_rows,
            "updated_at": __import__('datetime').datetime.now().isoformat(),
            "mode": "fallback",
            "message": "实时新闻暂不可用，已切换为内置公告",
        })
    except Exception as exc:
        fallback_rows = load_fallback_scenic_news()
        return build_response(True, {
            "topic": topic,
            "items": fallback_rows,
            "updated_at": __import__('datetime').datetime.now().isoformat(),
            "mode": "fallback",
            "message": f"新闻抓取暂时不可用，已切换为内置公告: {exc}",
        })


def fetch_user_portrait() -> Dict[str, Any]:
    ensure_interaction_tables()
    segment_rows = query_all(
        """
        SELECT segment_name, COUNT(*) AS user_count, ROUND(AVG(active_score),1) AS avg_active_score,
               ROUND(AVG(avg_budget),1) AS avg_budget
        FROM user_behavior_profile GROUP BY segment_name ORDER BY user_count DESC
        """
    )
    preference_rows = query_all(
        """
        SELECT preference_tag, COUNT(*) AS user_count, ROUND(AVG(active_score),1) AS avg_active_score
        FROM user_behavior_profile GROUP BY preference_tag ORDER BY user_count DESC
        """
    )
    city_rows = query_all(
        """
        SELECT city_name, COUNT(*) AS user_count
        FROM travel_users WHERE role='tourist' GROUP BY city_name ORDER BY user_count DESC LIMIT 15
        """
    )
    age_rows = query_all(
        """
        SELECT
          CASE
            WHEN age < 23 THEN '18-22岁'
            WHEN age < 31 THEN '23-30岁'
            WHEN age < 41 THEN '31-40岁'
            ELSE '41岁以上'
          END AS age_group,
          COUNT(*) AS user_count
        FROM travel_users WHERE role='tourist' GROUP BY age_group ORDER BY user_count DESC
        """
    )
    comment_rows = query_all(
        """
        SELECT city_name, COUNT(*) AS comment_count, ROUND(AVG(rating),1) AS avg_rating
        FROM user_poi_comments
        GROUP BY city_name
        ORDER BY comment_count DESC
        LIMIT 12
        """
    )
    interaction_rows = query_all(
        """
        SELECT
          COUNT(*) AS comment_count,
          COUNT(DISTINCT user_id) AS comment_user_count,
          ROUND(AVG(rating),1) AS avg_rating
        FROM user_poi_comments
        """
    )
    comment_text_rows = query_all(
        """
        SELECT content FROM user_poi_comments
        WHERE content IS NOT NULL AND content <> ''
        ORDER BY created_at DESC
        LIMIT 300
        """
    )
    word_count: Dict[str, int] = {}
    stop_words = {"这个", "景点", "感觉", "非常", "比较", "还是", "可以", "我们", "适合", "旅游", "地方"}
    for row in preference_rows:
        word = normalize_text(row.get("preference_tag"))
        if word:
            word_count[word] = word_count.get(word, 0) + safe_int(row.get("user_count")) * 5
    for row in city_rows:
        word = normalize_text(row.get("city_name"))
        if word:
            word_count[word] = word_count.get(word, 0) + safe_int(row.get("user_count")) * 3
    for row in comment_text_rows:
        content = normalize_text(row.get("content"))
        for word in ["亲子", "夜游", "美食", "自然", "山水", "古镇", "博物馆", "拍照", "休闲", "人多", "排队", "下雨", "高性价比", "交通方便"]:
            if word in content:
                word_count[word] = word_count.get(word, 0) + 4
        for token in content.replace("，", " ").replace("。", " ").replace(",", " ").split():
            token = token.strip()[:12]
            if len(token) >= 2 and token not in stop_words:
                word_count[token] = word_count.get(token, 0) + 1
    word_cloud = [
        {"name": name, "value": value}
        for name, value in sorted(word_count.items(), key=lambda item: item[1], reverse=True)[:36]
    ]
    return {
        "segments": segment_rows,
        "preferences": preference_rows,
        "cities": city_rows,
        "ages": age_rows,
        "comment_cities": comment_rows,
        "word_cloud": word_cloud,
        "algorithm_notes": [
            {"name": "用户分层", "principle": "按照活跃度、收藏、评论和预算把游客划分为新注册、评论互动、高活跃等类型。"},
            {"name": "偏好画像", "principle": "从注册偏好、收藏景点标签和评论关键词中提取主题倾向，用于运营侧内容投放。"},
        ],
        "interaction": interaction_rows[0] if interaction_rows else {"comment_count": 0, "comment_user_count": 0, "avg_rating": 0},
    }


def fetch_admin_users() -> Dict[str, Any]:
    ensure_interaction_tables()
    rows = query_all(
        """
        SELECT
          u.id, u.username, u.role, u.nickname, u.gender, u.age, u.city_name,
          u.phone, u.email, u.travel_preference, u.budget_level, u.avatar_url, u.created_at,
          COALESCE(p.segment_name, '未分层') AS segment_name,
          COALESCE(p.active_score, 0) AS active_score,
          COUNT(DISTINCT f.id) AS favorite_count,
          COUNT(DISTINCT c.id) AS comment_count
        FROM travel_users u
        LEFT JOIN user_behavior_profile p ON u.id=p.user_id
        LEFT JOIN user_favorites f ON u.id=f.user_id
        LEFT JOIN user_poi_comments c ON u.id=c.user_id
        GROUP BY u.id, u.username, u.role, u.nickname, u.gender, u.age, u.city_name,
                 u.phone, u.email, u.travel_preference, u.budget_level, u.avatar_url,
                 u.created_at, p.segment_name, p.active_score
        ORDER BY u.created_at DESC, u.id DESC
        LIMIT 200
        """
    )
    return build_response(True, rows)


def update_admin_user(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(query.get("user_id", ["0"])[0])
    if not user_id:
        return build_response(False, None, "缺少用户编号")
    allowed_fields = ["nickname", "gender", "age", "city_name", "phone", "email", "travel_preference", "budget_level", "avatar_url"]
    assignments = []
    params: List[Any] = []
    for field in allowed_fields:
        if field in query:
            assignments.append(f"`{field}`=%s")
            params.append(unquote_plus(query[field][0]))
    if "password" in query and normalize_text(query["password"][0]):
        assignments.append("password_hash=%s")
        params.append(password_hash(normalize_text(query["password"][0])))
    if not assignments:
        return build_response(False, None, "没有需要保存的字段")
    params.append(user_id)
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE travel_users SET {', '.join(assignments)} WHERE id=%s", tuple(params))
    return fetch_admin_users()


def delete_admin_user(query: Dict[str, List[str]]) -> Dict[str, Any]:
    ensure_interaction_tables()
    user_id = safe_int(query.get("user_id", ["0"])[0])
    if not user_id:
        return build_response(False, None, "缺少用户编号")
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_favorites WHERE user_id=%s", (user_id,))
            cur.execute("DELETE FROM user_poi_comments WHERE user_id=%s", (user_id,))
            cur.execute("DELETE FROM user_behavior_profile WHERE user_id=%s", (user_id,))
            cur.execute("DELETE FROM travel_users WHERE id=%s AND role<>'operator'", (user_id,))
    return fetch_admin_users()


def fetch_city_forecast_summary() -> List[Dict[str, Any]]:
    try:
        rows = query_all("SELECT * FROM flow_module_city_7day_forecast ORDER BY city_name ASC, forecast_date ASC")
        return refine_city_forecast_rows(rows)
    except Exception:
        rows = query_all(
            """
            SELECT city_name, forecast_date, ROUND(SUM(forecast_flow),0) AS forecast_flow
            FROM flow_module_future_7day_forecast
            GROUP BY city_name, forecast_date
            ORDER BY city_name ASC, forecast_date ASC
            """
        )
        return refine_city_forecast_rows(rows)


@lru_cache(maxsize=1)
def load_city_weekday_profile() -> Dict[str, Dict[int, float]]:
    profiles: Dict[str, Dict[int, List[float]]] = {}
    if not FLOW_SIMULATED_PATH.exists():
        return {}
    with FLOW_SIMULATED_PATH.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            city = normalize_text(row.get("cityName"))
            weekday = safe_int(row.get("weekday"))
            flow = safe_float(row.get("flow"))
            if not city or weekday <= 0:
                continue
            bucket = profiles.setdefault(city, {}).setdefault(weekday, [0.0, 0.0])
            bucket[0] += flow
            bucket[1] += 1.0
    normalized: Dict[str, Dict[int, float]] = {}
    for city, weekday_rows in profiles.items():
        means = {weekday: (total / count if count else 0.0) for weekday, (total, count) in weekday_rows.items()}
        base = sum(means.values()) / max(len(means), 1)
        if base <= 0:
            continue
        normalized[city] = {weekday: (value / base) for weekday, value in means.items() if value > 0}
    return normalized


def refine_city_forecast_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return rows
    profiles = load_city_weekday_profile()
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(normalize_text(row.get("city_name")), []).append(dict(row))

    refined: List[Dict[str, Any]] = []
    for city, city_rows in grouped.items():
        ordered = sorted(city_rows, key=lambda item: normalize_text(item.get("forecast_date")))
        raw_values = [safe_float(item.get("forecast_flow")) for item in ordered]
        if not raw_values:
            continue
        city_profile = profiles.get(city) or {}
        profile_weights = [city_profile.get(safe_int(item.get("weekday")), 1.0) for item in ordered]
        if any(weight <= 0 for weight in profile_weights):
            profile_weights = [1.0 for _ in ordered]
        avg_profile = sum(profile_weights) / max(len(profile_weights), 1)
        profile_weights = [weight / avg_profile for weight in profile_weights]
        mean_flow = sum(raw_values) / max(len(raw_values), 1)
        adjusted_values = [max(0.0, raw * 0.58 + mean_flow * weight * 0.42) for raw, weight in zip(raw_values, profile_weights)]
        scale = (sum(raw_values) / max(sum(adjusted_values), 1.0)) if sum(adjusted_values) > 0 else 1.0
        for row, value, weight in zip(ordered, adjusted_values, profile_weights):
            refined_row = dict(row)
            refined_row["forecast_flow"] = int(round(value * scale))
            refined_row["city_profile_weight"] = round(weight, 4)
            refined.append(refined_row)
    return sorted(refined, key=lambda item: (normalize_text(item.get("city_name")), normalize_text(item.get("forecast_date"))))


def app_router(path: str) -> Dict[str, Any]:
    parsed = urlparse(path)
    route = parsed.path
    query = parse_qs(parsed.query)

    if not db_available():
        return build_response(False, None, "数据库当前不可用")

    if route == "/":
        return build_response(True, {"project": "华东旅游数据分析、预测与推荐系统", "entry": "/app/modules"})
    if route == "/api/frontend-modules":
        return build_response(True, fetch_frontend_modules_bundle())
    if route == "/api/flow-module":
        return build_response(True, fetch_flow_module_bundle())
    if route == "/api/recommendation-gallery":
        return build_response(True, fetch_recommendation_gallery())
    if route == "/api/recommend-locations":
        return build_response(True, fetch_recommendation_locations(query))
    if route == "/api/recommendations":
        return fetch_recommendations_v2(query)
    if route == "/api/weather/current":
        return fetch_current_weather(query)
    if route == "/api/home-news":
        return fetch_scenic_news(query)
    if route == "/api/config":
        return build_response(
            True,
            {
                "amap_key": os.getenv("AMAP_WEB_KEY", ""),
                "baidu_ak": os.getenv("BAIDU_MAP_AK", ""),
                "llm_enabled": bool(os.getenv("LLM_API_KEY") and os.getenv("LLM_BASE_URL")),
            },
        )
    if route == "/api/poi/preview":
        try:
            return build_response(True, build_poi_preview_payload(query))
        except Exception as exc:
            return build_response(False, None, str(exc))
    if route == "/api/guide-options":
        return build_response(True, fetch_guide_options())
    if route == "/api/guide-plan":
        return build_response(True, build_ai_plan(query))
    if route == "/api/map-pois":
        city = normalize_text(query.get("city", [""])[0])
        theme = normalize_text(query.get("theme", [""])[0])
        limit = max(1, min(safe_int(query.get("limit", ["30"])[0]), 80))
        return build_response(True, related_map_pois(city, theme, limit))
    if route == "/api/auth/login":
        return login_user(query)
    if route == "/api/auth/register":
        return register_user(query)
    if route == "/api/user/profile":
        return build_response(True, {"user": fetch_user_profile(safe_int(query.get("user_id", ["0"])[0]))})
    if route == "/api/user/update-profile":
        return update_profile(query)
    if route == "/api/user/favorites":
        return fetch_favorites(query)
    if route == "/api/user/plans":
        return fetch_user_plans(query)
    if route == "/api/user/plan-detail":
        return fetch_plan_detail(query)
    if route == "/api/user/add-favorite":
        return add_favorite(query)
    if route == "/api/user/remove-favorite":
        return remove_favorite(query)
    if route == "/api/user/add-comment":
        return add_comment(query)
    if route == "/api/user/comments":
        return fetch_comments(query)
    if route == "/api/user/my-comments":
        return fetch_user_comments(query)
    if route == "/api/admin/user-portrait":
        return build_response(True, fetch_user_portrait())
    if route == "/api/admin/users":
        return fetch_admin_users()
    if route == "/api/admin/comments":
        return fetch_admin_comments()
    if route == "/api/admin/create-user":
        return create_admin_user(query)
    if route == "/api/admin/update-user":
        return update_admin_user(query)
    if route == "/api/admin/delete-user":
        return delete_admin_user(query)
    if route == "/api/flow/report":
        return build_response(True, fetch_json_payload("flow_module_training_report") or {})
    if route == "/api/city-stats":
        return build_response(True, fetch_table_rows("frontend_module_city_summary", order_by="poi_count DESC, comment_total DESC"))
    if route == "/api/hot-poi-top100":
        rows = fetch_table_rows("frontend_module_detail_hot_top20", limit=20, order_by="heat_score DESC, comment_count DESC")
        return build_response(True, [enrich_poi_row(row) for row in rows])
    return build_response(False, None, f"未找到接口: {route}")


def app_router_payload(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    parsed = urlparse(path)
    route = parsed.path
    if not db_available():
        return build_response(False, None, "数据库当前不可用")
    if route == "/api/user/update-profile-json":
        return update_profile_payload(payload)
    if route == "/api/user/plan/save-json":
        return save_plan_payload(payload)
    if route == "/api/user/plan/delete-json":
        return delete_plan_payload(payload)
    if route == "/api/user/plan/item/save-json":
        return save_plan_item_payload(payload)
    if route == "/api/user/plan/item/delete-json":
        return delete_plan_item_payload(payload)
    if route == "/api/user/plan/import-ai-json":
        return import_ai_plan_payload(payload)
    return build_response(False, None, f"未找到接口: {route}")


def create_fastapi_app():
    try:
        from fastapi import FastAPI
    except Exception:
        return None

    app = FastAPI(title="Travel Ctrip Analysis API", version="4.0.0")

    @app.get("/{full_path:path}")
    def catch_all(full_path: str) -> Dict[str, Any]:
        query = ""
        return app_router("/" + full_path + (("?" + query) if query else ""))

    return app


app = create_fastapi_app()


if __name__ == "__main__":
    import sys

    result = app_router(sys.argv[1] if len(sys.argv) > 1 else "/")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
