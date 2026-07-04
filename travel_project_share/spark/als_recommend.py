"""Spark ALS 景点推荐（读取 HDFS 用户表数据）"""
import argparse
import json
from pathlib import Path

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window

HDFS_ROOT = "/travel_project/users"
DEFAULT_FAV = f"{HDFS_ROOT}/user_favorites/user_favorites.csv"
DEFAULT_CMT = f"{HDFS_ROOT}/user_poi_comments/user_poi_comments.csv"


def build_session() -> SparkSession:
    return (
        SparkSession.builder.appName("travel_als_recommend")
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        .config("spark.executor.memory", "2g")
        .getOrCreate()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="基于 Spark ALS 的景点推荐")
    parser.add_argument("--favorites", default=DEFAULT_FAV, help="user_favorites.csv 路径（默认 HDFS）")
    parser.add_argument("--comments", default=DEFAULT_CMT, help="user_poi_comments.csv 路径（默认 HDFS）")
    parser.add_argument("--output", required=True, help="输出目录")
    parser.add_argument("--topn", type=int, default=8, help="每个用户推荐数量")
    parser.add_argument("--rank", type=int, default=20, help="ALS 隐藏因子数")
    parser.add_argument("--maxIter", type=int, default=20, help="训练迭代次数")
    args = parser.parse_args()

    spark = build_session()
    spark.sparkContext.setLogLevel("WARN")

    # 1. 读取收藏数据
    fav_raw = spark.read.option("header", True).csv(args.favorites)
    fav = (
        fav_raw.select(
            F.col("user_id").cast("int").alias("user_id"),
            F.col("poi_id").cast("long").alias("poi_id"),
            F.lit(4.0).alias("rating"),
        )
        .filter((F.col("user_id") > 0) & (F.col("poi_id") > 0))
    )
    records = [fav]
    print(f"收藏数据: {fav.count()} 行")

    # 2. 读取评论数据（如果有）
    if args.comments:
        cmt_raw = spark.read.option("header", True).csv(args.comments)
        cmt = (
            cmt_raw.select(
                F.col("user_id").cast("int").alias("user_id"),
                F.col("poi_id").cast("long").alias("poi_id"),
                F.col("rating").cast("double").alias("rating"),
            )
            .filter((F.col("user_id") > 0) & (F.col("poi_id") > 0) & (F.col("rating") > 0))
        )
        records.append(cmt)
        print(f"评论数据: {cmt.count()} 行")

    # 3. 合并：同一用户-景点取最高评分
    interactions = records[0]
    if len(records) > 1:
        interactions = records[0].unionByName(records[1])
    interactions = (
        interactions.groupBy("user_id", "poi_id")
        .agg(F.max("rating").alias("rating"))
        .cache()
    )

    n_users = interactions.select("user_id").distinct().count()
    n_poi = interactions.select("poi_id").distinct().count()
    n_inter = interactions.count()
    print(f"训练数据: {n_inter} 条, {n_users} 用户, {n_poi} 景点")

    if n_inter < 10:
        print("❌ 交互数据太少，无法训练")
        return

    # 4. 训练/测试切分
    train, test = interactions.randomSplit([0.8, 0.2], seed=42)

    # 5. ALS 训练
    als = ALS(
        userCol="user_id",
        itemCol="poi_id",
        ratingCol="rating",
        rank=args.rank,
        maxIter=args.maxIter,
        regParam=0.1,
        coldStartStrategy="drop",
        nonnegative=True,
        seed=42,
    )
    model = als.fit(train)
    print("✅ ALS 训练完成")

    # 6. 评估
    metrics = {}
    if test.count() > 0:
        pred = model.transform(test)
        rmse = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction").evaluate(pred)
        mae = RegressionEvaluator(metricName="mae", labelCol="rating", predictionCol="prediction").evaluate(pred)
        metrics = {"rmse": round(rmse, 4), "mae": round(mae, 4)}
        print(f"RMSE: {rmse:.4f}, MAE: {mae:.4f}")

    # 7. 给所有用户推荐 TOP N
    user_recs = model.recommendForAllUsers(args.topn)

    # 8. 展开推荐结果
    recs_flat = (
        user_recs.select(
            F.col("user_id"),
            F.explode(F.col("recommendations")).alias("rec")
        )
        .select(
            F.col("user_id"),
            F.row_number().over(Window.partitionBy("user_id").orderBy(F.desc("rec.rating"))).alias("rank"),
            F.col("rec.poi_id").cast("long").alias("poi_id"),
            F.round(F.col("rec.rating"), 6).alias("score"),
        )
    )

    out_path = Path(args.output)
    out_path.mkdir(parents=True, exist_ok=True)

    # 输出 CSV
    csv_path = out_path / "als_recommendations.csv"
    recs_flat.toPandas().to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"✅ 推荐结果: {csv_path} ({recs_flat.count()} 条)")

    # 训练报告
    report = {
        "model": "Spark MLlib ALS",
        "data": {"users": int(n_users), "pois": int(n_poi), "interactions": int(n_inter)},
        "params": {"rank": args.rank, "maxIter": args.maxIter, "topn": args.topn},
        "metrics": metrics,
        "output": str(csv_path),
        "note": "训练完成后的推荐结果可直接用 spark-sql JDBC 写入 MariaDB",
    }
    report_path = out_path / "als_training_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    spark.stop()


if __name__ == "__main__":
    main()
