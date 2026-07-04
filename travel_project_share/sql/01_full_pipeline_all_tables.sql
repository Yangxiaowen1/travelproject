-- =============================================
-- 携程旅游大数据分析 - 完整管道（21 张表）
-- DIM/DWD → flat_poi_full → 21 张 ADS/前端表 → MariaDB
-- 完全对齐 build_frontend_module_data.py + 04_generate_analysis_ads.py
-- =============================================

-- =============================================
-- 第一部分：DIM / DWD 临时视图
-- =============================================
SELECT '=== 第一部分：创建 DIM/DWD 视图 ===' AS step;

CREATE OR REPLACE TEMPORARY VIEW dim_city
USING csv OPTIONS (path '/travel_project/dim/dim_city/dim_city.csv', header 'true');

CREATE OR REPLACE TEMPORARY VIEW dim_district
USING csv OPTIONS (path '/travel_project/dim/dim_district/dim_district.csv', header 'true');

CREATE OR REPLACE TEMPORARY VIEW dim_region
USING csv OPTIONS (path '/travel_project/dim/dim_region/dim_region.csv', header 'true');

CREATE OR REPLACE TEMPORARY VIEW dim_sight_level
USING csv OPTIONS (path '/travel_project/dim/dim_sight_level/dim_sight_level.csv', header 'true');

CREATE OR REPLACE TEMPORARY VIEW dim_price_bucket
USING csv OPTIONS (path '/travel_project/dim/dim_price_bucket/dim_price_bucket.csv', header 'true');

CREATE OR REPLACE TEMPORARY VIEW dim_score_bucket
USING csv OPTIONS (path '/travel_project/dim/dim_score_bucket/dim_score_bucket.csv', header 'true');

CREATE OR REPLACE TEMPORARY VIEW dim_tag
USING csv OPTIONS (path '/travel_project/dim/dim_tag/dim_tag.csv', header 'true');

CREATE OR REPLACE TEMPORARY VIEW dwd_poi_base_info
USING csv OPTIONS (path '/travel_project/dwd/dwd_poi_base_info/dwd_poi_base_info.csv', header 'true');

CREATE OR REPLACE TEMPORARY VIEW dwd_poi_price_daily
USING csv OPTIONS (path '/travel_project/dwd/dwd_poi_price_daily/dwd_poi_price_daily.csv', header 'true');

CREATE OR REPLACE TEMPORARY VIEW dwd_poi_comment_daily
USING csv OPTIONS (path '/travel_project/dwd/dwd_poi_comment_daily/dwd_poi_comment_daily.csv', header 'true');

CREATE OR REPLACE TEMPORARY VIEW dwd_poi_tag_relation
USING csv OPTIONS (path '/travel_project/dwd/dwd_poi_tag_relation/dwd_poi_tag_relation.csv', header 'true');

CREATE OR REPLACE TEMPORARY VIEW dwd_poi_media_info
USING csv OPTIONS (path '/travel_project/dwd/dwd_poi_media_info/dwd_poi_media_info.csv', header 'true');

-- =============================================
-- 第二部分：源数据校验
-- =============================================
SELECT '=== 第二部分：源数据校验 ===' AS step;

SELECT 'dim_city', COUNT(*) FROM dim_city
UNION ALL SELECT 'dim_district', COUNT(*) FROM dim_district
UNION ALL SELECT 'dim_region', COUNT(*) FROM dim_region
UNION ALL SELECT 'dim_sight_level', COUNT(*) FROM dim_sight_level
UNION ALL SELECT 'dim_price_bucket', COUNT(*) FROM dim_price_bucket
UNION ALL SELECT 'dim_score_bucket', COUNT(*) FROM dim_score_bucket
UNION ALL SELECT 'dim_tag', COUNT(*) FROM dim_tag
UNION ALL SELECT 'dwd_poi_base_info', COUNT(*) FROM dwd_poi_base_info
UNION ALL SELECT 'dwd_poi_price_daily', COUNT(*) FROM dwd_poi_price_daily
UNION ALL SELECT 'dwd_poi_comment_daily', COUNT(*) FROM dwd_poi_comment_daily
UNION ALL SELECT 'dwd_poi_tag_relation', COUNT(*) FROM dwd_poi_tag_relation
UNION ALL SELECT 'dwd_poi_media_info', COUNT(*) FROM dwd_poi_media_info;

-- =============================================
-- 第三部分：去重 + 标签聚合 + 平铺视图
-- =============================================
SELECT '=== 第三部分：构造 flat_poi_full ===' AS step;

-- 3.1 按 poi_id 去重 base_info
CREATE OR REPLACE TEMPORARY VIEW dwd_poi_base_dedup AS
SELECT * FROM (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY CAST(poi_id AS BIGINT) ORDER BY CAST(region_id AS INT)) AS rn
  FROM dwd_poi_base_info
) tmp WHERE rn = 1;

SELECT 'base_info 去重后:', COUNT(*) FROM dwd_poi_base_dedup;

-- 3.2 标签聚合（多行拼成一行）
CREATE OR REPLACE TEMPORARY VIEW dwd_poi_tags_agg AS
SELECT
  CAST(poi_id AS BIGINT) AS poi_id_agg,
  CONCAT_WS('|', COLLECT_LIST(tag_name)) AS tag_list,
  COUNT(tag_name) AS tag_count
FROM dwd_poi_tag_relation
GROUP BY CAST(poi_id AS BIGINT);

SELECT '标签聚合后:', COUNT(*) FROM dwd_poi_tags_agg;

-- 3.3 flat_poi_full：完整平铺视图
CREATE OR REPLACE TEMPORARY VIEW flat_poi_full AS
SELECT
  CAST(b.poi_id AS BIGINT) AS poi_id,
  b.poiName AS poi_name,
  c.province_name AS province,
  b.cityName AS city_name,
  b.districtName AS district_name,
  b.regionName AS region_name,
  CAST(b.priceFloat AS DOUBLE) AS price,
  CAST(b.isFree AS INT) AS is_free,
  CAST(b.hasVideo AS INT) AS has_video,
  b.sightLevelStr AS sight_level,
  CAST(b.latitude AS DOUBLE) AS latitude,
  CAST(b.longitude AS DOUBLE) AS longitude,
  CAST(b.distance_to_center_km AS DOUBLE) AS distance_km,
  b.distance_level,
  CAST(d.commentScoreFloat AS DOUBLE) AS comment_score,
  CAST(d.commentCountInt AS INT) AS comment_count,
  CAST(d.heatScoreFloat AS DOUBLE) AS heat_score,
  d.score_level,
  d.heat_level,
  COALESCE(t.tag_list, '') AS tag_list,
  COALESCE(t.tag_count, 0) AS tag_count,
  b.shortFeatureText AS short_feature,
  -- 派生字段：price_level
  CASE
    WHEN CAST(b.priceFloat AS DOUBLE) <= 0 THEN '0元免费'
    WHEN CAST(b.priceFloat AS DOUBLE) < 100 THEN '0-100元'
    WHEN CAST(b.priceFloat AS DOUBLE) < 250 THEN '100-250元'
    ELSE '250元以上'
  END AS price_level,
  -- 派生字段：is_kid（从 tag 推断）
  CASE WHEN t.tag_list LIKE '%亲子同乐%' OR t.tag_list LIKE '%遛娃宝藏地%' THEN 1 ELSE 0 END AS is_kid,
  -- 派生字段：is_night_tour（从 tag 推断）
  CASE WHEN t.tag_list LIKE '%夜%' THEN 1 ELSE 0 END AS is_night_tour
FROM dwd_poi_base_dedup b
LEFT JOIN dim_city c ON CAST(b.city_id AS INT) = c.city_id
LEFT JOIN dwd_poi_comment_daily d ON CAST(b.poi_id AS BIGINT) = CAST(d.poi_id AS BIGINT)
LEFT JOIN dwd_poi_tags_agg t ON CAST(b.poi_id AS BIGINT) = t.poi_id_agg;

SELECT 'flat_poi_full rows:', COUNT(*) FROM flat_poi_full;

-- =============================================
-- 第四部分：ADS 聚合表（5 张，同 v4）
-- =============================================
SELECT '=== 第四部分：计算 5 张 ADS 表 ===' AS step;

-- 4.1 ads_city_dashboard
SELECT '--- 4.1 ads_city_dashboard ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW ads_city_dashboard AS
SELECT province, city_name AS cityName,
  COUNT(DISTINCT poi_id) AS poi_count,
  ROUND(AVG(price), 2) AS avg_price,
  ROUND(AVG(comment_score), 2) AS avg_score,
  ROUND(AVG(heat_score), 2) AS avg_heat,
  SUM(is_free) AS free_count,
  ROUND(AVG(CAST(is_free AS DOUBLE)), 4) AS free_ratio,
  SUM(CAST(comment_count AS BIGINT)) AS total_comments
FROM flat_poi_full GROUP BY province, city_name
ORDER BY poi_count DESC, avg_heat DESC;
SELECT 'ads_city_dashboard rows:', COUNT(*) FROM ads_city_dashboard;

-- 4.2 ads_province_dashboard
SELECT '--- 4.2 ads_province_dashboard ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW ads_province_dashboard AS
SELECT province,
  COUNT(DISTINCT city_name) AS city_count,
  COUNT(DISTINCT poi_id) AS poi_count,
  ROUND(AVG(price), 2) AS avg_price,
  ROUND(AVG(comment_score), 2) AS avg_score,
  ROUND(AVG(heat_score), 2) AS avg_heat,
  SUM(is_free) AS free_count,
  ROUND(AVG(CAST(is_free AS DOUBLE)), 4) AS free_ratio
FROM flat_poi_full GROUP BY province
ORDER BY poi_count DESC;
SELECT 'ads_province_dashboard rows:', COUNT(*) FROM ads_province_dashboard;

-- 4.3 ads_city_top8_poi
SELECT '--- 4.3 ads_city_top8_poi ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW ads_city_top8_poi AS
SELECT * FROM (
  SELECT province, city_name AS cityName,
    ROW_NUMBER() OVER (PARTITION BY city_name ORDER BY
      (heat_score * 0.4 + comment_score * 10 * 0.3 + LN(CAST(comment_count AS BIGINT) + 1) * 0.2 + CASE WHEN price = 0 THEN 1.0 ELSE 0.0 END * 0.1) DESC,
      heat_score DESC) AS city_rank,
    poi_id AS poiId, poi_name AS poiName, region_name AS regionName,
    price AS priceFloat, comment_score AS commentScoreFloat,
    heat_score AS heatScoreFloat,
    ROUND(heat_score * 0.4 + comment_score * 10 * 0.3 + LN(CAST(comment_count AS BIGINT) + 1) * 0.2 + CASE WHEN price = 0 THEN 1.0 ELSE 0.0 END * 0.1, 4) AS rank_score
  FROM flat_poi_full
) ranked WHERE city_rank <= 8;
SELECT 'ads_city_top8_poi rows:', COUNT(*) FROM ads_city_top8_poi;

-- 4.4 ads_province_top8_poi
SELECT '--- 4.4 ads_province_top8_poi ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW ads_province_top8_poi AS
SELECT * FROM (
  SELECT province,
    ROW_NUMBER() OVER (PARTITION BY province ORDER BY
      (heat_score * 0.4 + comment_score * 10 * 0.3 + LN(CAST(comment_count AS BIGINT) + 1) * 0.2 + CASE WHEN price = 0 THEN 1.0 ELSE 0.0 END * 0.1) DESC,
      heat_score DESC) AS province_rank,
    poi_id AS poiId, poi_name AS poiName, city_name AS cityName, region_name AS regionName,
    price AS priceFloat, comment_score AS commentScoreFloat,
    heat_score AS heatScoreFloat,
    ROUND(heat_score * 0.4 + comment_score * 10 * 0.3 + LN(CAST(comment_count AS BIGINT) + 1) * 0.2 + CASE WHEN price = 0 THEN 1.0 ELSE 0.0 END * 0.1, 4) AS rank_score
  FROM flat_poi_full
) ranked WHERE province_rank <= 8;
SELECT 'ads_province_top8_poi rows:', COUNT(*) FROM ads_province_top8_poi;

-- 4.5 ads_hot_poi_top100
SELECT '--- 4.5 ads_hot_poi_top100 ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW ads_hot_poi_top100 AS
SELECT poi_id, poi_name AS poiName, city_name AS cityName, province,
  region_name AS regionName, price AS priceFloat, comment_score AS commentScoreFloat,
  comment_count AS commentCountInt, heat_score AS heatScoreFloat
FROM flat_poi_full
SORT BY heat_score DESC, comment_count DESC LIMIT 100;
SELECT 'ads_hot_poi_top100 rows:', COUNT(*) FROM ads_hot_poi_top100;

-- =============================================
-- 第五部分：前端模块 CSV 表（16 张）
-- 对齐 build_frontend_module_data.py
-- =============================================
SELECT '=== 第五部分：计算 16 张前端模块表 ===' AS step;

-- ===== 5.1 frontend_module_home_hot_poi_top10 =====
SELECT '--- 5.1 home_hot_poi_top10 ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_home_hot_poi_top10 AS
SELECT poi_name, city_name, region_name, heat_score, comment_score, comment_count, price
FROM flat_poi_full
SORT BY heat_score DESC, comment_count DESC, comment_score DESC
LIMIT 10;
SELECT 'home_hot_poi_top10 rows:', COUNT(*) FROM frontend_module_home_hot_poi_top10;

-- ===== 5.2 frontend_module_home_tag_top20 =====
SELECT '--- 5.2 home_tag_top20 ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_home_tag_top20 AS
SELECT tag_name, COUNT(*) AS poi_count
FROM (
  SELECT EXPLODE(SPLIT(tag_list, '\\|')) AS tag_name FROM flat_poi_full
  WHERE tag_list IS NOT NULL AND tag_list != ''
)
WHERE tag_name IS NOT NULL AND tag_name != ''
GROUP BY tag_name
ORDER BY poi_count DESC, tag_name ASC
LIMIT 20;
SELECT 'home_tag_top20 rows:', COUNT(*) FROM frontend_module_home_tag_top20;

-- ===== 5.3 frontend_module_home_price_distribution =====
SELECT '--- 5.3 home_price_distribution ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_home_price_distribution AS
SELECT price_level, COUNT(*) AS poi_count
FROM flat_poi_full
GROUP BY price_level
ORDER BY price_level;
SELECT 'home_price_distribution rows:', COUNT(*) FROM frontend_module_home_price_distribution;

-- ===== 5.4 frontend_module_home_score_distribution =====
SELECT '--- 5.4 home_score_distribution ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_home_score_distribution AS
SELECT score_level, COUNT(*) AS poi_count
FROM flat_poi_full
GROUP BY score_level
ORDER BY score_level;
SELECT 'home_score_distribution rows:', COUNT(*) FROM frontend_module_home_score_distribution;

-- ===== 5.5 frontend_module_city_summary =====
SELECT '--- 5.5 city_summary ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW city_summary_inner AS
SELECT province, city_name,
  COUNT(*) AS poi_count,
  ROUND(AVG(price), 2) AS avg_price,
  ROUND(AVG(comment_score), 2) AS avg_score,
  ROUND(AVG(heat_score), 2) AS avg_heat,
  SUM(is_free) AS free_poi_count,
  ROUND(CAST(SUM(is_free) AS DOUBLE) / COUNT(*), 4) AS free_ratio,
  SUM(CASE WHEN comment_score >= 4.5 THEN 1 ELSE 0 END) AS high_score_poi_count,
  SUM(CASE WHEN sight_level = '5A' THEN 1 ELSE 0 END) AS five_a_poi_count,
  SUM(comment_count) AS comment_total
FROM flat_poi_full
GROUP BY province, city_name;

CREATE OR REPLACE TEMPORARY VIEW frontend_module_city_summary AS
SELECT * FROM city_summary_inner
ORDER BY poi_count DESC, comment_total DESC, city_name ASC;
SELECT 'city_summary rows:', COUNT(*) FROM frontend_module_city_summary;

-- ===== 5.6 frontend_module_city_tag_summary =====
SELECT '--- 5.6 city_tag_summary ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_city_tag_summary AS
SELECT city_name, tag_name, COUNT(*) AS poi_count
FROM (
  SELECT city_name, EXPLODE(SPLIT(tag_list, '\\|')) AS tag_name
  FROM flat_poi_full WHERE tag_list IS NOT NULL AND tag_list != ''
) WHERE tag_name IS NOT NULL AND tag_name != ''
GROUP BY city_name, tag_name
ORDER BY city_name ASC, poi_count DESC, tag_name ASC;
SELECT 'city_tag_summary rows:', COUNT(*) FROM frontend_module_city_tag_summary;

-- ===== 5.7 frontend_module_city_top_poi =====
SELECT '--- 5.7 city_top_poi ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_city_top_poi AS
SELECT * FROM (
  SELECT city_name,
    ROW_NUMBER() OVER (PARTITION BY city_name ORDER BY heat_score DESC, comment_count DESC, comment_score DESC) AS rank_no,
    poi_name, region_name, heat_score, comment_score, comment_count, price
  FROM flat_poi_full
) ranked WHERE rank_no <= 10
ORDER BY city_name ASC, rank_no ASC;
SELECT 'city_top_poi rows:', COUNT(*) FROM frontend_module_city_top_poi;

-- ===== 5.8 frontend_module_filter_poi_base =====
SELECT '--- 5.8 filter_poi_base ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_filter_poi_base AS
SELECT poi_id, poi_name, province, city_name, district_name, region_name,
  price, price_level, comment_score, comment_count, score_level,
  heat_score, heat_level, is_free, distance_km, distance_level,
  sight_level, tag_list AS tag_text, is_kid, is_night_tour,
  short_feature, latitude, longitude
FROM flat_poi_full
SORT BY heat_score DESC, comment_count DESC, poi_name ASC;
SELECT 'filter_poi_base rows:', COUNT(*) FROM frontend_module_filter_poi_base;

-- ===== 5.9 frontend_module_detail_hot_top20 =====
SELECT '--- 5.9 detail_hot_top20 ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_detail_hot_top20 AS
SELECT poi_id, poi_name, city_name, region_name, price, comment_score,
  comment_count, heat_score, sight_level, tag_list AS tag_text,
  short_feature, latitude, longitude
FROM flat_poi_full
SORT BY heat_score DESC, comment_count DESC, comment_score DESC
LIMIT 20;
SELECT 'detail_hot_top20 rows:', COUNT(*) FROM frontend_module_detail_hot_top20;

-- ===== 5.10 frontend_module_detail_value_top20 =====
SELECT '--- 5.10 detail_value_top20 ---' AS step;
-- 公式: comment_score*0.45 + heat_score*0.35 + min(comment_count/10000,1)*10*0.2 - min(price/500,1)*2
CREATE OR REPLACE TEMPORARY VIEW frontend_module_detail_value_top20 AS
SELECT poi_id, poi_name, city_name, region_name, price, comment_score,
  comment_count, heat_score, sight_level, tag_list AS tag_text,
  short_feature, latitude, longitude
FROM (
  SELECT *,
    (comment_score * 0.45 + heat_score * 0.35
     + LEAST(CAST(comment_count AS DOUBLE) / 10000.0, 1.0) * 10 * 0.2
     - LEAST(price / 500.0, 1.0) * 2) AS value_score
  FROM flat_poi_full
) scored
SORT BY value_score DESC
LIMIT 20;
SELECT 'detail_value_top20 rows:', COUNT(*) FROM frontend_module_detail_value_top20;

-- ===== 5.11 frontend_module_detail_free_top20 =====
SELECT '--- 5.11 detail_free_top20 ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_detail_free_top20 AS
SELECT poi_id, poi_name, city_name, region_name, price, comment_score,
  comment_count, heat_score, sight_level, tag_list AS tag_text,
  short_feature, latitude, longitude
FROM flat_poi_full
WHERE is_free = 1
SORT BY comment_score DESC, heat_score DESC, comment_count DESC
LIMIT 20;
SELECT 'detail_free_top20 rows:', COUNT(*) FROM frontend_module_detail_free_top20;

-- ===== 5.12 frontend_module_detail_family_top20 =====
SELECT '--- 5.12 detail_family_top20 ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_detail_family_top20 AS
SELECT poi_id, poi_name, city_name, region_name, price, comment_score,
  comment_count, heat_score, sight_level, tag_list AS tag_text,
  short_feature, latitude, longitude
FROM flat_poi_full
WHERE is_kid = 1
SORT BY heat_score DESC, comment_count DESC, comment_score DESC
LIMIT 20;
SELECT 'detail_family_top20 rows:', COUNT(*) FROM frontend_module_detail_family_top20;

-- ===== 5.13 frontend_module_detail_night_top20 =====
SELECT '--- 5.13 detail_night_top20 ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_detail_night_top20 AS
SELECT poi_id, poi_name, city_name, region_name, price, comment_score,
  comment_count, heat_score, sight_level, tag_list AS tag_text,
  short_feature, latitude, longitude
FROM flat_poi_full
WHERE is_night_tour = 1
SORT BY heat_score DESC, comment_count DESC, comment_score DESC
LIMIT 20;
SELECT 'detail_night_top20 rows:', COUNT(*) FROM frontend_module_detail_night_top20;

-- ===== 5.14 frontend_module_admin_city_summary =====
-- 与 city_summary 相同
SELECT '--- 5.14 admin_city_summary ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_admin_city_summary AS
SELECT * FROM city_summary_inner
ORDER BY poi_count DESC, comment_total DESC, city_name ASC;
SELECT 'admin_city_summary rows:', COUNT(*) FROM frontend_module_admin_city_summary;

-- ===== 5.15 frontend_module_admin_region_summary =====
SELECT '--- 5.15 admin_region_summary ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_admin_region_summary AS
SELECT city_name, region_name,
  COUNT(*) AS poi_count,
  ROUND(AVG(price), 2) AS avg_price,
  ROUND(AVG(comment_score), 2) AS avg_score,
  ROUND(AVG(heat_score), 2) AS avg_heat,
  SUM(comment_count) AS comment_total
FROM flat_poi_full
GROUP BY city_name, region_name
ORDER BY avg_heat DESC, comment_total DESC, city_name ASC, region_name ASC;
SELECT 'admin_region_summary rows:', COUNT(*) FROM frontend_module_admin_region_summary;

-- ===== 5.16 frontend_module_admin_tag_summary =====
SELECT '--- 5.16 admin_tag_summary ---' AS step;
CREATE OR REPLACE TEMPORARY VIEW frontend_module_admin_tag_summary AS
SELECT tag_name, COUNT(*) AS poi_count
FROM (
  SELECT EXPLODE(SPLIT(tag_list, '\\|')) AS tag_name FROM flat_poi_full
  WHERE tag_list IS NOT NULL AND tag_list != ''
)
WHERE tag_name IS NOT NULL AND tag_name != ''
GROUP BY tag_name
ORDER BY poi_count DESC, tag_name ASC
LIMIT 100;
SELECT 'admin_tag_summary rows:', COUNT(*) FROM frontend_module_admin_tag_summary;

-- =============================================
-- 第六部分：写入 MariaDB（21 张表）
-- =============================================
SELECT '=== 第六部分：写入 MariaDB ===' AS step;

-- JDBC 连接参数
-- url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true'
-- user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'

-- 6.1 ads_city_dashboard
SELECT '--- 6.1 写入 ads_city_dashboard ---' AS step;
DROP TABLE IF EXISTS spark_ads_city_dashboard;
CREATE TABLE spark_ads_city_dashboard USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'ads_city_dashboard', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM ads_city_dashboard;
DROP TABLE IF EXISTS map_ads_city_dashboard;
CREATE TABLE map_ads_city_dashboard USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'ads_city_dashboard', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_ads_city_dashboard SELECT * FROM ads_city_dashboard;
SELECT 'ads_city_dashboard', COUNT(*) FROM map_ads_city_dashboard;

-- 6.2 ads_province_dashboard
SELECT '--- 6.2 写入 ads_province_dashboard ---' AS step;
DROP TABLE IF EXISTS spark_ads_province_dashboard;
CREATE TABLE spark_ads_province_dashboard USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'ads_province_dashboard', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM ads_province_dashboard;
DROP TABLE IF EXISTS map_ads_province_dashboard;
CREATE TABLE map_ads_province_dashboard USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'ads_province_dashboard', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_ads_province_dashboard SELECT * FROM ads_province_dashboard;
SELECT 'ads_province_dashboard', COUNT(*) FROM map_ads_province_dashboard;

-- 6.3 ads_city_top8_poi
SELECT '--- 6.3 写入 ads_city_top8_poi ---' AS step;
DROP TABLE IF EXISTS spark_ads_city_top8_poi;
CREATE TABLE spark_ads_city_top8_poi USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'ads_city_top8_poi', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM ads_city_top8_poi;
DROP TABLE IF EXISTS map_ads_city_top8_poi;
CREATE TABLE map_ads_city_top8_poi USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'ads_city_top8_poi', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_ads_city_top8_poi SELECT * FROM ads_city_top8_poi;
SELECT 'ads_city_top8_poi', COUNT(*) FROM map_ads_city_top8_poi;

-- 6.4 ads_province_top8_poi
SELECT '--- 6.4 写入 ads_province_top8_poi ---' AS step;
DROP TABLE IF EXISTS spark_ads_province_top8_poi;
CREATE TABLE spark_ads_province_top8_poi USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'ads_province_top8_poi', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM ads_province_top8_poi;
DROP TABLE IF EXISTS map_ads_province_top8_poi;
CREATE TABLE map_ads_province_top8_poi USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'ads_province_top8_poi', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_ads_province_top8_poi SELECT * FROM ads_province_top8_poi;
SELECT 'ads_province_top8_poi', COUNT(*) FROM map_ads_province_top8_poi;

-- 6.5 ads_hot_poi_top100
SELECT '--- 6.5 写入 ads_hot_poi_top100 ---' AS step;
DROP TABLE IF EXISTS spark_ads_hot_poi_top100;
CREATE TABLE spark_ads_hot_poi_top100 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'ads_hot_poi_top100', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM ads_hot_poi_top100;
DROP TABLE IF EXISTS map_ads_hot_poi_top100;
CREATE TABLE map_ads_hot_poi_top100 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'ads_hot_poi_top100', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_ads_hot_poi_top100 SELECT * FROM ads_hot_poi_top100;
SELECT 'ads_hot_poi_top100', COUNT(*) FROM map_ads_hot_poi_top100;

-- 6.6 frontend_module_home_hot_poi_top10
SELECT '--- 6.6 写入 frontend_module_home_hot_poi_top10 ---' AS step;
DROP TABLE IF EXISTS spark_fm_hot_poi_top10;
CREATE TABLE spark_fm_hot_poi_top10 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_home_hot_poi_top10', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_home_hot_poi_top10;
DROP TABLE IF EXISTS map_fm_hot_poi_top10;
CREATE TABLE map_fm_hot_poi_top10 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_home_hot_poi_top10', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_hot_poi_top10 SELECT * FROM frontend_module_home_hot_poi_top10;
SELECT 'frontend_module_home_hot_poi_top10', COUNT(*) FROM map_fm_hot_poi_top10;

-- 6.7 frontend_module_home_tag_top20
SELECT '--- 6.7 写入 frontend_module_home_tag_top20 ---' AS step;
DROP TABLE IF EXISTS spark_fm_tag_top20;
CREATE TABLE spark_fm_tag_top20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_home_tag_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_home_tag_top20;
DROP TABLE IF EXISTS map_fm_tag_top20;
CREATE TABLE map_fm_tag_top20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_home_tag_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_tag_top20 SELECT * FROM frontend_module_home_tag_top20;
SELECT 'frontend_module_home_tag_top20', COUNT(*) FROM map_fm_tag_top20;

-- 6.8 frontend_module_home_price_distribution
SELECT '--- 6.8 写入 frontend_module_home_price_distribution ---' AS step;
DROP TABLE IF EXISTS spark_fm_price_dist;
CREATE TABLE spark_fm_price_dist USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_home_price_distribution', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_home_price_distribution;
DROP TABLE IF EXISTS map_fm_price_dist;
CREATE TABLE map_fm_price_dist USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_home_price_distribution', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_price_dist SELECT * FROM frontend_module_home_price_distribution;
SELECT 'frontend_module_home_price_distribution', COUNT(*) FROM map_fm_price_dist;

-- 6.9 frontend_module_home_score_distribution
SELECT '--- 6.9 写入 frontend_module_home_score_distribution ---' AS step;
DROP TABLE IF EXISTS spark_fm_score_dist;
CREATE TABLE spark_fm_score_dist USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_home_score_distribution', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_home_score_distribution;
DROP TABLE IF EXISTS map_fm_score_dist;
CREATE TABLE map_fm_score_dist USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_home_score_distribution', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_score_dist SELECT * FROM frontend_module_home_score_distribution;
SELECT 'frontend_module_home_score_distribution', COUNT(*) FROM map_fm_score_dist;

-- 6.10 frontend_module_city_summary
SELECT '--- 6.10 写入 frontend_module_city_summary ---' AS step;
DROP TABLE IF EXISTS spark_fm_city_summary;
CREATE TABLE spark_fm_city_summary USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_city_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT province, city_name, poi_count, avg_price, avg_score, avg_heat, free_poi_count, free_ratio, high_score_poi_count, five_a_poi_count, comment_total FROM frontend_module_city_summary;
DROP TABLE IF EXISTS map_fm_city_summary;
CREATE TABLE map_fm_city_summary USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_city_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_city_summary SELECT province, city_name, poi_count, avg_price, avg_score, avg_heat, free_poi_count, free_ratio, high_score_poi_count, five_a_poi_count, comment_total FROM frontend_module_city_summary;
SELECT 'frontend_module_city_summary', COUNT(*) FROM map_fm_city_summary;

-- 6.11 frontend_module_city_tag_summary
SELECT '--- 6.11 写入 frontend_module_city_tag_summary ---' AS step;
DROP TABLE IF EXISTS spark_fm_city_tag;
CREATE TABLE spark_fm_city_tag USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_city_tag_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_city_tag_summary;
DROP TABLE IF EXISTS map_fm_city_tag;
CREATE TABLE map_fm_city_tag USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_city_tag_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_city_tag SELECT * FROM frontend_module_city_tag_summary;
SELECT 'frontend_module_city_tag_summary', COUNT(*) FROM map_fm_city_tag;

-- 6.12 frontend_module_city_top_poi
SELECT '--- 6.12 写入 frontend_module_city_top_poi ---' AS step;
DROP TABLE IF EXISTS spark_fm_city_top_poi;
CREATE TABLE spark_fm_city_top_poi USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_city_top_poi', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_city_top_poi;
DROP TABLE IF EXISTS map_fm_city_top_poi;
CREATE TABLE map_fm_city_top_poi USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_city_top_poi', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_city_top_poi SELECT * FROM frontend_module_city_top_poi;
SELECT 'frontend_module_city_top_poi', COUNT(*) FROM map_fm_city_top_poi;

-- 6.13 frontend_module_filter_poi_base
SELECT '--- 6.13 写入 frontend_module_filter_poi_base ---' AS step;
DROP TABLE IF EXISTS spark_fm_filter_base;
CREATE TABLE spark_fm_filter_base USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_filter_poi_base', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_filter_poi_base;
DROP TABLE IF EXISTS map_fm_filter_base;
CREATE TABLE map_fm_filter_base USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_filter_poi_base', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_filter_base SELECT * FROM frontend_module_filter_poi_base;
SELECT 'frontend_module_filter_poi_base', COUNT(*) FROM map_fm_filter_base;

-- 6.14 frontend_module_detail_hot_top20
SELECT '--- 6.14 写入 frontend_module_detail_hot_top20 ---' AS step;
DROP TABLE IF EXISTS spark_fm_hot20;
CREATE TABLE spark_fm_hot20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_detail_hot_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_detail_hot_top20;
DROP TABLE IF EXISTS map_fm_hot20;
CREATE TABLE map_fm_hot20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_detail_hot_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_hot20 SELECT * FROM frontend_module_detail_hot_top20;
SELECT 'frontend_module_detail_hot_top20', COUNT(*) FROM map_fm_hot20;

-- 6.15 frontend_module_detail_value_top20
SELECT '--- 6.15 写入 frontend_module_detail_value_top20 ---' AS step;
DROP TABLE IF EXISTS spark_fm_value20;
CREATE TABLE spark_fm_value20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_detail_value_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_detail_value_top20;
DROP TABLE IF EXISTS map_fm_value20;
CREATE TABLE map_fm_value20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_detail_value_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_value20 SELECT * FROM frontend_module_detail_value_top20;
SELECT 'frontend_module_detail_value_top20', COUNT(*) FROM map_fm_value20;

-- 6.16 frontend_module_detail_free_top20
SELECT '--- 6.16 写入 frontend_module_detail_free_top20 ---' AS step;
DROP TABLE IF EXISTS spark_fm_free20;
CREATE TABLE spark_fm_free20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_detail_free_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_detail_free_top20;
DROP TABLE IF EXISTS map_fm_free20;
CREATE TABLE map_fm_free20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_detail_free_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_free20 SELECT * FROM frontend_module_detail_free_top20;
SELECT 'frontend_module_detail_free_top20', COUNT(*) FROM map_fm_free20;

-- 6.17 frontend_module_detail_family_top20
SELECT '--- 6.17 写入 frontend_module_detail_family_top20 ---' AS step;
DROP TABLE IF EXISTS spark_fm_family20;
CREATE TABLE spark_fm_family20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_detail_family_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_detail_family_top20;
DROP TABLE IF EXISTS map_fm_family20;
CREATE TABLE map_fm_family20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_detail_family_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_family20 SELECT * FROM frontend_module_detail_family_top20;
SELECT 'frontend_module_detail_family_top20', COUNT(*) FROM map_fm_family20;

-- 6.18 frontend_module_detail_night_top20
SELECT '--- 6.18 写入 frontend_module_detail_night_top20 ---' AS step;
DROP TABLE IF EXISTS spark_fm_night20;
CREATE TABLE spark_fm_night20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_detail_night_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_detail_night_top20;
DROP TABLE IF EXISTS map_fm_night20;
CREATE TABLE map_fm_night20 USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_detail_night_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_night20 SELECT * FROM frontend_module_detail_night_top20;
SELECT 'frontend_module_detail_night_top20', COUNT(*) FROM map_fm_night20;

-- 6.19 frontend_module_admin_city_summary
SELECT '--- 6.19 写入 frontend_module_admin_city_summary ---' AS step;
DROP TABLE IF EXISTS spark_fm_admin_city;
CREATE TABLE spark_fm_admin_city USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_admin_city_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT province, city_name, poi_count, avg_price, avg_score, avg_heat, free_poi_count, free_ratio, high_score_poi_count, five_a_poi_count, comment_total FROM frontend_module_admin_city_summary;
DROP TABLE IF EXISTS map_fm_admin_city;
CREATE TABLE map_fm_admin_city USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_admin_city_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_admin_city SELECT province, city_name, poi_count, avg_price, avg_score, avg_heat, free_poi_count, free_ratio, high_score_poi_count, five_a_poi_count, comment_total FROM frontend_module_admin_city_summary;
SELECT 'frontend_module_admin_city_summary', COUNT(*) FROM map_fm_admin_city;

-- 6.20 frontend_module_admin_region_summary
SELECT '--- 6.20 写入 frontend_module_admin_region_summary ---' AS step;
DROP TABLE IF EXISTS spark_fm_admin_region;
CREATE TABLE spark_fm_admin_region USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_admin_region_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_admin_region_summary;
DROP TABLE IF EXISTS map_fm_admin_region;
CREATE TABLE map_fm_admin_region USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_admin_region_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_admin_region SELECT * FROM frontend_module_admin_region_summary;
SELECT 'frontend_module_admin_region_summary', COUNT(*) FROM map_fm_admin_region;

-- 6.21 frontend_module_admin_tag_summary
SELECT '--- 6.21 写入 frontend_module_admin_tag_summary ---' AS step;
DROP TABLE IF EXISTS spark_fm_admin_tag;
CREATE TABLE spark_fm_admin_tag USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_admin_tag_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM frontend_module_admin_tag_summary;
DROP TABLE IF EXISTS map_fm_admin_tag;
CREATE TABLE map_fm_admin_tag USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'frontend_module_admin_tag_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_fm_admin_tag SELECT * FROM frontend_module_admin_tag_summary;
SELECT 'frontend_module_admin_tag_summary', COUNT(*) FROM map_fm_admin_tag;

-- =============================================
-- 第七部分：最终校验
-- =============================================
SELECT '=== 第七部分：最终校验 ===' AS step;

SELECT '=== MariaDB 写入结果 ===' AS result;
SELECT 'ads_city_dashboard' AS t, COUNT(*) AS c FROM map_ads_city_dashboard
UNION ALL SELECT 'ads_province_dashboard', COUNT(*) FROM map_ads_province_dashboard
UNION ALL SELECT 'ads_city_top8_poi', COUNT(*) FROM map_ads_city_top8_poi
UNION ALL SELECT 'ads_province_top8_poi', COUNT(*) FROM map_ads_province_top8_poi
UNION ALL SELECT 'ads_hot_poi_top100', COUNT(*) FROM map_ads_hot_poi_top100
UNION ALL SELECT 'fm_home_hot_poi_top10', COUNT(*) FROM map_fm_hot_poi_top10
UNION ALL SELECT 'fm_home_tag_top20', COUNT(*) FROM map_fm_tag_top20
UNION ALL SELECT 'fm_home_price_dist', COUNT(*) FROM map_fm_price_dist
UNION ALL SELECT 'fm_home_score_dist', COUNT(*) FROM map_fm_score_dist
UNION ALL SELECT 'fm_city_summary', COUNT(*) FROM map_fm_city_summary
UNION ALL SELECT 'fm_city_tag_summary', COUNT(*) FROM map_fm_city_tag
UNION ALL SELECT 'fm_city_top_poi', COUNT(*) FROM map_fm_city_top_poi
UNION ALL SELECT 'fm_filter_poi_base', COUNT(*) FROM map_fm_filter_base
UNION ALL SELECT 'fm_detail_hot_top20', COUNT(*) FROM map_fm_hot20
UNION ALL SELECT 'fm_detail_value_top20', COUNT(*) FROM map_fm_value20
UNION ALL SELECT 'fm_detail_free_top20', COUNT(*) FROM map_fm_free20
UNION ALL SELECT 'fm_detail_family_top20', COUNT(*) FROM map_fm_family20
UNION ALL SELECT 'fm_detail_night_top20', COUNT(*) FROM map_fm_night20
UNION ALL SELECT 'fm_admin_city_summary', COUNT(*) FROM map_fm_admin_city
UNION ALL SELECT 'fm_admin_region_summary', COUNT(*) FROM map_fm_admin_region
UNION ALL SELECT 'fm_admin_tag_summary', COUNT(*) FROM map_fm_admin_tag;

SELECT '=== 全部流程执行完毕 ===' AS finish;
