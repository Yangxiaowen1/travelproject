# 华东旅数

## 目录结构

- `api/`：FastAPI 接口与页面服务
- `frontend/`：前端页面、样式、图表脚本
- `data/`：页面展示和算法所需数据文件
- `scripts/`：结果整理脚本
- `spark/`：ALS 推荐与客流预测 Spark 脚本
- `sql/`：数据库建表与初始化 SQL
- `requirements.txt`：Python 依赖
- `start_modules.py`：推荐启动入口
- `start_modules.bat`：Windows 双击启动
- `sync_modules_data.bat`：手动刷新数据后再启动
- `.env.example`：环境变量示例

## 运行环境要求

必须有：

1. Python 3.10 或更高版本
2. MySQL 8.0 或 8.4

建议有：

1. 稳定网络
2. 浏览器

## 第一次运行

### 1. 安装依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

如果需要自定义数据库、地图或大模型配置，复制一份：

- `.env.example`

重命名为：

- `.env`

然后按自己电脑的数据库情况修改，默认配置已内置。

## 启动项目

推荐二选一：

1. 双击 `start_modules.bat`
2. 终端运行 `python start_modules.py`

启动成功后打开：

- `http://127.0.0.1:8000/app`（首页）
- `http://127.0.0.1:8000/app/modules`（模块页）
- `http://127.0.0.1:8000/docs`（接口文档）

## 演示账号

- 游客端：`tourist / 123456`
- 管理端：`operator / 123456`

## 如果需要刷新页面数据

如果你想重新整理模块结果并同步到数据库，再执行：

```bash
python start_modules.py --sync-data
```

或者双击：

- `sync_modules_data.bat`

## 如果启动失败，优先检查这几项

1. MySQL 是否已经安装并启动
2. Python 是否已经安装依赖（`pip install -r requirements.txt`）
3. `.env` 里的数据库账号密码是否正确
4. 3306 端口是否被别的数据库占用

## 内容说明

只保留了本地演示需要的部分：
- 页面
- 接口
- 数据
- 本地数据库目录
- 初始化脚本
- 启动脚本
没有保留集群迁移、历史草稿和归档材料。
