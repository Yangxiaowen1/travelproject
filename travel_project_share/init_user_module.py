from __future__ import annotations

import hashlib
import os
import random
from pathlib import Path

import pandas as pd
import pymysql


BASE_DIR = Path(__file__).resolve().parent
CLEAN_PATH = BASE_DIR / "data" / "clean" / "cleaned_with_standard_feature.csv"
DB_CONFIG = {
    "host": os.getenv("TRAVEL_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("TRAVEL_DB_PORT", "3306")),
    "user": os.getenv("TRAVEL_DB_USER", "root"),
    "password": os.getenv("TRAVEL_DB_PASSWORD", ""),
    "database": os.getenv("TRAVEL_DB_NAME", "travel_ctrip"),
    "charset": os.getenv("TRAVEL_DB_CHARSET", "utf8mb4"),
    "autocommit": True,
}


def password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def connect_db(database: str | None = "travel_ctrip"):
    cfg = dict(DB_CONFIG)
    if database is None:
        cfg.pop("database", None)
    return pymysql.connect(**cfg)


def ensure_database() -> None:
    conn = connect_db(None)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE IF NOT EXISTS travel_ctrip CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
    finally:
        conn.close()


def load_poi_sample() -> pd.DataFrame:
    df = pd.read_csv(CLEAN_PATH)
    keep = [
        "poiId",
        "poiName",
        "province",
        "cityName",
        "regionName",
        "commentScoreFloat",
        "heatScoreFloat",
        "priceFloat",
        "tagNames",
        "coverImageUrl",
        "detailUrl",
    ]
    df = df[keep].copy()
    df = df.sort_values(["heatScoreFloat", "commentScoreFloat"], ascending=False).head(500)
    return df.fillna("")


def main() -> None:
    ensure_database()
    pois = load_poi_sample()
    cities = [str(x) for x in pois["cityName"].dropna().unique()[:30]]
    preferences = ["山水自然", "亲子家庭", "历史人文", "夜游休闲", "高性价比", "网红打卡"]
    budgets = ["低预算", "中等预算", "高预算"]
    genders = ["男", "女"]
    random.seed(42)

    conn = connect_db()
    try:
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
                  UNIQUE KEY uniq_user_poi (user_id, poi_id)
                ) CHARACTER SET utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_behavior_profile (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  user_id BIGINT NOT NULL,
                  preference_tag VARCHAR(64) NOT NULL,
                  visit_count INT NOT NULL,
                  favorite_count INT NOT NULL,
                  avg_budget DOUBLE NOT NULL,
                  active_score DOUBLE NOT NULL,
                  segment_name VARCHAR(64) NOT NULL,
                  PRIMARY KEY (id),
                  UNIQUE KEY uniq_user_profile (user_id)
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

            demo_users = [
                ("tourist", "123456", "tourist", "演示游客", "女", 24, "上海市", "山水自然", "中等预算"),
                ("operator", "123456", "operator", "运营管理员", "男", 31, "杭州市", "运营分析", "高预算"),
            ]
            for username, password, role, nickname, gender, age, city, pref, budget in demo_users:
                cur.execute(
                    """
                    INSERT INTO travel_users
                    (username, password_hash, role, nickname, gender, age, city_name, travel_preference, budget_level, avatar_url)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE role=VALUES(role), nickname=VALUES(nickname)
                    """,
                    (
                        username,
                        password_hash(password),
                        role,
                        nickname,
                        gender,
                        age,
                        city,
                        pref,
                        budget,
                        "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=240&q=80",
                    ),
                )

            cur.execute("SELECT COUNT(*) FROM travel_users WHERE username LIKE 'user_%'")
            if cur.fetchone()[0] < 40:
                for idx in range(1, 81):
                    pref = random.choice(preferences)
                    budget = random.choice(budgets)
                    city = random.choice(cities)
                    gender = random.choice(genders)
                    age = random.randint(18, 55)
                    role = "tourist"
                    cur.execute(
                        """
                        INSERT INTO travel_users
                        (username, password_hash, role, nickname, gender, age, city_name, travel_preference, budget_level, avatar_url)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE nickname=VALUES(nickname)
                        """,
                        (
                            f"user_{idx:03d}",
                            password_hash("123456"),
                            role,
                            f"游客{idx:03d}",
                            gender,
                            age,
                            city,
                            pref,
                            budget,
                            f"https://api.dicebear.com/7.x/initials/svg?seed=user{idx}",
                        ),
                    )

            cur.execute("SELECT id, travel_preference, budget_level FROM travel_users WHERE role='tourist'")
            users = cur.fetchall()
            poi_rows = list(pois.itertuples(index=False))
            for user_id, pref, budget in users:
                sample_count = random.randint(2, 5)
                sample_pois = random.sample(poi_rows, sample_count)
                for poi in sample_pois:
                    cur.execute(
                        """
                        INSERT IGNORE INTO user_favorites
                        (user_id, poi_id, poi_name, province, city_name, region_name, cover_image_url, detail_url)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            user_id,
                            int(poi.poiId),
                            str(poi.poiName),
                            str(poi.province),
                            str(poi.cityName),
                            str(poi.regionName),
                            str(poi.coverImageUrl),
                            str(poi.detailUrl),
                        ),
                    )

                cur.execute("SELECT COUNT(*) FROM user_poi_comments WHERE user_id=%s", (user_id,))
                if cur.fetchone()[0] == 0:
                    comment_templates = [
                        "交通方便，适合周末轻松出行，拍照效果很好。",
                        "景区服务不错，亲子游体验好，排队时间可以接受。",
                        "自然风光很出片，雨天会影响体验，建议晴天去。",
                        "历史人文氛围浓，适合深度游和慢慢逛。",
                        "夜游氛围很好，美食选择多，适合年轻游客打卡。",
                        "性价比高，门票价格合理，适合家庭出行。",
                        "节假日人多，建议提前预约，上午去体验更好。",
                        "公共交通方便，周边住宿和餐饮都比较成熟。",
                    ]
                    for poi in sample_pois[: random.randint(1, min(3, len(sample_pois)))]:
                        cur.execute(
                            """
                            INSERT INTO user_poi_comments
                            (user_id, poi_id, poi_name, province, city_name, rating, content)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                            """,
                            (
                                user_id,
                                int(poi.poiId),
                                str(poi.poiName),
                                str(poi.province),
                                str(poi.cityName),
                                random.randint(4, 5),
                                random.choice(comment_templates),
                            ),
                        )

                segment = "高活跃收藏型" if sample_count >= 4 else "轻度浏览型"
                if pref in ["亲子家庭", "历史人文"]:
                    segment = "主题偏好明确型"
                cur.execute(
                    """
                    INSERT INTO user_behavior_profile
                    (user_id, preference_tag, visit_count, favorite_count, avg_budget, active_score, segment_name)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                    preference_tag=VALUES(preference_tag),
                    visit_count=VALUES(visit_count),
                    favorite_count=VALUES(favorite_count),
                    avg_budget=VALUES(avg_budget),
                    active_score=VALUES(active_score),
                    segment_name=VALUES(segment_name)
                    """,
                    (
                        user_id,
                        pref or "综合兴趣",
                        random.randint(8, 80),
                        sample_count,
                        {"低预算": 80, "中等预算": 220, "高预算": 520}.get(budget, 200),
                        round(random.uniform(45, 96), 1),
                        segment,
                    ),
                )
    finally:
        conn.close()

    print("用户、收藏和画像表已准备完成")


if __name__ == "__main__":
    main()
