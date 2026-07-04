from __future__ import annotations

import shutil
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
TARGET_DIR = DATA_DIR / "module_results"

COPY_PLAN = {
    DATA_DIR / "frontend_modules" / "01_tourist_home": TARGET_DIR / "01_home_overview",
    DATA_DIR / "frontend_modules" / "02_city_dashboard": TARGET_DIR / "02_city_province_dashboard",
    DATA_DIR / "frontend_modules" / "03_filter_panel": TARGET_DIR / "03_scenic_filter",
    DATA_DIR / "frontend_modules" / "04_scenic_detail": TARGET_DIR / "04_scenic_ranking",
    DATA_DIR / "frontend_modules" / "05_admin_dashboard": TARGET_DIR / "05_operator_dashboard",
    DATA_DIR / "flow_module": TARGET_DIR / "06_flow_forecast",
    DATA_DIR / "recommend": TARGET_DIR / "07_recommendation",
}

SINGLE_FILES = {
    DATA_DIR / "frontend_modules" / "module_manifest.json": TARGET_DIR / "module_manifest.json",
}


def replace_directory(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main() -> None:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    for src, dst in COPY_PLAN.items():
        replace_directory(src, dst)
    for src, dst in SINGLE_FILES.items():
        copy_file(src, dst)
    print(f"module_results refreshed -> {TARGET_DIR}")


if __name__ == "__main__":
    main()
