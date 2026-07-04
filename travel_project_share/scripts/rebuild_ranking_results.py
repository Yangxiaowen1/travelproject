from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parents[1]
FILTER_BASE_PATH = BASE_DIR / "data" / "module_results" / "03_scenic_filter" / "filter_poi_base.csv"
TARGET_DIRS = [
    BASE_DIR / "data" / "module_results" / "04_scenic_ranking",
    BASE_DIR / "data" / "frontend_modules" / "04_scenic_detail",
]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if not text:
            return default
        return float(text)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        text = str(value).strip()
        if not text:
            return default
        return int(float(text))
    except Exception:
        return default


def read_rows() -> List[Dict[str, Any]]:
    with FILTER_BASE_PATH.open("r", encoding="utf-8-sig", newline="") as fp:
        return list(csv.DictReader(fp))


def pick_fields(row: Dict[str, Any], ranking_score: float | None = None) -> Dict[str, Any]:
    payload = {
        "poi_id": safe_int(row.get("poi_id")),
        "poi_name": str(row.get("poi_name", "")).strip(),
        "city_name": str(row.get("city_name", "")).strip(),
        "region_name": str(row.get("region_name", "")).strip(),
        "price": safe_float(row.get("price")),
        "comment_score": safe_float(row.get("comment_score")),
        "comment_count": safe_int(row.get("comment_count")),
        "heat_score": safe_float(row.get("heat_score")),
        "sight_level": str(row.get("sight_level", "")).strip(),
        "tag_text": str(row.get("tag_text", "")).strip(),
        "short_feature": str(row.get("short_feature", "")).strip(),
        "latitude": safe_float(row.get("latitude")),
        "longitude": safe_float(row.get("longitude")),
    }
    if ranking_score is not None:
        payload["ranking_score"] = round(ranking_score, 6)
    return payload


def build_value_score(row: Dict[str, Any]) -> float:
    comment_score = safe_float(row.get("comment_score"))
    heat_score = safe_float(row.get("heat_score"))
    comment_count = safe_int(row.get("comment_count"))
    price = safe_float(row.get("price"))
    return (
        comment_score * 0.45
        + heat_score * 0.35
        + min(comment_count / 10000, 1.0) * 10 * 0.2
        - min(price / 500, 1.0) * 2
    )


def build_rankings(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    hot_rows = sorted(
        rows,
        key=lambda row: (
            safe_float(row.get("heat_score")),
            safe_int(row.get("comment_count")),
            safe_float(row.get("comment_score")),
        ),
        reverse=True,
    )
    free_rows = sorted(
        [row for row in rows if safe_int(row.get("is_free")) == 1],
        key=lambda row: (
            safe_float(row.get("heat_score")),
            safe_int(row.get("comment_count")),
            safe_float(row.get("comment_score")),
        ),
        reverse=True,
    )
    family_rows = sorted(
        [row for row in rows if safe_int(row.get("is_kid")) == 1],
        key=lambda row: (
            safe_float(row.get("heat_score")),
            safe_int(row.get("comment_count")),
            safe_float(row.get("comment_score")),
        ),
        reverse=True,
    )
    night_rows = sorted(
        [row for row in rows if safe_int(row.get("is_night_tour")) == 1],
        key=lambda row: (
            safe_float(row.get("heat_score")),
            safe_int(row.get("comment_count")),
            safe_float(row.get("comment_score")),
        ),
        reverse=True,
    )
    value_rows = sorted(
        rows,
        key=lambda row: (
            build_value_score(row),
            safe_float(row.get("heat_score")),
            safe_int(row.get("comment_count")),
            safe_float(row.get("comment_score")),
        ),
        reverse=True,
    )
    return {
        "hot_top20": [pick_fields(row) for row in hot_rows[:20]],
        "free_top20": [pick_fields(row) for row in free_rows[:20]],
        "family_top20": [pick_fields(row) for row in family_rows[:20]],
        "night_top20": [pick_fields(row) for row in night_rows[:20]],
        "value_top20": [pick_fields(row, build_value_score(row)) for row in value_rows[:20]],
    }


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    rows = read_rows()
    rankings = build_rankings(rows)
    for target_dir in TARGET_DIRS:
        for name, items in rankings.items():
            write_csv(target_dir / f"{name}.csv", items)
        write_json(target_dir / "detail_rankings.json", rankings)
    print(json.dumps({"updated_dirs": [str(path) for path in TARGET_DIRS], "row_count": len(rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
