mapred streaming \
-files mapper_task2.py,reducer_sum.py \
-mapper "python3 mapper_task2.py" \
-reducer "python3 reducer_sum.py" \
-input /data/chicago_crimes.csv \
-output /user/YOUR_CLUSTER_USERNAME/project/m1/task2