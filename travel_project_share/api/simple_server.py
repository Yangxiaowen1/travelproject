from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode

import uvicorn
from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles


HOST = "127.0.0.1"
PORT = 8000
BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"


def load_env_file() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()

try:
    from . import main as core
except ImportError:
    import main as core  # type: ignore[no-redef]


def json_response(payload: Dict[str, Any], status: int | None = None) -> Response:
    body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    final_status = status if status is not None else (200 if payload.get("success") else 404)
    return Response(content=body, media_type="application/json; charset=utf-8", status_code=final_status)


def api_response(payload: Dict[str, Any], status: int | None = None) -> Response:
    return json_response(payload, status=status)


def get_frontend_file(filename: str) -> Path:
    file_path = FRONTEND_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"页面文件不存在: {filename}")
    return file_path


def get_query_dict(request: Request) -> Dict[str, List[str]]:
    query_dict: Dict[str, List[str]] = {}
    for key, value in request.query_params.multi_items():
        query_dict.setdefault(key, []).append(value)
    return query_dict


def get_payload_dict(payload: Dict[str, Any] = Body(..., description="JSON request body")) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须为 JSON 对象")
    return payload


def ensure_db_ready() -> bool:
    if not core.db_available():
        raise HTTPException(status_code=503, detail="数据库当前不可用，请确认本地服务和 MySQL 已启动")
    return True


def build_route(path: str, query_dict: Dict[str, List[str]] | None = None) -> str:
    if not query_dict:
        return path
    query = urlencode([(key, value) for key, values in query_dict.items() for value in values], doseq=True)
    return f"{path}?{query}" if query else path


def forward_get(path: str, query_dict: Dict[str, List[str]]) -> Response:
    return api_response(core.app_router(build_route(path, query_dict)))


def forward_post(path: str, payload: Dict[str, Any]) -> Response:
    return api_response(core.app_router_payload(path, payload))


root_router = APIRouter(tags=["root"])
page_router = APIRouter(tags=["pages"])
core_router = APIRouter(prefix="/api", tags=["core"])
recommend_router = APIRouter(prefix="/api", tags=["recommendation"])
weather_router = APIRouter(prefix="/api/weather", tags=["weather"])
poi_router = APIRouter(prefix="/api/poi", tags=["poi"])
guide_router = APIRouter(prefix="/api", tags=["guide"])
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
user_router = APIRouter(prefix="/api/user", tags=["user"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])
flow_router = APIRouter(prefix="/api/flow", tags=["flow"])
stats_router = APIRouter(prefix="/api", tags=["stats"])


@root_router.get("/", summary="API root entry")
def root_entry() -> Response:
    return api_response(core.build_response(True, {"project": "华东旅游数据分析、预测与推荐系统", "entry": "/app/modules"}))


@page_router.get("/app", summary="Serve index page")
@page_router.get("/app/", include_in_schema=False)
def serve_app() -> FileResponse:
    return FileResponse(get_frontend_file("index.html"))


@page_router.get("/app/modules", summary="Serve modules page")
@page_router.get("/app/modules/", include_in_schema=False)
def serve_modules() -> FileResponse:
    return FileResponse(get_frontend_file("modules.html"))


@page_router.get("/app/dashboard", summary="Serve dashboard page")
@page_router.get("/app/dashboard/", include_in_schema=False)
def serve_dashboard() -> FileResponse:
    return FileResponse(get_frontend_file("dashboard.html"))


@core_router.get("/frontend-modules", summary="Get tourist/admin module bundle")
def frontend_modules(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/frontend-modules", query_dict)


@core_router.get("/flow-module", summary="Get flow module bundle")
def flow_module(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/flow-module", query_dict)


@recommend_router.get("/recommendation-gallery", summary="Get recommendation gallery")
def recommendation_gallery(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/recommendation-gallery", query_dict)


@recommend_router.get("/recommend-locations", summary="Get recommendation provinces, cities and POIs")
def recommend_locations(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/recommend-locations", query_dict)


@recommend_router.get("/recommendations", summary="Get recommendation results")
def recommendations(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/recommendations", query_dict)


@weather_router.get("/current", summary="Get current weather")
def current_weather(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/weather/current", query_dict)


@core_router.get("/home-news", summary="Get scenic news")
def home_news(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/home-news", query_dict)


@core_router.get("/config", summary="Get frontend config")
def app_config(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/config", query_dict)


@poi_router.get("/preview", summary="Get POI preview with map info")
def poi_preview(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/poi/preview", query_dict)


@guide_router.get("/guide-options", summary="Get AI guide options")
def guide_options(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/guide-options", query_dict)


@guide_router.get("/guide-plan", summary="Generate AI guide plan")
def guide_plan(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/guide-plan", query_dict)


@core_router.get("/map-pois", summary="Get map related POIs")
def map_pois(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/map-pois", query_dict)


@auth_router.get("/login", summary="User login")
def auth_login(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/auth/login", query_dict)


@auth_router.get("/register", summary="User register")
def auth_register(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/auth/register", query_dict)


@user_router.get("/profile", summary="Get user profile")
def user_profile(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/user/profile", query_dict)


@user_router.get("/update-profile", summary="Update user profile with query parameters")
def user_update_profile(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/user/update-profile", query_dict)


@user_router.post("/update-profile-json", summary="Update user profile with JSON body")
def user_update_profile_json(
    payload: Dict[str, Any] = Depends(get_payload_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_post("/api/user/update-profile-json", payload)


@user_router.get("/favorites", summary="Get favorite POIs")
def user_favorites(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/user/favorites", query_dict)


@user_router.get("/plans", summary="Get user plans")
def user_plans(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/user/plans", query_dict)


@user_router.get("/plan-detail", summary="Get single travel plan detail")
def user_plan_detail(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/user/plan-detail", query_dict)


@user_router.post("/plan/save-json", summary="Save travel plan")
def user_plan_save_json(
    payload: Dict[str, Any] = Depends(get_payload_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_post("/api/user/plan/save-json", payload)


@user_router.post("/plan/delete-json", summary="Delete travel plan")
def user_plan_delete_json(
    payload: Dict[str, Any] = Depends(get_payload_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_post("/api/user/plan/delete-json", payload)


@user_router.post("/plan/item/save-json", summary="Save travel plan item")
def user_plan_item_save_json(
    payload: Dict[str, Any] = Depends(get_payload_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_post("/api/user/plan/item/save-json", payload)


@user_router.post("/plan/item/delete-json", summary="Delete travel plan item")
def user_plan_item_delete_json(
    payload: Dict[str, Any] = Depends(get_payload_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_post("/api/user/plan/item/delete-json", payload)


@user_router.post("/plan/import-ai-json", summary="Import AI plan into user plans")
def user_plan_import_ai_json(
    payload: Dict[str, Any] = Depends(get_payload_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_post("/api/user/plan/import-ai-json", payload)


@user_router.get("/add-favorite", summary="Add favorite POI")
def user_add_favorite(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/user/add-favorite", query_dict)


@user_router.get("/remove-favorite", summary="Remove favorite POI")
def user_remove_favorite(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/user/remove-favorite", query_dict)


@user_router.get("/add-comment", summary="Add user comment")
def user_add_comment(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/user/add-comment", query_dict)


@user_router.get("/comments", summary="Get POI comments")
def user_comments(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/user/comments", query_dict)


@user_router.get("/my-comments", summary="Get current user comments")
def user_my_comments(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/user/my-comments", query_dict)


@admin_router.get("/user-portrait", summary="Get operator portrait module data")
def admin_user_portrait(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/admin/user-portrait", query_dict)


@admin_router.get("/users", summary="Get admin user list")
def admin_users(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/admin/users", query_dict)


@admin_router.get("/comments", summary="Get admin comments list")
def admin_comments(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/admin/comments", query_dict)


@admin_router.get("/create-user", summary="Create admin or tourist user")
def admin_create_user(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/admin/create-user", query_dict)


@admin_router.get("/update-user", summary="Update admin or tourist user")
def admin_update_user(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/admin/update-user", query_dict)


@admin_router.get("/delete-user", summary="Delete tourist user")
def admin_delete_user(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/admin/delete-user", query_dict)


@flow_router.get("/report", summary="Get flow training report")
def flow_report(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/flow/report", query_dict)


@stats_router.get("/city-stats", summary="Get city statistics")
def city_stats(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/city-stats", query_dict)


@stats_router.get("/hot-poi-top100", summary="Get hot POI top list")
def hot_poi_top100(
    query_dict: Dict[str, List[str]] = Depends(get_query_dict),
    db_ready: bool = Depends(ensure_db_ready),
) -> Response:
    _ = db_ready
    return forward_get("/api/hot-poi-top100", query_dict)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Travel Project API",
        version="2.0.0",
        description="采用 APIRouter + Depends 的华东旅游数据分析项目接口服务。",
    )
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR)), name="assets")

    app.include_router(root_router)
    app.include_router(page_router)
    app.include_router(core_router)
    app.include_router(recommend_router)
    app.include_router(weather_router)
    app.include_router(poi_router)
    app.include_router(guide_router)
    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(admin_router)
    app.include_router(flow_router)
    app.include_router(stats_router)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> Response:
        _ = request
        return json_response({"success": False, "message": exc.detail, "data": None}, exc.status_code)

    return app


app = create_app()


def main() -> None:
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
