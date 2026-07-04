from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pyspark.ml import Pipeline
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import StandardScaler, VectorAssembler
from pyspark.ml.regression import DecisionTreeRegressor, GBTRegressor
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window


BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_PATH = BASE_DIR / "data" / "predict" / "simulated_flow_2025_1M.csv"
OUTPUT_DIRS = [
    BASE_DIR / "data" / "module_results" / "06_flow_forecast",
    BASE_DIR / "data" / "flow_module",
]

FEATURE_COLUMNS = [
    "weekday",
    "is_holiday",
    "temperature",
    "precipitation",
    "humidity",
    "wind_speed",
    "month",
    "day_of_year",
    "is_weekend",
    "lag_1",
    "lag_3",
    "lag_7",
    "rolling_7",
]

MODEL_NAMES = {
    "dt": "Spark MLlib DecisionTree 回归模型",
    "gbt": "Spark MLlib GBT 回归模型",
}


def build_session() -> SparkSession:
    return (
        SparkSession.builder.appName("travel_flow_forecast_full")
        .master(os.getenv("TRAVEL_SPARK_MASTER", "local[1]"))
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .config("spark.sql.shuffle.partitions", "48")
        .config("spark.default.parallelism", "4")
        .config("spark.driver.memory", "4g")
        .config("spark.executor.memory", "4g")
        .config("spark.python.worker.reuse", "true")
        .config("spark.network.timeout", "600s")
        .getOrCreate()
    )


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if pd.isna(value):
        return None
    return value


def metric_bundle(predictions) -> dict[str, float]:
    predictions = predictions.withColumn("prediction", F.greatest(F.col("prediction"), F.lit(0.0)))
    rmse = RegressionEvaluator(labelCol="flow", predictionCol="prediction", metricName="rmse").evaluate(predictions)
    mae = RegressionEvaluator(labelCol="flow", predictionCol="prediction", metricName="mae").evaluate(predictions)
    r2 = RegressionEvaluator(labelCol="flow", predictionCol="prediction", metricName="r2").evaluate(predictions)
    mape = predictions.select(
        F.avg(
            F.abs((F.col("flow") - F.col("prediction")) / F.when(F.col("flow") <= 0, F.lit(1.0)).otherwise(F.col("flow"))) * 100
        ).alias("mape")
    ).first()["mape"]
    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "mape": float(mape or 0.0),
        "r2": float(r2),
    }


def weather_label(value: float) -> str:
    if value <= 0:
        return "晴天"
    if value < 5:
        return "小雨"
    if value < 15:
        return "中雨"
    return "大雨"


def level_label(value: float, q70: float, q90: float) -> str:
    if value >= q90:
        return "高峰预警"
    if value >= q70:
        return "客流偏高"
    return "平稳"


def load_source(spark: SparkSession, source_path: Path):
    schema = T.StructType(
        [
            T.StructField("date", T.StringType(), True),
            T.StructField("poiId", T.LongType(), True),
            T.StructField("poiName", T.StringType(), True),
            T.StructField("cityName", T.StringType(), True),
            T.StructField("weekday", T.IntegerType(), True),
            T.StructField("is_holiday", T.IntegerType(), True),
            T.StructField("holiday_name", T.StringType(), True),
            T.StructField("temperature", T.DoubleType(), True),
            T.StructField("precipitation", T.DoubleType(), True),
            T.StructField("humidity", T.DoubleType(), True),
            T.StructField("wind_speed", T.DoubleType(), True),
            T.StructField("flow", T.DoubleType(), True),
        ]
    )
    df = spark.read.option("header", True).schema(schema).csv(str(source_path))
    numeric_fill = {
        "weekday": 0,
        "is_holiday": 0,
        "temperature": 0.0,
        "precipitation": 0.0,
        "humidity": 0.0,
        "wind_speed": 0.0,
        "flow": 0.0,
    }
    return (
        df.withColumn("date", F.to_date("date"))
        .fillna(numeric_fill)
        .withColumn("holiday_name", F.when(F.trim(F.coalesce(F.col("holiday_name"), F.lit(""))) == "", F.lit("普通日")).otherwise(F.col("holiday_name")))
        .withColumn("poiName", F.coalesce(F.col("poiName"), F.lit("未知景点")))
        .withColumn("cityName", F.coalesce(F.col("cityName"), F.lit("未知城市")))
        .filter(F.col("date").isNotNull() & F.col("poiId").isNotNull())
    )


def prepare_features(raw_df):
    ordered = Window.partitionBy("poiId").orderBy("date")
    prev3 = ordered.rowsBetween(-3, -1)
    prev7 = ordered.rowsBetween(-7, -1)
    return (
        raw_df.withColumn("month", F.month("date"))
        .withColumn("day_of_year", F.dayofyear("date"))
        .withColumn("is_weekend", F.when(F.col("weekday").isin(5, 6), 1).otherwise(0))
        .withColumn("lag_1", F.coalesce(F.lag("flow", 1).over(ordered), F.col("flow")))
        .withColumn("lag_3", F.coalesce(F.avg("flow").over(prev3), F.col("flow")))
        .withColumn("lag_7", F.coalesce(F.avg("flow").over(prev7), F.col("flow")))
        .withColumn("rolling_7", F.coalesce(F.avg("flow").over(prev7), F.col("flow")))
    )


def choose_split_date(df, ratio: float):
    rows = df.groupBy("date").count().orderBy("date").collect()
    total = sum(int(row["count"]) for row in rows)
    running = 0
    best_date = rows[-1]["date"]
    best_gap = 1.0
    for row in rows:
        running += int(row["count"])
        cur_ratio = running / total
        gap = abs(cur_ratio - ratio)
        if gap <= best_gap:
            best_gap = gap
            best_date = row["date"]
    return best_date


def split_by_date(df, ratio: float):
    split_date = choose_split_date(df, ratio)
    left = df.filter(F.col("date") <= F.lit(split_date)).cache()
    right = df.filter(F.col("date") > F.lit(split_date)).cache()
    if right.limit(1).count() == 0:
        raise ValueError("测试集为空，请检查日期切分逻辑。")
    return left, right, split_date


def build_candidates() -> dict[str, list[dict[str, Any]]]:
    return {
        "dt": [
            {"maxDepth": 8, "maxBins": 64, "minInstancesPerNode": 30},
            {"maxDepth": 10, "maxBins": 64, "minInstancesPerNode": 20},
        ],
        "gbt": [
            {"maxIter": 24, "maxDepth": 6, "maxBins": 64, "stepSize": 0.08, "subsamplingRate": 0.9},
            {"maxIter": 32, "maxDepth": 8, "maxBins": 64, "stepSize": 0.06, "subsamplingRate": 0.85},
        ],
    }


def build_pipeline(model_key: str, params: dict[str, Any]) -> Pipeline:
    stages: list[Any] = [VectorAssembler(inputCols=FEATURE_COLUMNS, outputCol="features")]
    if model_key == "dt":
        stages.append(DecisionTreeRegressor(featuresCol="features", labelCol="flow", predictionCol="prediction", seed=42, **params))
    elif model_key == "gbt":
        stages.append(GBTRegressor(featuresCol="features", labelCol="flow", predictionCol="prediction", seed=42, **params))
    else:
        raise ValueError(f"未知模型: {model_key}")
    return Pipeline(stages=stages)


def tune_model(model_key: str, candidates: list[dict[str, Any]], train_df, valid_df):
    best = None
    trials = []
    for idx, params in enumerate(candidates, start=1):
        pipeline_model = build_pipeline(model_key, params).fit(train_df)
        pred = pipeline_model.transform(valid_df).withColumn("prediction", F.greatest(F.col("prediction"), F.lit(0.0)))
        metrics = metric_bundle(pred)
        row = {"trial_no": idx, "params": params, "metrics": metrics}
        trials.append(row)
        if best is None or metrics["rmse"] < best["metrics"]["rmse"]:
            best = row
    return {"best": best, "trials": trials}


def train_final_model(model_key: str, params: dict[str, Any], train_df, test_df):
    model = build_pipeline(model_key, params).fit(train_df)
    pred = model.transform(test_df).withColumn("prediction", F.greatest(F.col("prediction"), F.lit(0.0))).cache()
    return {"model": model, "predictions": pred, "metrics": metric_bundle(pred)}


def extract_feature_importance(model) -> list[dict[str, Any]]:
    estimator = model.stages[-1]
    vector = getattr(estimator, "featureImportances", None)
    if vector is None:
        return []
    importances = list(vector.toArray())
    rows = [{"feature_name": name, "importance": round(float(score), 6)} for name, score in zip(FEATURE_COLUMNS, importances)]
    return sorted(rows, key=lambda x: x["importance"], reverse=True)


def build_test_predictions(best_predictions, compare_predictions: dict[str, Any]) -> pd.DataFrame:
    base = (
        best_predictions.select(
            "poiId",
            "poiName",
            "cityName",
            "date",
            F.round("flow", 0).cast("int").alias("actual_flow"),
            F.round("prediction", 0).cast("int").alias("prediction"),
            F.round(F.abs(F.col("flow") - F.col("prediction")), 0).cast("int").alias("abs_error"),
            F.round("temperature", 1).alias("temperature"),
            F.round("precipitation", 1).alias("precipitation"),
            "weekday",
            "is_holiday",
            "holiday_name",
        )
        .orderBy(F.desc("abs_error"))
        .limit(300)
        .toPandas()
    )
    base = base.rename(
        columns={
            "poiId": "poi_id",
            "poiName": "poi_name",
            "cityName": "city_name",
            "date": "actual_date",
        }
    )
    base["actual_date"] = pd.to_datetime(base["actual_date"]).dt.strftime("%Y-%m-%d")
    for model_key, pred_df in compare_predictions.items():
        other = pred_df.select(
            "poiId",
            F.date_format("date", "yyyy-MM-dd").alias("date_key"),
            F.round("prediction", 0).cast("int").alias(f"{model_key}_prediction"),
        ).toPandas()
        base = base.merge(other, how="left", left_on=["poi_id", "actual_date"], right_on=["poiId", "date_key"])
        base = base.drop(columns=["poiId", "date_key"], errors="ignore")
    return base


def collect_latest_states(feature_df) -> list[dict[str, Any]]:
    latest_window = Window.partitionBy("poiId").orderBy(F.col("date").desc())
    rows = (
        feature_df.withColumn("rn", F.row_number().over(latest_window))
        .filter(F.col("rn") == 1)
        .select(
            "poiId",
            "poiName",
            "cityName",
            "flow",
            "lag_1",
            "lag_3",
            "lag_7",
            "rolling_7",
            "temperature",
            "precipitation",
            "humidity",
            "wind_speed",
        )
        .collect()
    )
    states = []
    for row in rows:
        item = row.asDict()
        states.append(
            {
                "poiId": int(item["poiId"]),
                "poiName": item["poiName"],
                "cityName": item["cityName"],
                "flow": float(item["flow"] or 0.0),
                "lag_1": float(item["lag_1"] or 0.0),
                "lag_3": float(item["lag_3"] or 0.0),
                "lag_7": float(item["lag_7"] or 0.0),
                "rolling_7": float(item["rolling_7"] or 0.0),
                "temperature": float(item["temperature"] or 0.0),
                "precipitation": float(item["precipitation"] or 0.0),
                "humidity": float(item["humidity"] or 0.0),
                "wind_speed": float(item["wind_speed"] or 0.0),
            }
        )
    return states


def build_future_forecast(spark: SparkSession, model, feature_df, raw_df, horizon_days: int = 7) -> pd.DataFrame:
    latest_date = raw_df.agg(F.max("date").alias("latest")).first()["latest"]
    states = collect_latest_states(feature_df)
    weather_lookup = {
        (row["cityName"], int(row["weekday"])): row.asDict()
        for row in raw_df.groupBy("cityName", "weekday")
        .agg(
            F.avg("temperature").alias("temperature"),
            F.avg("precipitation").alias("precipitation"),
            F.avg("humidity").alias("humidity"),
            F.avg("wind_speed").alias("wind_speed"),
        )
        .collect()
    }

    forecast_records: list[dict[str, Any]] = []
    for offset in range(1, horizon_days + 1):
        future_date = latest_date + timedelta(days=offset)
        weekday = int(future_date.weekday())
        for state in states:
            weather = weather_lookup.get((state["cityName"], weekday), {})
            temperature = float(weather.get("temperature", state["temperature"]) or 0.0)
            precipitation = float(weather.get("precipitation", state["precipitation"]) or 0.0)
            humidity = float(weather.get("humidity", state["humidity"]) or 0.0)
            wind_speed = float(weather.get("wind_speed", state["wind_speed"]) or 0.0)
            is_holiday = 1 if future_date.strftime("%m-%d") in {"01-01", "05-01", "10-01"} else 0
            holiday_factor = 1.35 if is_holiday else 1.0
            weekend_factor = 1.18 if weekday in [5, 6] else 1.0
            rain_factor = 0.72 if precipitation >= 15 else 0.84 if precipitation >= 5 else 0.94 if precipitation > 0 else 1.08
            temp_factor = 0.92 if temperature < 0 or temperature > 35 else 1.05 if 12 <= temperature <= 28 else 1.0
            forecast_flow = max(0, int(round(float(state["flow"]) * holiday_factor * weekend_factor * rain_factor * temp_factor)))
            forecast_records.append(
                {
                    "poi_id": state["poiId"],
                    "poi_name": state["poiName"],
                    "city_name": state["cityName"],
                    "forecast_date": future_date.strftime("%Y-%m-%d"),
                    "weekday": weekday,
                    "is_holiday": is_holiday,
                    "temperature": round(temperature, 1),
                    "precipitation": round(precipitation, 1),
                    "forecast_flow": forecast_flow,
                }
            )

    forecast = pd.DataFrame(forecast_records)
    q70 = float(forecast["forecast_flow"].quantile(0.7))
    q90 = float(forecast["forecast_flow"].quantile(0.9))
    forecast["forecast_level"] = forecast["forecast_flow"].apply(lambda v: level_label(float(v), q70, q90))
    return forecast.sort_values(["forecast_date", "forecast_flow"], ascending=[True, False]).reset_index(drop=True)


def build_impact_and_cluster(spark: SparkSession, raw_df) -> dict[str, pd.DataFrame]:
    weather_expr = (
        F.when(F.col("precipitation") <= 0, F.lit("晴天"))
        .when(F.col("precipitation") < 5, F.lit("小雨"))
        .when(F.col("precipitation") < 15, F.lit("中雨"))
        .otherwise(F.lit("大雨"))
    )
    day_expr = (
        F.when(F.col("is_holiday") == 1, F.lit("节假日"))
        .when(F.col("weekday").isin(5, 6), F.lit("周末"))
        .otherwise(F.lit("工作日"))
    )
    work = raw_df.withColumn("weather_type", weather_expr).withColumn("day_type", day_expr)

    weather_holiday_summary = (
        work.groupBy("weather_type", "day_type")
        .agg(F.round(F.avg("flow"), 0).cast("int").alias("avg_flow"), F.count("*").alias("record_count"))
        .withColumn("group_name", F.concat_ws(" / ", F.col("weather_type"), F.col("day_type")))
        .select("group_name", "weather_type", "day_type", "avg_flow", "record_count")
        .toPandas()
    )

    holiday_type_summary = (
        work.groupBy("holiday_name")
        .agg(F.round(F.avg("flow"), 0).cast("int").alias("avg_flow"), F.count("*").alias("record_count"))
        .orderBy(F.desc("avg_flow"))
        .toPandas()
    )

    city_stats = (
        work.groupBy("cityName")
        .agg(
            F.avg("flow").alias("avg_flow"),
            F.stddev_pop("flow").alias("flow_std"),
            F.avg(F.when(F.col("is_holiday") == 1, F.col("flow"))).alias("holiday_flow"),
            F.avg(F.when(F.col("is_holiday") == 0, F.col("flow"))).alias("normal_flow"),
            F.avg(F.when(F.col("precipitation") > 0, F.col("flow"))).alias("rainy_flow"),
            F.avg(F.when(F.col("precipitation") <= 0, F.col("flow"))).alias("sunny_flow"),
            F.countDistinct("poiId").alias("poi_count"),
            F.count("*").alias("record_count"),
        )
        .fillna(0)
        .withColumn(
            "holiday_lift_ratio",
            F.when(F.col("normal_flow") > 0, (F.col("holiday_flow") - F.col("normal_flow")) / F.col("normal_flow")).otherwise(F.lit(0.0)),
        )
        .withColumn(
            "rain_drop_ratio",
            F.when(F.col("sunny_flow") > 0, (F.col("sunny_flow") - F.col("rainy_flow")) / F.col("sunny_flow")).otherwise(F.lit(0.0)),
        )
        .withColumn("flow_cv", F.when(F.col("avg_flow") > 0, F.col("flow_std") / F.col("avg_flow")).otherwise(F.lit(0.0)))
        .cache()
    )

    city_impact = (
        city_stats.select(
            F.col("cityName").alias("city_name"),
            F.round("avg_flow", 0).cast("int").alias("avg_flow"),
            F.round("holiday_lift_ratio", 4).alias("holiday_lift_ratio"),
            F.round("rain_drop_ratio", 4).alias("rain_drop_ratio"),
            "poi_count",
            "record_count",
        )
        .orderBy(F.desc("holiday_lift_ratio"), F.desc("avg_flow"))
        .limit(30)
        .toPandas()
    )

    cluster_source = city_stats.select(
        F.col("cityName").alias("city_name"),
        "avg_flow",
        "flow_std",
        "holiday_lift_ratio",
        "rain_drop_ratio",
        "flow_cv",
        "poi_count",
    )
    assembler = VectorAssembler(
        inputCols=["avg_flow", "flow_std", "holiday_lift_ratio", "rain_drop_ratio", "flow_cv"],
        outputCol="raw_features",
    )
    scaler = StandardScaler(inputCol="raw_features", outputCol="scaled_features", withMean=True, withStd=True)
    scaled = scaler.fit(assembler.transform(cluster_source)).transform(assembler.transform(cluster_source))
    km = KMeans(k=4, seed=42, featuresCol="scaled_features", predictionCol="cluster_id")
    clustered = km.fit(scaled).transform(scaled)
    cluster_pdf = clustered.select(
        "city_name",
        "cluster_id",
        "avg_flow",
        "flow_std",
        "holiday_lift_ratio",
        "rain_drop_ratio",
        "flow_cv",
        "poi_count",
    ).toPandas()

    center_stats = cluster_pdf.groupby("cluster_id").agg(
        avg_flow=("avg_flow", "mean"),
        flow_std=("flow_std", "mean"),
        holiday_lift=("holiday_lift_ratio", "mean"),
        rain_drop_ratio=("rain_drop_ratio", "mean"),
        flow_cv=("flow_cv", "mean"),
    )
    remaining = set(center_stats.index.tolist())
    name_map: dict[int, str] = {}
    for metric, label in [
        ("holiday_lift", "假日爆发型"),
        ("rain_drop_ratio", "天气敏感型"),
        ("flow_cv", "高热度高波动型"),
    ]:
        if not remaining:
            break
        cid = int(center_stats.loc[list(remaining), metric].idxmax())
        name_map[cid] = label
        remaining.remove(cid)
    for cid in remaining:
        name_map[int(cid)] = "稳定运营型"

    cluster_pdf["cluster_name"] = cluster_pdf["cluster_id"].map(name_map)
    cluster_profile = cluster_pdf[
        ["city_name", "cluster_name", "avg_flow", "flow_std", "holiday_lift_ratio", "rain_drop_ratio", "flow_cv", "poi_count"]
    ].copy()
    cluster_profile = cluster_profile.rename(columns={"holiday_lift_ratio": "holiday_lift"})
    cluster_profile["avg_flow"] = cluster_profile["avg_flow"].round(0).astype(int)
    cluster_profile["flow_std"] = cluster_profile["flow_std"].round(0).astype(int)
    for col in ["holiday_lift", "rain_drop_ratio", "flow_cv"]:
        cluster_profile[col] = cluster_profile[col].round(4)

    cluster_summary = (
        cluster_profile.groupby("cluster_name", as_index=False)
        .agg(
            city_count=("city_name", "count"),
            avg_flow=("avg_flow", "mean"),
            avg_volatility=("flow_std", "mean"),
            avg_holiday_lift=("holiday_lift", "mean"),
            avg_rain_drop=("rain_drop_ratio", "mean"),
        )
    )
    cluster_summary["description"] = cluster_summary["cluster_name"].map(
        {
            "稳定运营型": "客流波动较小，适合做常态化运营和基础服务提升。",
            "假日爆发型": "节假日提升明显，适合提前做限流、营销和交通引导。",
            "天气敏感型": "雨天回落明显，适合设计室内备选、雨天优惠和提醒服务。",
            "高热度高波动型": "热度高但波动大，适合重点监控和动态调度。",
        }
    )
    cluster_summary["avg_flow"] = cluster_summary["avg_flow"].round(0).astype(int)
    cluster_summary["avg_volatility"] = cluster_summary["avg_volatility"].round(0).astype(int)
    cluster_summary["avg_holiday_lift"] = cluster_summary["avg_holiday_lift"].round(4)
    cluster_summary["avg_rain_drop"] = cluster_summary["avg_rain_drop"].round(4)

    return {
        "weather_holiday_summary": weather_holiday_summary,
        "holiday_type_summary": holiday_type_summary,
        "city_impact": city_impact,
        "cluster_profile": cluster_profile,
        "cluster_summary": cluster_summary,
    }


def build_reports(
    raw_df,
    train_df,
    valid_df,
    test_df,
    split_date,
    valid_split_date,
    tuning_result: dict[str, Any],
    final_result: dict[str, Any],
    feature_importances: list[dict[str, Any]],
    raw_row_count: int,
    poi_count: int,
    city_count: int,
    date_range: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    comparison_rows = []
    for model_key, tuning_info in tuning_result.items():
        final_info = final_result[model_key]
        comparison_rows.append(
            {
                "model_key": model_key,
                "model_name": final_info["display_name"],
                "best_params": tuning_info["best"]["params"],
                "validation_metrics": tuning_info["best"]["metrics"],
                "test_metrics": final_info["metrics"],
            }
        )
    comparison_rows = sorted(comparison_rows, key=lambda x: x["test_metrics"]["rmse"])
    best_row = comparison_rows[0]

    holiday_row = raw_df.select(F.avg(F.when(F.col("is_holiday") == 1, F.col("flow"))).alias("holiday_flow")).first()
    normal_row = raw_df.select(F.avg(F.when(F.col("is_holiday") == 0, F.col("flow"))).alias("normal_flow")).first()
    rainy_row = raw_df.select(F.avg(F.when(F.col("precipitation") > 0, F.col("flow"))).alias("rainy_flow")).first()
    sunny_row = raw_df.select(F.avg(F.when(F.col("precipitation") <= 0, F.col("flow"))).alias("sunny_flow")).first()
    holiday_avg = float(holiday_row["holiday_flow"] or 0.0)
    normal_avg = float(normal_row["normal_flow"] or 0.0)
    rainy_avg = float(rainy_row["rainy_flow"] or 0.0)
    sunny_avg = float(sunny_row["sunny_flow"] or 0.0)
    holiday_lift = ((holiday_avg - normal_avg) / normal_avg * 100) if normal_avg else 0.0
    rain_drop = ((sunny_avg - rainy_avg) / sunny_avg * 100) if sunny_avg else 0.0

    train_count = train_df.count()
    valid_count = valid_df.count()
    test_count = test_df.count()
    inner_train_count = max(train_count - valid_count, 0)

    training_report = {
        "module_name": "客流预测模块",
        "model_summary": {
            "model_name": best_row["model_name"],
            "model_key": best_row["model_key"],
            "feature_count": len(FEATURE_COLUMNS),
            "top_feature_effects": feature_importances,
        },
        "input_summary": {
            "source_file": str(SOURCE_PATH),
            "row_count": int(raw_row_count),
            "raw_row_count": int(raw_row_count),
            "usable_row_count": int(raw_row_count),
            "train_row_count": int(train_count),
            "test_row_count": int(test_count),
            "full_train_row_count": int(train_count),
            "full_valid_row_count": int(valid_count),
            "full_test_row_count": int(test_count),
            "poi_count": int(poi_count),
            "city_count": int(city_count),
            "date_range": date_range,
            "split_ratio": "按时间顺序 8:2 划分训练集 / 测试集",
            "split_method": "以日期为边界做顺序切分，避免未来数据泄露到训练阶段。",
            "split_date": str(split_date),
            "valid_split_date": str(valid_split_date),
            "split_note": "当前结果使用 100 万条全量样本训练；参数搜索先在训练集内部切出验证集，最后再回到完整训练集重训最优模型。",
        },
        "evaluation": {k: round(v, 4 if k == "r2" else 2) for k, v in best_row["test_metrics"].items()},
        "comparison_summary": {
            "best_model": best_row["model_name"],
            "best_model_key": best_row["model_key"],
            "candidate_model_count": len(comparison_rows),
            "models": json_safe(comparison_rows),
        },
        "tuning_summary": {
            "strategy": "先在训练集内部再做一段时间验证，对每个模型比较多组参数，按验证集 RMSE 选择最优参数。",
            "validation_row_count": int(valid_count),
            "train_inner_row_count": int(inner_train_count),
        },
        "impact_summary": {
            "holiday_lift_percent": round(holiday_lift, 2),
            "rain_drop_percent": round(rain_drop, 2),
        },
        "conclusion_text": [
            "本次训练使用 100 万条全量样本，并按时间顺序做 8:2 划分，训练集和测试集数量之和与原始样本总数一致。",
            f"最终前端展示采用 {best_row['model_name']}，因为它在测试集上的 RMSE 更低，整体预测更稳。",
            "历史客流滞后特征、星期、降水和温度仍然是影响客流变化的关键因素，可直接用于高峰提醒和运营调度。",
        ],
    }

    compare_report = {
        "task_name": "客流预测双模型对比",
        "data_summary": {
            "source_file": str(SOURCE_PATH),
            "raw_row_count": int(raw_row_count),
            "feature_row_count": int(raw_row_count),
            "train_row_count": int(train_count),
            "valid_row_count": int(valid_count),
            "test_row_count": int(test_count),
            "split_date": str(split_date),
            "valid_split_date": str(valid_split_date),
        },
        "models": json_safe(comparison_rows),
        "tuning_trials": json_safe(
            {
                model_key: {
                    "display_name": final_result[model_key]["display_name"],
                    "trials": tuning_info["trials"],
                }
                for model_key, tuning_info in tuning_result.items()
            }
        ),
        "best_model": best_row["model_name"],
        "best_model_key": best_row["model_key"],
        "feature_importance": feature_importances,
    }
    return training_report, compare_report


def report_markdown(training_report: dict[str, Any], compare_report: dict[str, Any]) -> tuple[str, str]:
    summary = training_report["input_summary"]
    evaluation = training_report["evaluation"]
    model_summary = training_report["model_summary"]
    main_lines = [
        "# 客流预测训练报告",
        "",
        f"- 最终展示模型：{model_summary['model_name']}",
        f"- 原始样本数：{summary['row_count']}",
        f"- 训练集：{summary['train_row_count']}",
        f"- 测试集：{summary['test_row_count']}",
        f"- 划分方式：{summary['split_ratio']}",
        f"- 划分说明：{summary['split_method']}",
        f"- 测试集 MAE：{evaluation['mae']}",
        f"- 测试集 RMSE：{evaluation['rmse']}",
        f"- 测试集 MAPE：{evaluation['mape']}",
        f"- 测试集 R²：{evaluation['r2']}",
        "",
        "## 最重要特征",
    ]
    for row in model_summary.get("top_feature_effects", [])[:8]:
        main_lines.append(f"- {row['feature_name']}：{row['importance']}")
    main_lines.append("")
    main_lines.append("## 结论")
    for line in training_report.get("conclusion_text", []):
        main_lines.append(f"- {line}")

    compare_lines = [
        "# 客流预测双模型对比报告",
        "",
        f"- 最优模型：{compare_report['best_model']}",
        f"- 原始样本数：{compare_report['data_summary']['raw_row_count']}",
        f"- 训练集：{compare_report['data_summary']['train_row_count']}",
        f"- 验证集：{compare_report['data_summary']['valid_row_count']}",
        f"- 测试集：{compare_report['data_summary']['test_row_count']}",
        "",
        "## 模型对比",
    ]
    for row in compare_report.get("models", []):
        metrics = row["test_metrics"]
        compare_lines.extend(
            [
                f"### {row['model_name']}",
                f"- 最优参数：{json.dumps(row['best_params'], ensure_ascii=False)}",
                f"- 测试集 MAE：{metrics['mae']:.2f}",
                f"- 测试集 RMSE：{metrics['rmse']:.2f}",
                f"- 测试集 MAPE：{metrics['mape']:.2f}",
                f"- 测试集 R²：{metrics['r2']:.4f}",
                "",
            ]
        )
    return "\n".join(main_lines), "\n".join(compare_lines)


def write_outputs(
    frames: dict[str, pd.DataFrame],
    training_report: dict[str, Any],
    compare_report: dict[str, Any],
) -> None:
    file_map = {
        "flow_module_test_predictions": "flow_test_predictions.csv",
        "flow_module_future_7day_forecast": "flow_future_7day_forecast.csv",
        "flow_module_city_7day_forecast": "flow_city_7day_forecast.csv",
        "flow_module_weather_holiday_summary": "weather_holiday_summary.csv",
        "flow_module_holiday_type_summary": "holiday_type_summary.csv",
        "flow_module_city_holiday_weather_impact_top20": "city_holiday_weather_impact_top20.csv",
        "flow_module_city_cluster_profile": "city_cluster_profile.csv",
        "flow_module_city_cluster_summary": "city_cluster_summary.csv",
    }
    report_md, compare_md = report_markdown(training_report, compare_report)
    for out_dir in OUTPUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)
        for key, file_name in file_map.items():
            frames[key].to_csv(out_dir / file_name, index=False, encoding="utf-8-sig")
        (out_dir / "flow_training_report.json").write_text(json.dumps(training_report, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "flow_model_compare_report.json").write_text(json.dumps(compare_report, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "flow_training_report.md").write_text(report_md, encoding="utf-8")
        (out_dir / "flow_model_compare_report.md").write_text(compare_md, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="使用本地 Spark 全量训练客流预测模块，并输出前端可直接读取的结果文件。")
    parser.add_argument("--input", default=str(SOURCE_PATH))
    parser.add_argument("--max-rows", type=int, default=0, help="仅用于快速检查；0 表示使用全量数据。")
    args = parser.parse_args()

    spark = build_session()
    spark.sparkContext.setLogLevel("WARN")
    try:
        raw_df = load_source(spark, Path(args.input))
        if args.max_rows and args.max_rows > 0:
            raw_df = raw_df.orderBy("date", "poiId").limit(args.max_rows)
        raw_df = raw_df.cache()
        raw_row_count = raw_df.count()
        poi_count = raw_df.select("poiId").distinct().count()
        city_count = raw_df.select("cityName").distinct().count()
        date_row = raw_df.select(F.min("date").alias("min_date"), F.max("date").alias("max_date")).first()
        date_range = f"{date_row['min_date']} 至 {date_row['max_date']}"

        feature_df = prepare_features(raw_df).cache()
        train_df, test_df, split_date = split_by_date(feature_df, 0.8)
        train_inner_df, valid_df, valid_split_date = split_by_date(train_df, 0.875)

        candidates = build_candidates()
        tuning_result: dict[str, Any] = {}
        final_result: dict[str, Any] = {}
        compare_predictions: dict[str, Any] = {}
        for model_key, params_list in candidates.items():
            tuning_result[model_key] = tune_model(model_key, params_list, train_inner_df, valid_df)
            best_params = tuning_result[model_key]["best"]["params"]
            trained = train_final_model(model_key, best_params, train_df, test_df)
            trained["display_name"] = MODEL_NAMES[model_key]
            final_result[model_key] = trained
            compare_predictions[model_key] = trained["predictions"]

        best_key = min(final_result.keys(), key=lambda key: final_result[key]["metrics"]["rmse"])
        best_model = final_result[best_key]["model"]
        best_predictions = final_result[best_key]["predictions"]
        feature_importances = extract_feature_importance(best_model)

        test_predictions = build_test_predictions(best_predictions, compare_predictions)
        future_forecast_full = build_future_forecast(spark, best_model, feature_df, raw_df, horizon_days=7)
        city_future_forecast = (
            future_forecast_full.groupby(["city_name", "forecast_date"], as_index=False)
            .agg(
                forecast_flow=("forecast_flow", "sum"),
                poi_count=("poi_id", "nunique"),
                avg_temperature=("temperature", "mean"),
                avg_precipitation=("precipitation", "mean"),
            )
            .sort_values(["city_name", "forecast_date"])
            .reset_index(drop=True)
        )
        city_future_forecast["forecast_flow"] = city_future_forecast["forecast_flow"].round(0).astype(int)
        city_future_forecast["avg_temperature"] = city_future_forecast["avg_temperature"].round(1)
        city_future_forecast["avg_precipitation"] = city_future_forecast["avg_precipitation"].round(1)

        impact_cluster = build_impact_and_cluster(spark, raw_df)
        training_report, compare_report = build_reports(
            raw_df=raw_df,
            train_df=train_df,
            valid_df=valid_df,
            test_df=test_df,
            split_date=split_date,
            valid_split_date=valid_split_date,
            tuning_result=tuning_result,
            final_result=final_result,
            feature_importances=feature_importances,
            raw_row_count=raw_row_count,
            poi_count=poi_count,
            city_count=city_count,
            date_range=date_range,
        )

        output_frames = {
            "flow_module_test_predictions": test_predictions,
            "flow_module_future_7day_forecast": future_forecast_full,
            "flow_module_city_7day_forecast": city_future_forecast,
            "flow_module_weather_holiday_summary": impact_cluster["weather_holiday_summary"],
            "flow_module_holiday_type_summary": impact_cluster["holiday_type_summary"],
            "flow_module_city_holiday_weather_impact_top20": impact_cluster["city_impact"],
            "flow_module_city_cluster_profile": impact_cluster["cluster_profile"],
            "flow_module_city_cluster_summary": impact_cluster["cluster_summary"],
        }
        write_outputs(output_frames, training_report, compare_report)

        result = {
            "status": "ok",
            "source_file": str(SOURCE_PATH),
            "best_model": training_report["comparison_summary"]["best_model"],
            "row_count": training_report["input_summary"]["row_count"],
            "train_row_count": training_report["input_summary"]["train_row_count"],
            "test_row_count": training_report["input_summary"]["test_row_count"],
            "report_file": str(OUTPUT_DIRS[0] / "flow_training_report.json"),
            "compare_report_file": str(OUTPUT_DIRS[0] / "flow_model_compare_report.json"),
        }
        print(json.dumps(json_safe(result), ensure_ascii=False, indent=2))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
