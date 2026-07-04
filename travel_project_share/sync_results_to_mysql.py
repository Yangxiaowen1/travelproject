"""
【⚠️ 警示：仅为一键演示部署使用】
本模块会强制删除（DROP）并重建数据库表以覆盖最新数据，存在严重的数据破坏风险。
严禁在生产环境或包含重要业务数据的数据库中运行！仅供项目一键演示部署与初始化体验。
"""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pymysql


BASE_DIR = Path(__file__).resolve().parent
MODULE_RESULT_DIR = BASE_DIR / "data" / "module_results"
FRONTEND_HOME_DIR = MODULE_RESULT_DIR / "01_home_overview"
CITY_PROVINCE_DIR = MODULE_RESULT_DIR / "02_city_province_dashboard"
FILTER_DIR = MODULE_RESULT_DIR / "03_scenic_filter"
RANKING_DIR = MODULE_RESULT_DIR / "04_scenic_ranking"
OPERATOR_DIR = MODULE_RESULT_DIR / "05_operator_dashboard"
FLOW_DIR = MODULE_RESULT_DIR / "06_flow_forecast"

DB_CONFIG = {
    "host": os.getenv("TRAVEL_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("TRAVEL_DB_PORT", "3306")),
    "user": os.getenv("TRAVEL_DB_USER", "root"),
    "password": os.getenv("TRAVEL_DB_PASSWORD", ""),
    "database": os.getenv("TRAVEL_DB_NAME", "travel_ctrip"),
    "charset": os.getenv("TRAVEL_DB_CHARSET", "utf8mb4"),
    "autocommit": True,
}


TABLE_MAP = {
    "frontend_module_home_hot_poi_top10": FRONTEND_HOME_DIR / "home_hot_poi_top10.csv",
    "frontend_module_home_price_distribution": FRONTEND_HOME_DIR / "home_price_distribution.csv",
    "frontend_module_home_score_distribution": FRONTEND_HOME_DIR / "home_score_distribution.csv",
    "frontend_module_home_distance_distribution": FRONTEND_HOME_DIR / "home_distance_distribution.csv",
    "frontend_module_home_comment_score_distribution": FRONTEND_HOME_DIR / "home_comment_score_distribution.csv",
    "frontend_module_home_tag_top20": FRONTEND_HOME_DIR / "home_tag_top20.csv",
    "frontend_module_city_summary": CITY_PROVINCE_DIR / "city_summary.csv",
    "frontend_module_city_tag_summary": CITY_PROVINCE_DIR / "city_tag_summary.csv",
    "frontend_module_city_top_poi": CITY_PROVINCE_DIR / "city_top_poi.csv",
    "frontend_module_filter_poi_base": FILTER_DIR / "filter_poi_base.csv",
    "frontend_module_detail_family_top20": RANKING_DIR / "family_top20.csv",
    "frontend_module_detail_free_top20": RANKING_DIR / "free_top20.csv",
    "frontend_module_detail_hot_top20": RANKING_DIR / "hot_top20.csv",
    "frontend_module_detail_night_top20": RANKING_DIR / "night_top20.csv",
    "frontend_module_detail_value_top20": RANKING_DIR / "value_top20.csv",
    "frontend_module_admin_city_summary": OPERATOR_DIR / "admin_city_summary.csv",
    "frontend_module_admin_region_summary": OPERATOR_DIR / "admin_region_summary.csv",
    "frontend_module_admin_tag_summary": OPERATOR_DIR / "admin_tag_summary.csv",
    "flow_module_test_predictions": FLOW_DIR / "flow_test_predictions.csv",
    "flow_module_future_7day_forecast": FLOW_DIR / "flow_future_7day_forecast.csv",
    "flow_module_city_7day_forecast": FLOW_DIR / "flow_city_7day_forecast.csv",
    "flow_module_weather_holiday_summary": FLOW_DIR / "weather_holiday_summary.csv",
    "flow_module_holiday_type_summary": FLOW_DIR / "holiday_type_summary.csv",
    "flow_module_city_holiday_weather_impact_top20": FLOW_DIR / "city_holiday_weather_impact_top20.csv",
    "flow_module_city_cluster_profile": FLOW_DIR / "city_cluster_profile.csv",
    "flow_module_city_cluster_summary": FLOW_DIR / "city_cluster_summary.csv",
}


JSON_MAP = {
    "frontend_module_home_overview": FRONTEND_HOME_DIR / "home_overview.json",
    "frontend_module_filter_options": FILTER_DIR / "filter_options.json",
    "frontend_module_detail_rankings": RANKING_DIR / "detail_rankings.json",
    "frontend_module_manifest": MODULE_RESULT_DIR / "module_manifest.json",
    "flow_module_training_report": FLOW_DIR / "flow_training_report.json",
}


def sanitize(name: str) -> str:
    clean = re.sub(r"[^0-9a-zA-Z_]+", "_", name.strip())
    clean = clean.strip("_")
    if not clean:
        clean = "col"
    return clean.lower()


def infer_column_type(values: List[str]) -> str:
    non_empty = [str(v).strip() for v in values if str(v).strip() != ""]
    if not non_empty:
        return "TEXT"

    is_int = True
    is_float = True
    max_len = 0
    for value in non_empty:
        max_len = max(max_len, len(value))
        normalized = value.strip()
        if not re.fullmatch(r"[+-]?\d+", normalized):
            is_int = False
        try:
            float(normalized)
        except Exception:
            is_float = False

    if is_int:
        return "BIGINT"
    if is_float:
        return "DOUBLE"
    if max_len <= 255:
        return "VARCHAR(255)"
    if max_len <= 2000:
        return "TEXT"
    return "LONGTEXT"


def read_csv_rows(path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def connect():
    return pymysql.connect(**DB_CONFIG)


def ensure_database() -> None:
    conn = pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        charset=DB_CONFIG["charset"],
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE IF NOT EXISTS travel_ctrip CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
    finally:
        conn.close()


def sync_csv_table(conn, table_name: str, path: Path) -> Dict[str, Any]:
    fieldnames, rows = read_csv_rows(path)
    columns = [sanitize(name) for name in fieldnames]
    value_map = {sanitize(src): [row.get(src, "") for row in rows] for src in fieldnames}
    column_defs = ", ".join(f"`{col}` {infer_column_type(value_map[col])} NULL" for col in columns)

    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        cur.execute(f"CREATE TABLE `{table_name}` ({column_defs}) CHARACTER SET utf8mb4")
        if rows:
            placeholders = ", ".join(["%s"] * len(columns))
            col_sql = ", ".join(f"`{col}`" for col in columns)
            sql = f"INSERT INTO `{table_name}` ({col_sql}) VALUES ({placeholders})"
            data = [tuple(row.get(src, None) for src in fieldnames) for row in rows]
            cur.executemany(sql, data)
    return {"table_name": table_name, "row_count": len(rows), "source_file": str(path)}


def sync_json_table(conn, table_name: str, path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        cur.execute(
            f"""
            CREATE TABLE `{table_name}` (
              `id` BIGINT NOT NULL AUTO_INCREMENT,
              `payload_json` LONGTEXT NULL,
              PRIMARY KEY (`id`)
            ) CHARACTER SET utf8mb4
            """
        )
        cur.execute(f"INSERT INTO `{table_name}` (`payload_json`) VALUES (%s)", (json.dumps(payload, ensure_ascii=False),))
    return {"table_name": table_name, "row_count": 1, "source_file": str(path)}


def main() -> None:
    ensure_database()
    conn = connect()
    results: List[Dict[str, Any]] = []
    try:
        for table_name, path in TABLE_MAP.items():
            if path.exists():
                results.append(sync_csv_table(conn, table_name, path))
        for table_name, path in JSON_MAP.items():
            if path.exists():
                results.append(sync_json_table(conn, table_name, path))
    finally:
        conn.close()

    print(json.dumps({"synced_tables": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
