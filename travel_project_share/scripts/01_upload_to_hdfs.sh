#!/bin/bash
# ===================================================
# 一键创建 HDFS 目录 + 上传 DIM/DWD CSV 文件
# 用法: bash scripts/upload_to_hdfs.sh
# 虚拟机根目录: /opt/project/travel_project
# HDFS 根目录: /travel_project
# ===================================================
set -e

LOCAL_ROOT="/opt/project/travel_project"
HDFS_ROOT="/travel_project"
HADOOP_BIN="/opt/module/hadoop/bin/hdfs"

# 检查本地数据目录
echo "=== 检查本地数据目录 ==="
for dir in \
  "$LOCAL_ROOT/data/dim/dim_sight_level" \
  "$LOCAL_ROOT/data/dim/dim_price_bucket" \
  "$LOCAL_ROOT/data/dim/dim_score_bucket" \
  "$LOCAL_ROOT/data/dim/dim_distance_center" \
  "$LOCAL_ROOT/data/dim/dim_city" \
  "$LOCAL_ROOT/data/dim/dim_district" \
  "$LOCAL_ROOT/data/dim/dim_region" \
  "$LOCAL_ROOT/data/dim/dim_tag" \
  "$LOCAL_ROOT/data/dwd/dwd_poi_base_info" \
  "$LOCAL_ROOT/data/dwd/dwd_poi_price_daily" \
  "$LOCAL_ROOT/data/dwd/dwd_poi_comment_daily" \
  "$LOCAL_ROOT/data/dwd/dwd_poi_tag_relation" \
  "$LOCAL_ROOT/data/dwd/dwd_poi_media_info"; do
  if [ -d "$dir" ]; then
    echo "  ✅ $dir"
  else
    echo "  ⚠️  $dir 不存在，将创建"
    mkdir -p "$dir"
  fi
done

# 创建 HDFS 目录
echo ""
echo "=== 创建 HDFS 目录 ==="

# DIM 目录
for dir in dim_sight_level dim_price_bucket dim_score_bucket dim_distance_center \
           dim_city dim_district dim_region dim_tag; do
  echo "  mkdir $HDFS_ROOT/dim/$dir"
  $HADOOP_BIN dfs -mkdir -p "$HDFS_ROOT/dim/$dir"
done

# DWD 目录
for dir in dwd_poi_base_info dwd_poi_price_daily dwd_poi_comment_daily \
           dwd_poi_tag_relation dwd_poi_media_info; do
  echo "  mkdir $HDFS_ROOT/dwd/$dir"
  $HADOOP_BIN dfs -mkdir -p "$HDFS_ROOT/dwd/$dir"
done

# 上传 CSV 文件（取每个目录下第一个 part-*.csv 文件，合并成同名 CSV）
echo ""
echo "=== 上传 DIM CSV 文件 ==="
DIM_TABLES=("dim_sight_level" "dim_price_bucket" "dim_score_bucket" "dim_distance_center" "dim_city" "dim_district" "dim_region" "dim_tag")
for table in "${DIM_TABLES[@]}"; do
  src_dir="$LOCAL_ROOT/data/dim/$table"
  src_file=$(ls "$src_dir"/part-*.csv 2>/dev/null | head -1)
  dst="$HDFS_ROOT/dim/$table/$table.csv"
  if [ -n "$src_file" ]; then
    $HADOOP_BIN dfs -put -f "$src_file" "$dst"
    echo "  ✅ $table.csv -> hdfs:$dst"
  else
    echo "  ⚠️  $table: 未找到 part-*.csv 文件"
  fi
done

echo ""
echo "=== 上传 DWD CSV 文件 ==="
DWD_TABLES=("dwd_poi_base_info" "dwd_poi_price_daily" "dwd_poi_comment_daily" "dwd_poi_tag_relation" "dwd_poi_media_info")
for table in "${DWD_TABLES[@]}"; do
  src_dir="$LOCAL_ROOT/data/dwd/$table"
  src_file=$(ls "$src_dir"/part-*.csv 2>/dev/null | head -1)
  dst="$HDFS_ROOT/dwd/$table/$table.csv"
  if [ -n "$src_file" ]; then
    $HADOOP_BIN dfs -put -f "$src_file" "$dst"
    echo "  ✅ $table.csv -> hdfs:$dst"
  else
    echo "  ⚠️  $table: 未找到 part-*.csv 文件"
  fi
done

echo ""
echo "=== 验证 HDFS 文件 ==="
echo ""
echo "--- DIM ---"
$HADOOP_BIN dfs -ls "$HDFS_ROOT/dim/"*/ | awk '{print $NF}'
echo ""
echo "--- DWD ---"
$HADOOP_BIN dfs -ls "$HDFS_ROOT/dwd/"*/ | awk '{print $NF}'

echo ""
echo "=== 全部完成 ==="
