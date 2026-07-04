#!/bin/bash
# ===================================================
# 2. Spark SQL 全流程执行并写入 MariaDB
# bash /opt/project/travel_project/scripts/02_run_spark_pipeline.sh
# 02_run_spark_pipeline.sh:用 spark-sql 按顺序执行 01→02→03 三个 SQL 文件
#   01_full_pipeline_all_tables.sql → 计算 21 张 ADS+前端模块表写入 travel_stat
#   02_json_tables_mariadb.sql     → 在 MariaDB 拼 4 张 JSON 表
#   03_init_result_tables.sql      → 从 HDFS 读用户 CSV 写入 user 表
# 依赖: 01_upload_to_hdfs.sh 已执行（HDFS 已有 DIM/DWD/users 数据）
# 用法: bash scripts/02_run_spark_pipeline.sh
# ===================================================
set -e

SQL_DIR="/opt/project/travel_project/sql"
SPARK_SQL="/opt/module/spark/bin/spark-sql"
LOG_DIR="/opt/project/travel_project/logs"

mkdir -p "$LOG_DIR"

echo "========================================"
echo " Spark SQL 管道开始执行"
echo " 时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 检查 spark-sql 是否存在
if [ ! -f "$SPARK_SQL" ]; then
  echo "❌ spark-sql 不存在: $SPARK_SQL"
  echo "   请检查 SPARK_HOME 路径"
  exit 1
fi

# 按顺序执行 3 个 SQL 文件
FILES=(
  "01_full_pipeline_all_tables.sql"
  "02_json_tables_mariadb.sql"
  "03_init_result_tables.sql"
)

for sql_file in "${FILES[@]}"; do
  full_path="$SQL_DIR/$sql_file"
  log_file="$LOG_DIR/${sql_file%.sql}_$(date '+%Y%m%d_%H%M%S').log"

  if [ ! -f "$full_path" ]; then
    echo "⚠️  跳过: $sql_file（文件不存在）"
    continue
  fi

  echo ""
  echo "--- 执行: $sql_file ---"
  echo "    日志: $log_file"
  echo "    开始: $(date '+%H:%M:%S')"

  start_ts=$(date +%s)
  $SPARK_SQL -f "$full_path" > "$log_file" 2>&1
  exit_code=$?
  end_ts=$(date +%s)
  elapsed=$((end_ts - start_ts))

  if [ $exit_code -eq 0 ]; then
    echo " ✅ 完成 ($(printf '%02d:%02d' $((elapsed/60)) $((elapsed%60))))"
  else
    echo " ❌ 失败 (退出码: $exit_code)"
    echo "    查看日志: $log_file"
    exit $exit_code
  fi
done

echo ""
echo "========================================"
echo " 全部 SQL 执行完毕"
echo " 结束时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
