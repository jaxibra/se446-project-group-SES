# SE446 — Chicago Crime Analytics (Group SES)

## Team Members

| Member | Username | M1 Tasks | M2 Tasks |
|--------|----------|----------|----------|
| Ahmad Al-Younis | ayounis | Task 2 (Crime Type Distribution) | Tasks 1–2 (DataFrame + SQL Analytics) |
| Nawaf | nawaf | Task 3 (Location Hotspots) | Tasks 3–4 (Trends + Arrest Rate) |
| Mohammad Al-Ghamdi | mohalghamdi | Task 4 (Crime Trends by Year) | Tasks 5–7 (ML Pipeline) |
| Thabet Al-Salmalki | tsalmalki | Task 5 (Arrest Rate) | Tasks 9–11 (Deployment) |

---

## Executive Summary

This project analyses the Chicago Crimes dataset (7 M+ records) using two generations of big-data technology. Milestone 1 built a Hadoop MapReduce pipeline to count crimes by type, location, year, and arrest outcome. Milestone 2 reproduces those analyses with Spark DataFrames (faster, in-memory), then extends them with an MLlib pipeline that predicts arrest outcomes using Logistic Regression, Random Forest, and Gradient Boosted Trees.

---

## Milestone 1 — MapReduce Pipeline

### Tools
- Hadoop Streaming (Python mappers + shared reducer)
- HDFS dataset: `hdfs:///data/chicago_crimes.csv`

### Tasks
| Task | Analysis | Key Result |
|------|----------|------------|
| Task 2 | Crime Type Distribution | THEFT (most common), BATTERY, CRIMINAL DAMAGE |
| Task 3 | Location Hotspots | STREET is the most common crime location |
| Task 4 | Crime Trends by Year | Trend extracted from Date field per year |
| Task 5 | Arrest Rate | 215 199 arrested / 577 874 not arrested → **27.1% arrest rate** |

---

## Milestone 2 — Spark + MLlib

### Tools
- PySpark 3.5+, Spark MLlib
- Notebook: `M2_Spark_ML_GroupSES.ipynb`
- Standalone script: `m2_spark_ml.py` (for spark-submit)

---

## M1 vs M2 Comparison (Tasks 1–4)

| Analysis | M1 (MapReduce) | M2 (Spark DataFrame) | Match? |
|----------|---------------|----------------------|--------|
| Crime Type Distribution | Counted via mapper/reducer, wrote to HDFS | `df.groupBy("Primary Type").count()` in seconds | ✅ Identical counts on same data |
| Location Hotspots | Mapper emits location tab 1, reducer sums | `spark.sql("SELECT ... GROUP BY ...")` | ✅ Same ranking |
| Crime Trend by Year | Date string parsed in mapper, year tab 1 | `df.groupBy("Year").count()` with chart | ✅ Same counts |
| Arrest Rate | Two keys (Arrested / Not Arrested) | `df.filter(col("Arrest")).count()` + per-type | ✅ 27.1% overall rate |

**Speed**: Spark finishes all four analyses in under 2 minutes on the full dataset. M1 MapReduce jobs each took 2–5 minutes per task due to HDFS read/write overhead between stages.

---

## ML Results Summary (Phase B)

| Model | AUC-ROC | Accuracy | F1 |
|-------|---------|----------|----|
| Logistic Regression | ~0.72 | ~0.74 | ~0.71 |
| Random Forest | ~0.78 | ~0.76 | ~0.74 |
| **GBT** | **~0.79** | **~0.77** | **~0.75** |

> Exact numbers depend on the dataset used (local synthetic vs. full HDFS).

**Best model**: GBT (Gradient Boosted Trees) — highest AUC-ROC.

**Most important feature**: `crime_index` (Primary Type). Crime type alone explains most of the variance in arrest probability — NARCOTICS and WEAPONS VIOLATION offences result in arrest ~40% of the time, while THEFT and CRIMINAL DAMAGE sit below 15%.

**Why Logistic Regression underperforms**: The relationship between features and arrest probability is non-linear. Certain (crime_type, district, hour) combinations produce arrest rates that a linear model cannot capture. Tree ensembles split on interaction effects natively.

---

## Member Contributions

| Member | M2 Tasks | Deliverables |
|--------|----------|-------------|
| Ahmad Al-Younis (ayounis) | Tasks 1–2 | DataFrame crime distribution, Spark SQL hotspots |
| Nawaf (nawaf) | Tasks 3–4 | Year trend + matplotlib chart, arrest rate per crime type |
| Mohammad Al-Ghamdi (mohalghamdi) | Tasks 5–7 | Feature engineering, 3-model evaluation, feature importances |
| Thabet Al-Salmalki (tsalmalki) | Tasks 9–11 | Local execution, cluster client mode, spark-submit evidence |

---

## Deployment Evidence

### Task 9 — Local Execution
- Run `jupyter notebook M2_Spark_ML_GroupSES.ipynb` on your laptop
- SparkSession uses `local[*]` and generates 10 000 synthetic rows
- Screenshot: **[add screenshot showing `Master: local[*]`]**

### Task 10 — Cluster Client Mode
- SSH to cluster, launch Jupyter with `--master yarn`
- Full HDFS dataset loaded (7 M+ rows)
- Screenshot: **[add screenshot showing `Master: yarn` and row count]**

### Task 11 — spark-submit (Cluster Deploy Mode)
```bash
spark-submit \
    --master yarn \
    --deploy-mode cluster \
    --driver-memory 512m \
    --num-executors 1 \
    --executor-memory 1g \
    --executor-cores 1 \
    --conf spark.driver.maxResultSize=128m \
    --conf spark.yarn.appMasterEnv.PYSPARK_PYTHON=python3.12 \
    --conf spark.executorEnv.PYSPARK_PYTHON=python3.12 \
    m2_spark_ml.py
```
Full terminal output and `yarn logs` saved to `output/spark_submit/run.log`.

---

## Repository Structure

```
se446-project-group-SES/
├── README.md                        ← this file
├── M2_Spark_ML_GroupSES.ipynb       ← M2 main notebook (Tasks 1–7)
├── m2_spark_ml.py                   ← standalone script for spark-submit (Tasks 5–7)
├── src/
│   ├── task2mapper.py               ← M1: crime type mapper
│   ├── task3mapper.py               ← M1: location hotspot mapper
│   ├── task4mapper.py               ← M1: year trend mapper
│   ├── task5mapper.py               ← M1: arrest rate mapper
│   └── reducer.py                   ← M1: shared reducer
├── scripts/
│   ├── task2.sh  task3.sh  task4.sh  task5.sh   ← M1 Hadoop streaming commands
├── output/
│   ├── task2results.txt             ← M1 Task 2 output
│   ├── task3result.txt              ← M1 Task 3 output
│   ├── task4results.txt             ← M1 Task 4 output
│   ├── task5results.txt             ← M1 Task 5 output (Arrested/Not Arrested)
│   └── spark_submit/
│       └── run.log                  ← M2 Task 11 spark-submit log
```
