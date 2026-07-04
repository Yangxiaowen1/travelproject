from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
API_DIR = PROJECT_ROOT / "api"
REFRESH_RESULT_SCRIPT = PROJECT_ROOT / "scripts" / "refresh_module_results.py"
SYNC_SCRIPT = PROJECT_ROOT / "sync_results_to_mysql.py"
INIT_USER_SCRIPT = PROJECT_ROOT / "init_user_module.py"
ENV_FILE = PROJECT_ROOT / ".env"
MYSQL_LOCAL_DIR = PROJECT_ROOT / "mysql_local"
MYSQL_DATA_DIR = MYSQL_LOCAL_DIR / "data"
MYSQL_LOG_DIR = MYSQL_LOCAL_DIR / "logs"
MYSQL_CONFIG_PATH = MYSQL_LOCAL_DIR / "my.generated.ini"
MYSQL_BIN_CANDIDATES = [
    Path(r"C:\Program Files\MySQL\MySQL Server 8.4\bin"),
    Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin"),
]
DEFAULT_URLS = [
    "http://127.0.0.1:8000/api/frontend-modules",
    "http://127.0.0.1:8000/api/flow-module",
    "http://127.0.0.1:8000/app/modules",
]
API_PYTHON_CANDIDATES = [
    Path(sys.executable),
    Path(r"C:\Users\DELL\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
]


def print_line(text: str) -> None:
    print(text, flush=True)


def load_env_file() -> dict[str, str]:
    env = os.environ.copy()
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def find_mysql_bin() -> Path | None:
    for path in MYSQL_BIN_CANDIDATES:
        if (path / "mysql.exe").exists() and (path / "mysqld.exe").exists():
            return path
    return None


def can_connect_port(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def render_mysql_config(mysql_bin: Path, env: dict[str, str]) -> Path:
    MYSQL_LOCAL_DIR.mkdir(exist_ok=True)
    MYSQL_LOG_DIR.mkdir(parents=True, exist_ok=True)
    port = int(env.get("TRAVEL_DB_PORT", "3306"))
    basedir = mysql_bin.parent.as_posix()
    datadir = MYSQL_DATA_DIR.as_posix()
    log_file = (MYSQL_LOG_DIR / "mysql.err").as_posix()
    content = "\n".join(
        [
            "[mysqld]",
            f"basedir={basedir}",
            f"datadir={datadir}",
            f"port={port}",
            "bind-address=127.0.0.1",
            "character-set-server=utf8mb4",
            "collation-server=utf8mb4_general_ci",
            f"log-error={log_file}",
            "",
            "[client]",
            f"port={port}",
            "default-character-set=utf8mb4",
            "",
        ]
    )
    MYSQL_CONFIG_PATH.write_text(content, encoding="utf-8")
    return MYSQL_CONFIG_PATH


def can_connect_mysql(env: dict[str, str]) -> bool:
    host = env.get("TRAVEL_DB_HOST", "127.0.0.1")
    port = int(env.get("TRAVEL_DB_PORT", "3306"))
    user = env.get("TRAVEL_DB_USER", "root")
    password = env.get("TRAVEL_DB_PASSWORD", "")
    if not can_connect_port(host, port):
        return False

    mysql_bin = find_mysql_bin()
    if mysql_bin is None:
        return True

    mysql_exe = mysql_bin / "mysql.exe"
    cmd = [str(mysql_exe), f"-h{host}", f"-P{port}", f"-u{user}", "-e", "SELECT 1"]
    if password:
        cmd.insert(4, f"-p{password}")
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8,
        )
        return result.returncode == 0
    except Exception:
        return False


def ensure_mysql_started(env: dict[str, str]) -> None:
    host = env.get("TRAVEL_DB_HOST", "127.0.0.1")
    port = int(env.get("TRAVEL_DB_PORT", "3306"))
    if can_connect_mysql(env):
        print_line("数据库已经在运行")
        return

    if host not in {"127.0.0.1", "localhost"}:
        raise RuntimeError(f"无法连接数据库 {host}:{port}，请先确认对方数据库已启动")

    mysql_bin = find_mysql_bin()
    if mysql_bin is None:
        raise RuntimeError("没有找到本机 MySQL 8.x。请先安装 MySQL，再重新启动项目。")
    if not MYSQL_DATA_DIR.exists():
        raise RuntimeError("项目内缺少 mysql_local/data，无法自动拉起本地数据库。")

    mysql_config = render_mysql_config(mysql_bin, env)
    mysqld_exe = mysql_bin / "mysqld.exe"
    print_line("正在启动本地数据库...")
    subprocess.Popen(
        [str(mysqld_exe), f"--defaults-file={mysql_config}"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    start = time.time()
    while time.time() - start < 30:
        time.sleep(2)
        if can_connect_mysql(env):
            print_line("数据库启动成功")
            return
    raise RuntimeError(f"本地数据库启动失败，请检查 {MYSQL_LOG_DIR / 'mysql.err'}")


def run_step(script_path: Path, title: str, env: dict[str, str]) -> None:
    if not script_path.exists():
        raise RuntimeError(f"{title}失败：缺少文件 {script_path.name}")
    print_line(f"{title}...")
    result = subprocess.run([sys.executable, str(script_path)], cwd=str(PROJECT_ROOT), text=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"{title}失败")


def ensure_port_ready(port: int, timeout_seconds: int = 20) -> None:
    start = time.time()
    while time.time() - start < timeout_seconds:
        if can_connect_port("127.0.0.1", port):
            return
        time.sleep(1)
    raise RuntimeError("页面服务没有正常启动")


def python_has_fastapi(python_exe: Path) -> bool:
    if not python_exe.exists():
        return False
    try:
        result = subprocess.run(
            [str(python_exe), "-c", "import fastapi,uvicorn"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def pick_api_python() -> Path:
    for candidate in API_PYTHON_CANDIDATES:
        if python_has_fastapi(candidate):
            return candidate
    raise RuntimeError("没有找到可用的 FastAPI 运行环境，请先执行 pip install -r requirements.txt")


def ensure_api_started(env: dict[str, str]) -> None:
    if can_connect_port("127.0.0.1", 8000):
        print_line("页面服务已经在运行")
        return
    print_line("正在启动页面服务...")
    api_python = pick_api_python()
    subprocess.Popen(
        [str(api_python), "simple_server.py"],
        cwd=str(API_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    ensure_port_ready(8000)


def check_urls() -> None:
    for url in DEFAULT_URLS:
        with urllib.request.urlopen(url, timeout=60) as response:
            if response.status != 200:
                raise RuntimeError(f"页面检查失败：{url}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print_line("开始准备项目运行环境")
    env = load_env_file()
    ensure_mysql_started(env)
    run_step(INIT_USER_SCRIPT, "初始化演示账号和游客数据", env)
    ensure_api_started(env)
    print_line("检查页面地址...")
    check_urls()
    print_line("")
    print_line("项目已经可以打开")
    print_line("首页: http://127.0.0.1:8000/app")
    print_line("模块页: http://127.0.0.1:8000/app/modules")
    if not args.sync_data:
        print_line("如需手动更新榜单和分析结果，请执行: python start_modules.py --sync-data")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print_line(f"启动失败: {exc}")
        sys.exit(1)
