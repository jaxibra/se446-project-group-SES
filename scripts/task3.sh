mapred streaming \
  -files src/ task3mapper.py,src/reducer.py \
  -mapper "python3 task3mapper.py" \
  -reducer "python3 reducer.py" \
  -input /data/chicago_crimes.csv \
  -output /user/YOUR_CLUSTER_USERNAME/project/m1/task3
