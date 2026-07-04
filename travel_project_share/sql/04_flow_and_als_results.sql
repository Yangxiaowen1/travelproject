-- =====================================================
-- 04. flow_module + als_recommendations 结果写入 + 行程空表
-- 读取本地/共享目录 CSV → spark-sql JDBC 写入 MariaDB
-- =====================================================
USE travel_stat;

-- =====================================================
-- 第一部分：客流预测 8 张 CSV 表
-- =====================================================

-- 1.1 flow_module_city_7day_forecast
SELECT '--- 1.1 flow_module_city_7day_forecast ---' AS step;
DROP TABLE IF EXISTS spark_flow_01;
CREATE TABLE spark_flow_01
USING csv OPTIONS (path 'file:///opt/project/travel_project/data/flow_module/flow_city_7day_forecast.csv', header 'true');
DROP TABLE IF EXISTS spark_flow_01_tmp;
CREATE TABLE spark_flow_01_tmp
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_city_7day_forecast', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM spark_flow_01 WHERE 1=0;
DROP TABLE IF EXISTS map_flow_01;
CREATE TABLE map_flow_01
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_city_7day_forecast', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_flow_01 SELECT * FROM spark_flow_01;
SELECT 'flow_module_city_7day_forecast', COUNT(*) FROM map_flow_01;

-- 1.2 flow_module_future_7day_forecast
SELECT '--- 1.2 flow_module_future_7day_forecast ---' AS step;
DROP TABLE IF EXISTS spark_flow_02;
CREATE TABLE spark_flow_02
USING csv OPTIONS (path 'file:///opt/project/travel_project/data/flow_module/flow_future_7day_forecast.csv', header 'true');
DROP TABLE IF EXISTS spark_flow_02_tmp;
CREATE TABLE spark_flow_02_tmp
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_future_7day_forecast', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM spark_flow_02 WHERE 1=0;
DROP TABLE IF EXISTS map_flow_02;
CREATE TABLE map_flow_02
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_future_7day_forecast', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_flow_02 SELECT * FROM spark_flow_02;
SELECT 'flow_module_future_7day_forecast', COUNT(*) FROM map_flow_02;

-- 1.3 flow_module_test_predictions
SELECT '--- 1.3 flow_module_test_predictions ---' AS step;
DROP TABLE IF EXISTS spark_flow_03;
CREATE TABLE spark_flow_03
USING csv OPTIONS (path 'file:///opt/project/travel_project/data/flow_module/flow_test_predictions.csv', header 'true');
DROP TABLE IF EXISTS spark_flow_03_tmp;
CREATE TABLE spark_flow_03_tmp
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_test_predictions', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM spark_flow_03 WHERE 1=0;
DROP TABLE IF EXISTS map_flow_03;
CREATE TABLE map_flow_03
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_test_predictions', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_flow_03 SELECT * FROM spark_flow_03;
SELECT 'flow_module_test_predictions', COUNT(*) FROM map_flow_03;

-- 1.4 flow_module_weather_holiday_summary
SELECT '--- 1.4 flow_module_weather_holiday_summary ---' AS step;
DROP TABLE IF EXISTS spark_flow_04;
CREATE TABLE spark_flow_04
USING csv OPTIONS (path 'file:///opt/project/travel_project/data/flow_module/weather_holiday_summary.csv', header 'true');
DROP TABLE IF EXISTS spark_flow_04_tmp;
CREATE TABLE spark_flow_04_tmp
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_weather_holiday_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM spark_flow_04 WHERE 1=0;
DROP TABLE IF EXISTS map_flow_04;
CREATE TABLE map_flow_04
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_weather_holiday_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_flow_04 SELECT * FROM spark_flow_04;
SELECT 'flow_module_weather_holiday_summary', COUNT(*) FROM map_flow_04;

-- 1.5 flow_module_holiday_type_summary
SELECT '--- 1.5 flow_module_holiday_type_summary ---' AS step;
DROP TABLE IF EXISTS spark_flow_05;
CREATE TABLE spark_flow_05
USING csv OPTIONS (path 'file:///opt/project/travel_project/data/flow_module/holiday_type_summary.csv', header 'true');
DROP TABLE IF EXISTS spark_flow_05_tmp;
CREATE TABLE spark_flow_05_tmp
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_holiday_type_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM spark_flow_05 WHERE 1=0;
DROP TABLE IF EXISTS map_flow_05;
CREATE TABLE map_flow_05
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_holiday_type_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_flow_05 SELECT * FROM spark_flow_05;
SELECT 'flow_module_holiday_type_summary', COUNT(*) FROM map_flow_05;

-- 1.6 flow_module_city_holiday_weather_impact_top20
SELECT '--- 1.6 flow_module_city_holiday_weather_impact_top20 ---' AS step;
DROP TABLE IF EXISTS spark_flow_06;
CREATE TABLE spark_flow_06
USING csv OPTIONS (path 'file:///opt/project/travel_project/data/flow_module/city_holiday_weather_impact_top20.csv', header 'true');
DROP TABLE IF EXISTS spark_flow_06_tmp;
CREATE TABLE spark_flow_06_tmp
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_city_holiday_weather_impact_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM spark_flow_06 WHERE 1=0;
DROP TABLE IF EXISTS map_flow_06;
CREATE TABLE map_flow_06
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_city_holiday_weather_impact_top20', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_flow_06 SELECT * FROM spark_flow_06;
SELECT 'flow_module_city_holiday_weather_impact_top20', COUNT(*) FROM map_flow_06;

-- 1.7 flow_module_city_cluster_profile
SELECT '--- 1.7 flow_module_city_cluster_profile ---' AS step;
DROP TABLE IF EXISTS spark_flow_07;
CREATE TABLE spark_flow_07
USING csv OPTIONS (path 'file:///opt/project/travel_project/data/flow_module/city_cluster_profile.csv', header 'true');
DROP TABLE IF EXISTS spark_flow_07_tmp;
CREATE TABLE spark_flow_07_tmp
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_city_cluster_profile', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM spark_flow_07 WHERE 1=0;
DROP TABLE IF EXISTS map_flow_07;
CREATE TABLE map_flow_07
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_city_cluster_profile', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_flow_07 SELECT * FROM spark_flow_07;
SELECT 'flow_module_city_cluster_profile', COUNT(*) FROM map_flow_07;

-- 1.8 flow_module_city_cluster_summary
SELECT '--- 1.8 flow_module_city_cluster_summary ---' AS step;
DROP TABLE IF EXISTS spark_flow_08;
CREATE TABLE spark_flow_08
USING csv OPTIONS (path 'file:///opt/project/travel_project/data/flow_module/city_cluster_summary.csv', header 'true');
DROP TABLE IF EXISTS spark_flow_08_tmp;
CREATE TABLE spark_flow_08_tmp
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_city_cluster_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM spark_flow_08 WHERE 1=0;
DROP TABLE IF EXISTS map_flow_08;
CREATE TABLE map_flow_08
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'flow_module_city_cluster_summary', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_flow_08 SELECT * FROM spark_flow_08;
SELECT 'flow_module_city_cluster_summary', COUNT(*) FROM map_flow_08;

-- 1.9 flow_module_training_report (JSON 表)
SELECT '--- 1.9 flow_module_training_report ---' AS step;
CREATE TABLE IF NOT EXISTS flow_module_training_report (
  id BIGINT NOT NULL AUTO_INCREMENT, payload_json LONGTEXT NULL, PRIMARY KEY (id)
) CHARACTER SET utf8mb4;

-- =====================================================
-- 第二部分：ALS 推荐结果
-- =====================================================
SELECT '--- 2.1 als_recommendations ---' AS step;
DROP TABLE IF EXISTS spark_als;
CREATE TABLE spark_als
USING csv OPTIONS (path 'file:///opt/project/travel_project_share/data/module_results/07_recommendation/als_recommendations_live.csv', header 'true');
DROP TABLE IF EXISTS spark_als_tmp;
CREATE TABLE spark_als_tmp
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'als_recommendations', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
) AS SELECT * FROM spark_als WHERE 1=0;
DROP TABLE IF EXISTS map_als;
CREATE TABLE map_als
USING jdbc OPTIONS (
    url 'jdbc:mysql://192.168.56.101:3306/travel_stat?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true',
    dbtable 'als_recommendations', user 'agri', password 'Agri@123456', driver 'com.mysql.cj.jdbc.Driver'
);
INSERT INTO map_als SELECT * FROM spark_als;
SELECT 'als_recommendations', COUNT(*) FROM map_als;

-- =====================================================
-- 第三部分：行程规划空表（DDL）
-- =====================================================

-- 3.1 travel_plans
SELECT '--- 3.1 travel_plans ---' AS step;
CREATE TABLE IF NOT EXISTS travel_plans (
  id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  city_name VARCHAR(100) NOT NULL,
  days INT NOT NULL,
  theme VARCHAR(100) NULL,
  budget_level VARCHAR(50) NULL,
  total_budget DOUBLE NULL,
  status VARCHAR(20) DEFAULT 'draft',
  plan_json LONGTEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) CHARACTER SET utf8mb4;
SELECT 'travel_plans created' AS result;

-- 3.2 travel_plan_items
SELECT '--- 3.2 travel_plan_items ---' AS step;
CREATE TABLE IF NOT EXISTS travel_plan_items (
  id BIGINT NOT NULL AUTO_INCREMENT,
  plan_id BIGINT NOT NULL,
  day_no INT NOT NULL,
  sort_no INT NOT NULL,
  time_slot VARCHAR(50) NULL,
  poi_id BIGINT NULL,
  poi_name VARCHAR(255) NULL,
  duration_min INT NULL,
  transport VARCHAR(100) NULL,
  meal_type VARCHAR(50) NULL,
  cost DOUBLE NULL,
  note TEXT NULL,
  PRIMARY KEY (id)
) CHARACTER SET utf8mb4;
SELECT 'travel_plan_items created' AS result;

-- =====================================================
-- 最终校验
-- =====================================================
SELECT '=== 04 号脚本执行完毕 ===' AS finish;
