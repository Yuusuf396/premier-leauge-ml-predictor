#!/usr/bin/env python3
"""
Data Quest PySpark ML Pipeline
Reimplements the Premier League predictor using PySpark for scalable distributed computing.
Uses temporal train/val/test splits, rolling form features, and Spark ML Pipeline API.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Tuple

import pandas as pd
from pyspark.sql import SparkSession, Window, DataFrame
from pyspark.sql.functions import (
    col, lag, avg, when, row_number, lit, count,
    to_date, datediff, cast
)
from pyspark.sql.types import IntegerType, DoubleType, StringType
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
import numpy as np


# Configuration
LOCAL_DATA_PATH = os.getenv("DATA_PATH", "ml/data/premier_league_2017_2026.csv")
OUTPUT_DIR = "ml/outputs"
SPARK_MEMORY = "4g"
SPARK_CORES = "*"


def create_spark_session() -> SparkSession:
    """Create or retrieve Spark session."""
    return SparkSession.builder \
        .appName("DataQuest-PL-Pipeline") \
        .config("spark.driver.memory", SPARK_MEMORY) \
        .config("spark.sql.shuffle.partitions", 200) \
        .getOrCreate()


def generate_synthetic_data(num_matches: int = 3040) -> pd.DataFrame:
    """Generate synthetic Premier League match data for testing."""
    np.random.seed(42)
    
    teams = [
        "Arsenal", "Aston Villa", "Bournemouth", "Brighton", "Chelsea",
        "Crystal Palace", "Everton", "Fulham", "Ipswich", "Leicester",
        "Liverpool", "Manchester City", "Manchester United", "Newcastle",
        "Nottingham", "Southampton", "Tottenham", "West Ham", "Wolves"
    ]
    
    dates = []
    home_teams = []
    away_teams = []
    home_goals = []
    away_goals = []
    home_shots = []
    away_shots = []
    home_shots_on_target = []
    away_shots_on_target = []
    home_corners = []
    away_corners = []
    home_fouls = []
    away_fouls = []
    results = []
    
    start_date = datetime(2017, 8, 1)
    
    for i in range(num_matches):
        date = start_date + timedelta(days=np.random.randint(0, 365))
        home = np.random.choice(teams)
        away = np.random.choice([t for t in teams if t != home])
        
        hg = np.random.poisson(1.5)
        ag = np.random.poisson(1.2)
        
        result = "H" if hg > ag else ("D" if hg == ag else "A")
        
        dates.append(date)
        home_teams.append(home)
        away_teams.append(away)
        home_goals.append(int(hg))
        away_goals.append(int(ag))
        home_shots.append(np.random.randint(8, 20))
        away_shots.append(np.random.randint(8, 20))
        home_shots_on_target.append(np.random.randint(2, 8))
        away_shots_on_target.append(np.random.randint(2, 8))
        home_corners.append(np.random.randint(2, 12))
        away_corners.append(np.random.randint(2, 12))
        home_fouls.append(np.random.randint(8, 16))
        away_fouls.append(np.random.randint(8, 16))
        results.append(result)
    
    return pd.DataFrame({
        "date": dates,
        "home_team": home_teams,
        "away_team": away_teams,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_shots": home_shots,
        "away_shots": away_shots,
        "home_shots_on_target": home_shots_on_target,
        "away_shots_on_target": away_shots_on_target,
        "home_corners": home_corners,
        "away_corners": away_corners,
        "home_fouls": home_fouls,
        "away_fouls": away_fouls,
        "result": results,
    })


def load_data(spark: SparkSession) -> DataFrame:
    """Load match data from CSV or generate synthetic data."""
    if os.path.exists(LOCAL_DATA_PATH):
        print(f"  Loading data from {LOCAL_DATA_PATH}")
        df = spark.read.csv(LOCAL_DATA_PATH, header=True, inferSchema=True)
    else:
        print(f"  Generating synthetic data ({LOCAL_DATA_PATH} not found)")
        pdf = generate_synthetic_data()
        df = spark.createDataFrame(pdf)
    
    # Ensure date column is a date type
    df = df.withColumn("date", to_date(col("date")))
    
    # Create target: 0 = Not Home Win, 1 = Home Win
    df = df.withColumn("label", when(col("result") == "H", 1).otherwise(0))
    
    return df.sort("date")


def create_rolling_features(df: DataFrame, window_size: int = 5) -> DataFrame:
    """
    Create rolling form features using Spark Window functions.
    - Home team: avg goals scored in last N matches
    - Away team: avg goals conceded in last N matches
    """
    
    # Home team rolling average (goals scored when playing at home)
    home_window = Window.partitionBy("home_team").orderBy("date").rangeBetween(-window_size * 365, -1)
    df = df.withColumn(
        "home_form_scored",
        avg("home_goals").over(home_window)
    )
    
    # Away team rolling average (goals conceded when playing away)
    away_window = Window.partitionBy("away_team").orderBy("date").rangeBetween(-window_size * 365, -1)
    df = df.withColumn(
        "away_form_conceded",
        avg("away_goals").over(away_window)
    )
    
    # Fill NaN values with 0 (for matches without history)
    df = df.fillna(0)
    
    return df


def create_temporal_splits(df: DataFrame) -> Tuple[DataFrame, DataFrame, DataFrame]:
    """
    Create temporal train/val/test splits (no data leakage).
    Assumes 9 seasons (2017-2026): ~380 matches/season
    """
    
    # Get date bounds
    date_range = df.select("date").distinct().sort("date")
    dates = [row["date"] for row in date_range.collect()]
    
    total_matches = df.count()
    train_size = int(0.5 * total_matches)    # 50% train
    val_size = int(0.1 * total_matches)      # 10% val
    
    split_date_1 = dates[train_size - 1] if train_size < len(dates) else dates[-1]
    split_date_2 = dates[train_size + val_size - 1] if train_size + val_size < len(dates) else dates[-1]
    
    train_df = df.filter(col("date") <= split_date_1)
    val_df = df.filter((col("date") > split_date_1) & (col("date") <= split_date_2))
    test_df = df.filter(col("date") > split_date_2)
    
    return train_df, val_df, test_df


def build_and_train_model(
    spark: SparkSession,
    train_df: DataFrame,
    val_df: DataFrame,
    test_df: DataFrame,
    model_class,
    model_name: str,
) -> Tuple[PipelineModel, dict]:
    """Build and train a single model with Spark ML Pipeline."""
    
    print(f"\n── Training {model_name} ──")
    
    # Feature columns
    feature_cols = [
        "home_shots", "away_shots",
        "home_shots_on_target", "away_shots_on_target",
        "home_corners", "away_corners",
        "home_fouls", "away_fouls",
        "home_form_scored", "away_form_conceded"
    ]
    
    # Build pipeline
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")
    scaler = StandardScaler(inputCol="features", outputCol="scaledFeatures")
    
    model_instance = model_class(featuresCol="scaledFeatures", labelCol="label")
    
    pipeline = Pipeline(stages=[assembler, scaler, model_instance])
    
    # Train
    trained_model = pipeline.fit(train_df)
    
    # Evaluate
    evaluator = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction")
    
    val_predictions = trained_model.transform(val_df)
    val_accuracy = evaluator.evaluate(val_predictions, {evaluator.metricName: "accuracy"})
    val_f1 = evaluator.evaluate(val_predictions, {evaluator.metricName: "f1"})
    
    test_predictions = trained_model.transform(test_df)
    test_accuracy = evaluator.evaluate(test_predictions, {evaluator.metricName: "accuracy"})
    test_f1 = evaluator.evaluate(test_predictions, {evaluator.metricName: "f1"})
    
    print(f"  [{model_name} | Validation]  Accuracy={val_accuracy:.4f}  F1={val_f1:.4f}")
    print(f"  [{model_name} | Test]        Accuracy={test_accuracy:.4f}  F1={test_f1:.4f}")
    
    return trained_model, {
        "model_name": model_name,
        "val_accuracy": val_accuracy,
        "val_f1": val_f1,
        "test_accuracy": test_accuracy,
        "test_f1": test_f1,
    }


def save_results(test_predictions: DataFrame, results_list: list):
    """Save predictions and metrics to CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Save predictions
    predictions_path = f"{OUTPUT_DIR}/predictions_report.csv"
    test_predictions.select("date", "home_team", "away_team", "result", "prediction", "probability") \
        .coalesce(1) \
        .write.csv(predictions_path, header=True, mode="overwrite")
    
    # Save metrics
    metrics_df = pd.DataFrame(results_list)
    metrics_path = f"{OUTPUT_DIR}/metrics_{datetime.now().strftime('%Y-%m-%d')}.csv"
    metrics_df.to_csv(metrics_path, index=False)
    
    print(f"✓ Report saved → {predictions_path}")


def main():
    """Main pipeline execution."""
    print("\n── Data Quest | PySpark Pipeline ──")
    
    spark = create_spark_session()
    
    try:
        # Load data
        df = load_data(spark)
        print(f"✓ Loaded {df.count():,} matches")
        
        # Create features
        df = create_rolling_features(df)
        
        # Temporal split
        train_df, val_df, test_df = create_temporal_splits(df)
        train_count = train_df.count()
        val_count = val_df.count()
        test_count = test_df.count()
        
        print(f"  Train: {train_count:,}  Val: {val_count:,}  Test: {test_count:,}")
        
        # Train models
        results = []
        
        lr_model, lr_metrics = build_and_train_model(
            spark, train_df, val_df, test_df,
            LogisticRegression, "LogisticRegression"
        )
        results.append(lr_metrics)
        
        rf_model, rf_metrics = build_and_train_model(
            spark, train_df, val_df, test_df,
            RandomForestClassifier, "RandomForest"
        )
        results.append(rf_metrics)
        
        # Save best model's predictions
        best_model = lr_model if lr_metrics["test_f1"] >= rf_metrics["test_f1"] else rf_model
        test_predictions = best_model.transform(test_df)
        save_results(test_predictions, results)
        
        print("\n── Done ──\n")
    
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
