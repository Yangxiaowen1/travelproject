-- MariaDB 10.3 兼容版（没有 JSON_ARRAYAGG，用 GROUP_CONCAT 代替）
-- 先删旧表再重建，避免 id 残留
USE travel_stat;

-- =====================================================
-- 1. frontend_module_home_overview
-- =====================================================
DROP TABLE IF EXISTS frontend_module_home_overview;
CREATE TABLE frontend_module_home_overview (
  id BIGINT NOT NULL AUTO_INCREMENT, payload_json LONGTEXT NULL, PRIMARY KEY (id)
) CHARACTER SET utf8mb4;

INSERT INTO frontend_module_home_overview(payload_json)
SELECT CONCAT(
  '{"cards":{',
  '"poi_total":', (SELECT COUNT(*) FROM frontend_module_filter_poi_base), ',',
  '"city_total":', (SELECT COUNT(DISTINCT city_name) FROM frontend_module_filter_poi_base), ',',
  '"province_total":', (SELECT COUNT(DISTINCT province) FROM frontend_module_filter_poi_base), ',',
  '"free_poi_total":', (SELECT SUM(is_free) FROM frontend_module_filter_poi_base), ',',
  '"avg_price":', (SELECT ROUND(AVG(price),2) FROM frontend_module_filter_poi_base), ',',
  '"avg_score":', (SELECT ROUND(AVG(comment_score),2) FROM frontend_module_filter_poi_base), ',',
  '"avg_heat":', (SELECT ROUND(AVG(heat_score),2) FROM frontend_module_filter_poi_base),
  '},',
  '"price_distribution":[', (SELECT GROUP_CONCAT(CONCAT('{"price_level":"',price_level,'","poi_count":',poi_count,'}') SEPARATOR ',') FROM frontend_module_home_price_distribution), '],',
  '"score_distribution":[', (SELECT GROUP_CONCAT(CONCAT('{"score_level":"',score_level,'","poi_count":',poi_count,'}') SEPARATOR ',') FROM frontend_module_home_score_distribution), '],',
  '"tag_top20":[', (SELECT GROUP_CONCAT(CONCAT('{"tag_name":"',tag_name,'","poi_count":',poi_count,'}') SEPARATOR ',') FROM frontend_module_home_tag_top20), '],',
  '"hot_poi_top10":[', (SELECT GROUP_CONCAT(CONCAT('{"poi_name":"',poi_name,'","city_name":"',city_name,'","heat_score":',heat_score,',"comment_score":',comment_score,',"comment_count":',comment_count,',"price":',price,'}') SEPARATOR ',') FROM frontend_module_home_hot_poi_top10), ']',
  '}'
);

-- =====================================================
-- 2. frontend_module_filter_options
-- =====================================================
DROP TABLE IF EXISTS frontend_module_filter_options;
CREATE TABLE frontend_module_filter_options (
  id BIGINT NOT NULL AUTO_INCREMENT, payload_json LONGTEXT NULL, PRIMARY KEY (id)
) CHARACTER SET utf8mb4;

INSERT INTO frontend_module_filter_options(payload_json)
SELECT CONCAT(
  '{"province_options":[', (SELECT GROUP_CONCAT(DISTINCT CONCAT('"',province,'"') ORDER BY province SEPARATOR ',') FROM frontend_module_filter_poi_base), '],',
  '"city_options":[', (SELECT GROUP_CONCAT(DISTINCT CONCAT('"',city_name,'"') ORDER BY city_name SEPARATOR ',') FROM frontend_module_filter_poi_base), '],',
  '"price_level_options":[', (SELECT GROUP_CONCAT(DISTINCT CONCAT('"',price_level,'"') ORDER BY price_level SEPARATOR ',') FROM frontend_module_filter_poi_base), '],',
  '"score_level_options":[', (SELECT GROUP_CONCAT(DISTINCT CONCAT('"',score_level,'"') ORDER BY score_level SEPARATOR ',') FROM frontend_module_filter_poi_base), '],',
  '"distance_level_options":[', (SELECT GROUP_CONCAT(DISTINCT CONCAT('"',distance_level,'"') ORDER BY distance_level SEPARATOR ',') FROM frontend_module_filter_poi_base), '],',
  '"tag_options":[', (SELECT GROUP_CONCAT(CONCAT('"',tag_name,'"') ORDER BY poi_count DESC SEPARATOR ',') FROM frontend_module_admin_tag_summary LIMIT 100), ']',
  '}'
);

-- =====================================================
-- 3. frontend_module_detail_rankings
-- =====================================================
DROP TABLE IF EXISTS frontend_module_detail_rankings;
CREATE TABLE frontend_module_detail_rankings (
  id BIGINT NOT NULL AUTO_INCREMENT, payload_json LONGTEXT NULL, PRIMARY KEY (id)
) CHARACTER SET utf8mb4;

INSERT INTO frontend_module_detail_rankings(payload_json)
SELECT CONCAT(
  '{"hot_top20":[',
  (SELECT GROUP_CONCAT(CONCAT('{"poi_id":',poi_id,',"poi_name":"',poi_name,'","city_name":"',city_name,
    '","region_name":"',region_name,'","price":',price,',"comment_score":',comment_score,
    ',"comment_count":',comment_count,',"heat_score":',heat_score,
    ',"sight_level":"',sight_level,'","tag_text":"',tag_text,
    '","short_feature":"',short_feature,'","latitude":',latitude,',"longitude":',longitude,'}')
    SEPARATOR ',') FROM frontend_module_detail_hot_top20),
  '],"value_top20":[',
  (SELECT GROUP_CONCAT(CONCAT('{"poi_id":',poi_id,',"poi_name":"',poi_name,'","city_name":"',city_name,
    '","region_name":"',region_name,'","price":',price,',"comment_score":',comment_score,
    ',"comment_count":',comment_count,',"heat_score":',heat_score,
    ',"sight_level":"',sight_level,'","tag_text":"',tag_text,
    '","short_feature":"',short_feature,'","latitude":',latitude,',"longitude":',longitude,'}')
    SEPARATOR ',') FROM frontend_module_detail_value_top20),
  '],"free_top20":[',
  (SELECT GROUP_CONCAT(CONCAT('{"poi_id":',poi_id,',"poi_name":"',poi_name,'","city_name":"',city_name,
    '","region_name":"',region_name,'","price":',price,',"comment_score":',comment_score,
    ',"comment_count":',comment_count,',"heat_score":',heat_score,
    ',"sight_level":"',sight_level,'","tag_text":"',tag_text,
    '","short_feature":"',short_feature,'","latitude":',latitude,',"longitude":',longitude,'}')
    SEPARATOR ',') FROM frontend_module_detail_free_top20),
  '],"family_top20":[',
  (SELECT GROUP_CONCAT(CONCAT('{"poi_id":',poi_id,',"poi_name":"',poi_name,'","city_name":"',city_name,
    '","region_name":"',region_name,'","price":',price,',"comment_score":',comment_score,
    ',"comment_count":',comment_count,',"heat_score":',heat_score,
    ',"sight_level":"',sight_level,'","tag_text":"',tag_text,
    '","short_feature":"',short_feature,'","latitude":',latitude,',"longitude":',longitude,'}')
    SEPARATOR ',') FROM frontend_module_detail_family_top20),
  '],"night_top20":[',
  (SELECT GROUP_CONCAT(CONCAT('{"poi_id":',poi_id,',"poi_name":"',poi_name,'","city_name":"',city_name,
    '","region_name":"',region_name,'","price":',price,',"comment_score":',comment_score,
    ',"comment_count":',comment_count,',"heat_score":',heat_score,
    ',"sight_level":"',sight_level,'","tag_text":"',tag_text,
    '","short_feature":"',short_feature,'","latitude":',latitude,',"longitude":',longitude,'}')
    SEPARATOR ',') FROM frontend_module_detail_night_top20),
  ']}'
);

-- =====================================================
-- 4. frontend_module_manifest
-- =====================================================
DROP TABLE IF EXISTS frontend_module_manifest;
CREATE TABLE frontend_module_manifest (
  id BIGINT NOT NULL AUTO_INCREMENT, payload_json LONGTEXT NULL, PRIMARY KEY (id)
) CHARACTER SET utf8mb4;

INSERT INTO frontend_module_manifest(payload_json)
VALUES ('{"source_file":"hdfs:///travel_project/dwd/...","row_count_after_dedup":7715,"module_outputs":[
  {"module_name":"01_tourist_home","description":"游客端首页概况、价格分布、评分分布、热门景点、热门标签"},
  {"module_name":"02_city_dashboard","description":"城市看板、城市标签画像、城市热门景点榜"},
  {"module_name":"03_filter_panel","description":"景点筛选页所需的选项和基础景点列表"},
  {"module_name":"04_scenic_detail","description":"景点详情页可用的热门榜、性价比榜、亲子榜、夜游榜"},
  {"module_name":"05_admin_dashboard","description":"后台运营端所需的城市汇总、区域热度、标签运营概况"}
]}');
