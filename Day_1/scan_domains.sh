#!/bin/bash
# 1단계 정찰: 10번 방부터 95번 방까지 bb_ 토픽 찾기

for d in $(seq 10 95)
do
  echo "===== Domain $d ====="
  ROS_DOMAIN_ID=$d ros2 topic list --no-daemon --spin-time 4 -t | grep bb_
done
