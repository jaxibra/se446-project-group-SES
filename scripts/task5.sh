#!/bin/bash

source /etc/profile.d/hadoop.sh

hdfs dfs -mkdir -p /user/tsalmalki/project/m1
hdfs dfs -rm -r -f /user/tsalmalki/project/m1/task5

mapred streaming \
  -files ../src/task5mapper.py,../src/reducer.py \
  -mapper "python3 task5mapper.py" \
  -reducer "python3 reducer.py" \
  -input /data/chicago_crimes.csv \
  -output /user/tsalmalki/project/m1/task5
