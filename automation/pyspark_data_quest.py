from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler, StringIndexer
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
import os

# ─── SPARK SESSION ───────────────────────────────────────────────────────────

spark = (
    SparkSession.builder
    .appName("DataQuest-PremierLeague")
    .config("spark.sql.shuffle.partitions", "8")   # lower for local dev
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# ─── PATHS ───────────────────────────────────────────────────────────────────

LOCAL_DATA_PATH = os.getenv("DATA_PATH", "data/premier_league_2017_2026.csv")
MODEL_OUTPUT    = os.getenv("MODEL_OUT",  "output/pl_spark_model")
REPORT_OUTPUT   = os.getenv("REPORT_OUT", "output/predictions_report.csv")

# ─── 1. INGEST ────────────────────────────────────────────────────────────────

def load_data(path: str):
    """
    Expected columns (match your actual CSV schema):
      season, date, home_team, away_team,
      home_goals, away_goals,
      home_shots, away_shots, home_shots_on_target, away_shots_on_target,
      home_corners, away_corners, home_fouls, away_fouls,
      result   ← H / D / A
    """
    df = (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(path)
    )
    print(f"✓ Loaded {df.count():,} matches from {path}")
    df.printSchema()
    return df


# ─── 2. FEATURE ENGINEERING ──────────────────────────────────────────────────

def engineer_features(df):
    """
    Build rolling form features — the same logic as the pandas pipeline
    but expressed in Spark window functions so it scales to full history.
    """

    # ── encode result as int target ──────────────────────────────────────────
    df = df.withColumn(
        "target",
        F.when(F.col("result") == "H", 2)
         .when(F.col("result") == "D", 1)
         .otherwise(0)           # Away win
    )

    # ── goal diff ────────────────────────────────────────────────────────────
    df = df.withColumn("goal_diff", F.col("home_goals") - F.col("away_goals"))

    # ── shot accuracy ────────────────────────────────────────────────────────
    df = (
        df
        .withColumn(
            "home_shot_acc",
            F.col("home_shots_on_target") / (F.col("home_shots") + 1)
        )
        .withColumn(
            "away_shot_acc",
            F.col("away_shots_on_target") / (F.col("away_shots") + 1)
        )
    )

    # ── rolling 5-match form (home points) ───────────────────────────────────
    home_window = (
        Window.partitionBy("home_team")
              .orderBy("date")
              .rowsBetween(-5, -1)
    )
    df = df.withColumn(
        "home_form_pts",
        F.avg(
            F.when(F.col("result") == "H", 3)
             .when(F.col("result") == "D", 1)
             .otherwise(0)
        ).over(home_window)
    )

    # ── rolling 5-match form (away points) ───────────────────────────────────
    away_window = (
        Window.partitionBy("away_team")
              .orderBy("date")
              .rowsBetween(-5, -1)
    )
    df = df.withColumn(
        "away_form_pts",
        F.avg(
            F.when(F.col("result") == "A", 3)
             .when(F.col("result") == "D", 1)
             .otherwise(0)
        ).over(away_window)
    )

    # ── fill nulls for first few matches of a season ─────────────────────────
    df = df.fillna({"home_form_pts": 1.0, "away_form_pts": 1.0})

    return df


# ─── 3. TRAIN / VAL / TEST SPLIT (temporal) ──────────────────────────────────

def temporal_split(df):
    """
    Mirrors the structured split from the scikit-learn pipeline:
      seasons 2017-2022 → train
      season  2023      → validation
      seasons 2024-2026 → holdout test
    """
    train = df.filter(F.col("season") <= 2022)
    val   = df.filter(F.col("season") == 2023)
    test  = df.filter(F.col("season") >= 2024)

    print(f"  Train: {train.count():,}  Val: {val.count():,}  Test: {test.count():,}")
    return train, val, test


# ─── 4. SPARK ML PIPELINE ────────────────────────────────────────────────────

FEATURE_COLS = [
    "home_shots", "away_shots",
    "home_shots_on_target", "away_shots_on_target",
    "home_corners", "away_corners",
    "home_fouls", "away_fouls",
    "goal_diff", "home_shot_acc", "away_shot_acc",
    "home_form_pts", "away_form_pts",
]


def build_pipeline(model_type: str = "rf"):
    assembler = VectorAssembler(inputCols=FEATURE_COLS, outputCol="raw_features")
    scaler    = StandardScaler(inputCol="raw_features", outputCol="features",
                               withMean=True, withStd=True)

    if model_type == "lr":
        clf = LogisticRegression(
            featuresCol="features",
            labelCol="target",
            maxIter=100,
            regParam=0.01,
        )
    else:
        clf = RandomForestClassifier(
            featuresCol="features",
            labelCol="target",
            numTrees=100,
            maxDepth=6,
            seed=42,
        )

    return Pipeline(stages=[assembler, scaler, clf])


# ─── 5. EVALUATE ─────────────────────────────────────────────────────────────

def evaluate(predictions, label: str):
    evaluator = MulticlassClassificationEvaluator(
        labelCol="target", predictionCol="prediction"
    )
    acc = evaluator.setMetricName("accuracy").evaluate(predictions)
    f1  = evaluator.setMetricName("f1").evaluate(predictions)
    print(f"  [{label}] Accuracy={acc:.4f}  F1={f1:.4f}")
    return {"label": label, "accuracy": round(acc, 4), "f1": round(f1, 4)}


# ─── 6. GENERATE REPORT ──────────────────────────────────────────────────────

def save_report(predictions, metrics: list, output_path: str):
    """
    Write a flat prediction report — every row is one match with
    the model's predicted result and probability.
    """
    report = predictions.select(
        "season", "date", "home_team", "away_team",
        "result", F.col("prediction").cast("int").alias("predicted"),
        "home_form_pts", "away_form_pts",
    )

    # coalesce to 1 part for a clean single CSV output
    (
        report.coalesce(1)
              .write
              .mode("overwrite")
              .option("header", True)
              .csv(output_path)
    )
    print(f"✓ Report saved → {output_path}")

    metrics_df = spark.createDataFrame(metrics)
    metrics_df.show()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("── Data Quest | PySpark Pipeline ──")

    # For demo purposes, generate synthetic data if the CSV doesn't exist
    if not os.path.exists(LOCAL_DATA_PATH):
        print(f"  '{LOCAL_DATA_PATH}' not found — generating synthetic data...")
        _generate_synthetic_csv(LOCAL_DATA_PATH)

    df   = load_data(LOCAL_DATA_PATH)
    df   = engineer_features(df)
    train, val, test = temporal_split(df)

    metrics = []
    for model_type, label in [("lr", "LogisticRegression"), ("rf", "RandomForest")]:
        print(f"\n── Training {label} ──")
        pipeline = build_pipeline(model_type)
        model    = pipeline.fit(train)

        val_preds  = model.transform(val)
        test_preds = model.transform(test)

        metrics.append(evaluate(val_preds,  f"{label} | Validation"))
        metrics.append(evaluate(test_preds, f"{label} | Test"))

    print("\n── Saving report ──")
    os.makedirs("output", exist_ok=True)
    save_report(test_preds, metrics, REPORT_OUTPUT)

    spark.stop()
    print("── Done ──")


# ─── SYNTHETIC DATA GENERATOR (demo only) ────────────────────────────────────

def _generate_synthetic_csv(path: str, n: int = 3_040):
    """Generates fake PL match data for local testing."""
    import random, csv
    teams = [
        "Arsenal","Chelsea","Liverpool","ManCity","ManUnited",
        "Spurs","Newcastle","Everton","Aston Villa","Brighton",
        "Wolves","Leicester","West Ham","Crystal Palace","Brentford",
        "Fulham","Bournemouth","Nottm Forest","Burnley","Luton",
    ]
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "season","date","home_team","away_team",
            "home_goals","away_goals",
            "home_shots","away_shots",
            "home_shots_on_target","away_shots_on_target",
            "home_corners","away_corners",
            "home_fouls","away_fouls","result",
        ])
        writer.writeheader()
        for season in range(2017, 2027):
            for _ in range(n // 10):
                home, away = random.sample(teams, 2)
                hg = random.randint(0, 5)
                ag = random.randint(0, 4)
                result = "H" if hg > ag else ("A" if ag > hg else "D")
                writer.writerow({
                    "season": season,
                    "date": f"{season}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                    "home_team": home, "away_team": away,
                    "home_goals": hg, "away_goals": ag,
                    "home_shots": random.randint(5, 25),
                    "away_shots": random.randint(3, 20),
                    "home_shots_on_target": random.randint(2, 10),
                    "away_shots_on_target": random.randint(1, 8),
                    "home_corners": random.randint(2, 12),
                    "away_corners": random.randint(1, 10),
                    "home_fouls": random.randint(6, 18),
                    "away_fouls": random.randint(6, 18),
                    "result": result,
                })
    print(f"✓ Synthetic data written to {path}")


if __name__ == "__main__":
    main()

