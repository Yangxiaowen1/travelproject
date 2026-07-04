from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from urllib.parse import quote, urlencode


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CLEAN_PATH = DATA_DIR / "clean" / "cleaned_with_standard_feature.csv"
OUTPUT_DIR = DATA_DIR / "module_results" / "08_poi_geo_preview"
CSV_PATH = OUTPUT_DIR / "poi_geo_preview.csv"
JSON_PATH = OUTPUT_DIR / "poi_geo_preview.json"
SUMMARY_PATH = OUTPUT_DIR / "poi_geo_preview_summary.json"
ENV_PATH = BASE_DIR / ".env"


def load_env() -> None:
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def normalize_text(value: object) -> str:
    return str(value or "").strip()


def safe_float(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def split_tags(value: str) -> list[str]:
    text = normalize_text(value).replace("[", "").replace("]", "").replace("'", "")
    return [item.strip() for item in text.split(",") if item.strip()]


def build_amap_static_url(row: dict[str, object], amap_key: str) -> str:
    if not amap_key:
        return ""
    lat = safe_float(row.get("latitude"))
    lon = safe_float(row.get("longitude"))
    label = normalize_text(row.get("poiName"))[:6] or "景点"
    params = {
        "key": amap_key,
        "location": f"{lon:.6f},{lat:.6f}",
        "zoom": "15",
        "size": "900*520",
        "scale": "2",
        "traffic": "0",
        "markers": f"mid,0x4E8D63,{quote(label)}:{lon:.6f},{lat:.6f}",
    }
    return "https://restapi.amap.com/v3/staticmap?" + urlencode(params, safe=",:*")


def build_preview_row(row: dict[str, object], amap_key: str) -> dict[str, object]:
    tags = split_tags(normalize_text(row.get("tagNames")))
    return {
        "poi_id": normalize_text(row.get("poiId")),
        "poi_name": normalize_text(row.get("poiName")),
        "province": normalize_text(row.get("province")),
        "city_name": normalize_text(row.get("cityName")),
        "region_name": normalize_text(row.get("regionName")),
        "latitude": safe_float(row.get("latitude")),
        "longitude": safe_float(row.get("longitude")),
        "tag_text": " | ".join(tags[:3]),
        "preview_mode": "map_heat_fallback",
        "preview_title": f"{normalize_text(row.get('poiName'))} 空间预览",
        "preview_image_url": build_amap_static_url(row, amap_key),
        "cover_image_url": normalize_text(row.get("coverImageUrl")),
        "detail_url": normalize_text(row.get("detailUrl")),
    }


def main() -> None:
    load_env()
    amap_key = os.getenv("AMAP_WEB_KEY", "").strip()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    with CLEAN_PATH.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            lat = safe_float(row.get("latitude"))
            lon = safe_float(row.get("longitude"))
            if not lat or not lon:
                continue
            rows.append(build_preview_row(row, amap_key))

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    JSON_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "source_file": str(CLEAN_PATH),
                "output_csv": str(CSV_PATH),
                "output_json": str(JSON_PATH),
                "preview_mode": "map_heat_fallback",
                "row_count": len(rows),
                "amap_key_loaded": bool(amap_key),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Generated {len(rows)} preview rows -> {CSV_PATH}")


if __name__ == "__main__":
    main()
