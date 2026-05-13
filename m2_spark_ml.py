#!/usr/bin/env python3
"""
============================================================
SE446 - Milestone 2: Spark ML Pipeline  (spark-submit script)
Group SES

Task 5: Feature Engineering Pipeline   - Mohammad Al-Ghamdi (mohalghamdi)
Task 6: Train and Evaluate Three Models - Mohammad Al-Ghamdi (mohalghamdi)
Task 7: Feature Importances             - Mohammad Al-Ghamdi (mohalghamdi)

Run on cluster:
    spark-submit \\
        --master yarn \\
        --deploy-mode cluster \\
        --driver-memory 512m \\
        --num-executors 1 \\
        --executor-memory 1g \\
        --executor-cores 1 \\
        --conf spark.driver.maxResultSize=128m \\
        --conf spark.yarn.appMasterEnv.PYSPARK_PYTHON=python3.12 \\
        --conf spark.executorEnv.PYSPARK_PYTHON=python3.12 \\
        m2_spark_ml.py
============================================================
"""

import sys
import os
import time
import random

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, udf
from pyspark.sql.types import (
    StructType, StructField, IntegerType, StringType, BooleanType, DoubleType
)
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, VectorAssembler
from pyspark.ml.classification import (
    LogisticRegression, RandomForestClassifier, GBTClassifier
)
from pyspark.ml.evaluation import (
    BinaryClassificationEvaluator, MulticlassClassificationEvaluator
)

# ==============================================================
# SparkSession
# ==============================================================
spark = SparkSession.builder \
    .appName('SE446_M2_SparkML_GroupSES') \
    .getOrCreate()

spark.sparkContext.setLogLevel('WARN')

DIVIDER = '=' * 65
print('\n' + DIVIDER)
print(f'Spark {spark.version}  |  Master: {spark.sparkContext.master}')
print(DIVIDER + '\n')

IS_CLUSTER = 'yarn' in spark.sparkContext.master.lower()


# ==============================================================
# Local data generator  (10 000 synthetic rows for local mode)
# ==============================================================
def generate_local_data(n=10000):
    random.seed(42)
    CRIME_TYPES = [
        'THEFT', 'BATTERY', 'CRIMINAL DAMAGE', 'ASSAULT', 'OTHER OFFENSE',
        'MOTOR VEHICLE THEFT', 'DECEPTIVE PRACTICE', 'ROBBERY', 'BURGLARY',
        'WEAPONS VIOLATION', 'NARCOTICS', 'CRIMINAL TRESPASS',
        'OFFENSE INVOLVING CHILDREN', 'HOMICIDE', 'ARSON',
    ]
    LOCATIONS = [
        'STREET', 'RESIDENCE', 'APARTMENT', 'SIDEWALK', 'OTHER',
        'PARKING LOT/GARAGE(NON.RESID.)', 'SCHOOL, PUBLIC, BUILDING',
        'RESTAURANT', 'ALLEY', 'GAS STATION',
    ]
    HIGH_ARREST = {'NARCOTICS', 'WEAPONS VIOLATION'}
    rows = []
    for i in range(n):
        ct = random.choice(CRIME_TYPES)
        arrest = random.random() < (0.42 if ct in HIGH_ARREST else 0.22)
        domestic = random.random() < 0.15
        year = random.randint(2001, 2023)
        mo = random.randint(1, 12)
        day = random.randint(1, 28)
        h = random.randint(0, 23)
        m = random.randint(0, 59)
        date_str = f'{mo:02d}/{day:02d}/{year} {h:02d}:{m:02d}:00'
        district = random.randint(1, 25)
        rows.append((
            i + 1, date_str, ct, random.choice(LOCATIONS),
            arrest, domestic, district, year, h,
        ))

    schema = StructType([
        StructField('ID', IntegerType()),
        StructField('Date', StringType()),
        StructField('Primary Type', StringType()),
        StructField('Location Description', StringType()),
        StructField('Arrest', BooleanType()),
        StructField('Domestic', BooleanType()),
        StructField('District', IntegerType()),
        StructField('Year', IntegerType()),
        StructField('Hour', IntegerType()),
    ])
    return spark.createDataFrame(rows, schema)


# ==============================================================
# Data loading
# ==============================================================
print('Loading data ...')
if IS_CLUSTER:
    df_raw = spark.read.csv(
        'hdfs:///data/chicago_crimes.csv', header=True, inferSchema=True
    )
    full_count = df_raw.count()
    print(f'Full HDFS dataset: {full_count:,} rows')

    # Sample 5% for ML tasks so training fits the cluster memory budget.
    # Phase A (Tasks 1-4) in the notebook uses the full dataset.
    df_raw = df_raw.sample(False, 0.05, seed=42)
    print(f'ML sample (5 %):   {df_raw.count():,} rows')

    # Extract hour from "MM/DD/YYYY HH:MM:SS AM/PM" date strings
    @udf(IntegerType())
    def _parse_hour(date_str):
        if not date_str:
            return 0
        try:
            parts = str(date_str).strip().split(' ')
            h = int(parts[1].split(':')[0])
            if len(parts) > 2:
                if parts[2].upper() == 'PM' and h != 12:
                    h += 12
                elif parts[2].upper() == 'AM' and h == 12:
                    h = 0
            return h % 24
        except Exception:
            return 0

    df_raw = df_raw.withColumn('Hour', _parse_hour(col('Date')))
else:
    df_raw = generate_local_data(10000)
    print(f'Generated {df_raw.count():,} synthetic rows (local mode)')

# ==============================================================
# Preprocessing
# ==============================================================
df = (
    df_raw
    .withColumn('label', col('Arrest').cast('integer'))
    .withColumn('Domestic_str', col('Domestic').cast('string'))
    .na.fill({'District': 1, 'Hour': 0, 'label': 0, 'Domestic_str': 'false'})
    .na.drop(subset=['Primary Type'])
)
print(f'Rows after cleaning: {df.count():,}\n')


# ==============================================================
# Task 5: Feature Engineering Pipeline
# Author: Mohammad Al-Ghamdi (mohalghamdi)
# ==============================================================
print(DIVIDER)
print('TASK 5: Feature Engineering Pipeline')
print('Author: Mohammad Al-Ghamdi (mohalghamdi)')
print(DIVIDER)

crime_indexer = StringIndexer(
    inputCol='Primary Type', outputCol='crime_index', handleInvalid='skip'
)
domestic_indexer = StringIndexer(
    inputCol='Domestic_str', outputCol='domestic_index', handleInvalid='skip'
)
assembler = VectorAssembler(
    inputCols=['District', 'crime_index', 'Hour', 'domestic_index'],
    outputCol='features',
)

train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)
train_df.cache()
print(f'Train: {train_df.count():,} rows  |  Test: {test_df.count():,} rows\n')

feat_pipeline = Pipeline(stages=[crime_indexer, domestic_indexer, assembler])
feat_model = feat_pipeline.fit(train_df)
train_data = feat_model.transform(train_df)
test_data = feat_model.transform(test_df)

print('Sample features vector (5 rows):')
train_data.select(
    'Primary Type', 'District', 'Hour', 'Domestic_str', 'features', 'label'
).show(5, truncate=False)
print('Feature vector positions:')
print('  [0] District      - police district number (1-25)')
print('  [1] crime_index   - encoded Primary Type (StringIndexer output)')
print('  [2] Hour          - hour of day (0-23)')
print('  [3] domestic_index - encoded Domestic flag (true=1 / false=0)\n')


# ==============================================================
# Task 6: Train and Evaluate Three Models
# Author: Mohammad Al-Ghamdi (mohalghamdi)
# ==============================================================
print(DIVIDER)
print('TASK 6: Train and Evaluate Three Models')
print('Author: Mohammad Al-Ghamdi (mohalghamdi)')
print(DIVIDER)

bin_eval  = BinaryClassificationEvaluator(labelCol='label', metricName='areaUnderROC')
acc_eval  = MulticlassClassificationEvaluator(labelCol='label', metricName='accuracy')
f1_eval   = MulticlassClassificationEvaluator(labelCol='label', metricName='f1')
prec_eval = MulticlassClassificationEvaluator(labelCol='label', metricName='weightedPrecision')
rec_eval  = MulticlassClassificationEvaluator(labelCol='label', metricName='weightedRecall')


def evaluate(model, test_data):
    preds = model.transform(test_data)
    tp = preds.filter((col('prediction') == 1) & (col('label') == 1)).count()
    tn = preds.filter((col('prediction') == 0) & (col('label') == 0)).count()
    fp = preds.filter((col('prediction') == 1) & (col('label') == 0)).count()
    fn = preds.filter((col('prediction') == 0) & (col('label') == 1)).count()
    return {
        'AUC': bin_eval.evaluate(preds),
        'Acc': acc_eval.evaluate(preds),
        'F1':  f1_eval.evaluate(preds),
        'Pre': prec_eval.evaluate(preds),
        'Rec': rec_eval.evaluate(preds),
        'TP': tp, 'TN': tn, 'FP': fp, 'FN': fn,
    }


results = {}

# --- Logistic Regression ---
print('\n[1/3] Training Logistic Regression (maxIter=100, regParam=0.01) ...')
t0 = time.time()
lr_model = LogisticRegression(
    featuresCol='features', labelCol='label', maxIter=100, regParam=0.01
).fit(train_data)
results['Logistic Regression'] = evaluate(lr_model, test_data)
results['Logistic Regression']['time'] = time.time() - t0
print(f'      Finished in {results["Logistic Regression"]["time"]:.1f}s')

# --- Random Forest ---
print('[2/3] Training Random Forest (numTrees=100, maxDepth=5) ...')
t0 = time.time()
rf_model = RandomForestClassifier(
    featuresCol='features', labelCol='label', numTrees=100, maxDepth=5, seed=42
).fit(train_data)
results['Random Forest'] = evaluate(rf_model, test_data)
results['Random Forest']['time'] = time.time() - t0
print(f'      Finished in {results["Random Forest"]["time"]:.1f}s')

# --- Gradient Boosted Trees ---
print('[3/3] Training GBT (maxIter=50, maxDepth=5) ...')
t0 = time.time()
gbt_model = GBTClassifier(
    featuresCol='features', labelCol='label', maxIter=50, maxDepth=5, seed=42
).fit(train_data)
results['GBT'] = evaluate(gbt_model, test_data)
results['GBT']['time'] = time.time() - t0
print(f'      Finished in {results["GBT"]["time"]:.1f}s')

# Comparison table
print('\n' + '=' * 88)
print(f'{"Model":<25} {"AUC-ROC":>8} {"Accuracy":>9} {"F1":>8} {"Precision":>10} {"Recall":>8} {"Time":>7}')
print('-' * 88)
for name, r in results.items():
    print(
        f'{name:<25} {r["AUC"]:>8.4f} {r["Acc"]:>9.4f} {r["F1"]:>8.4f} '
        f'{r["Pre"]:>10.4f} {r["Rec"]:>8.4f} {r["time"]:>6.1f}s'
    )
print('=' * 88)

print('\nConfusion Matrices:')
print(f'  {"Model":<25}  {"TN":>8}  {"FP":>8}  {"FN":>8}  {"TP":>8}')
print(f'  {"-"*25}  {"-"*8}  {"-"*8}  {"-"*8}  {"-"*8}')
for name, r in results.items():
    print(f'  {name:<25}  {r["TN"]:>8,}  {r["FP"]:>8,}  {r["FN"]:>8,}  {r["TP"]:>8,}')


# ==============================================================
# Task 7: Feature Importances (Random Forest)
# Author: Mohammad Al-Ghamdi (mohalghamdi)
# ==============================================================
print('\n' + DIVIDER)
print('TASK 7: Feature Importances (Random Forest)')
print('Author: Mohammad Al-Ghamdi (mohalghamdi)')
print(DIVIDER)

feature_names = ['District', 'crime_index', 'Hour', 'domestic_index']
importances   = rf_model.featureImportances.toArray()
ranked = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)

print('\nFeature Importance Ranking:')
print(f'  {"Rank":<5} {"Feature":<20} {"Importance":>11}  Bar (scaled to 50 chars)')
print(f'  {"-"*5} {"-"*20} {"-"*11}  {"-"*50}')
for rank, (name, imp) in enumerate(ranked, 1):
    bar = '#' * int(imp * 50)
    print(f'  {rank:<5} {name:<20} {imp:>11.4f}  {bar}')

top = ranked[0][0]
print(f'\nMost important feature: {top}')
print("""
Interpretation:
  - crime_index (Primary Type) dominates because arrest likelihood varies
    dramatically by crime type: NARCOTICS and WEAPONS VIOLATION offences
    result in arrest ~40% of the time, while THEFT sits below 15%.
    This matches the per-type arrest rates found in Task 4.

  - Logistic Regression underperforms tree models because the relationship
    between features and arrest probability is non-linear. Certain
    (crime_type, district, hour) combinations produce arrest rates far
    above what the sum of individual linear effects would predict.
    Tree ensembles capture these interaction effects natively, which
    is why Random Forest and GBT both score higher AUC-ROC.
""")

print(DIVIDER)
print('SE446 M2 - ML Pipeline complete.')
print(DIVIDER + '\n')

spark.stop()
