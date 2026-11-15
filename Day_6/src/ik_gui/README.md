# ik_gui

Qt Creator로 만든 UI(`ui/mainwindow.ui`)의 버튼으로 손끝 목표를 옮기면,
URDF로 수치 IK(감쇠 최소제곱 야코비안 반복)를 풀어 `/joint_states`로 보내고
RViz에서 팔이 움직이는 걸 보는 패키지예요.

## 설치
```bash
sudo apt install python3-pyqt5 python3-numpy
cd ~/ros2_ws
colcon build --packages-select ik_gui
source install/setup.bash
```

## 실행
```bash
ros2 launch ik_gui mani_ui.launch.py
```
robot_state_publisher, RViz, 조종기 창이 같이 켜져요. joint_state_publisher_gui는 켜지 마세요.
목표점(공)을 보려면 RViz Add → Marker → Topic `/ik_target`.

## 파일
- `ik_gui/kinematics.py`: URDF 읽기, FK, 야코비안, 수치 IK (ROS 없이 numpy만)
- `ik_gui/ik_node.py`: ROS 통신 (robot_description 받기, joint_states / 마커 보내기)
- `ik_gui/mani_ui_node.py`: mainwindow.ui 불러와서 버튼과 IK 연결
- `ui/mainwindow.ui`: Qt Creator로 수정 가능. 위젯 이름을 바꾸면 mani_ui_node.py도 같이 바꿔야 해요.
