import sys, time
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor, MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

MODE = sys.argv[1] if len(sys.argv) > 1 else 'single'
START = time.monotonic()


def now():
    return f"{time.monotonic() - START:5.2f}s"


class Demo(Node):
    def __init__(self):
        super().__init__('demo')
        group = ReentrantCallbackGroup() if MODE == 'multi' else None   # multi일 때만 "동시 실행 가능" 그룹
        self.create_timer(1.0, self.work_a, callback_group=group)
        self.create_timer(1.0, self.work_b, callback_group=group)

    def work_a(self):
        print(f"{now()}  A 시작")
        time.sleep(0.5)                  # 0.5초 걸리는 일 (예: find_box)
        print(f"{now()}  A 끝")

    def work_b(self):
        print(f"{now()}  B 시작")
        time.sleep(0.5)                  # 0.5초 걸리는 일 (예: find_grasp)
        print(f"{now()}  B 끝")


rclpy.init()
executor = MultiThreadedExecutor() if MODE == 'multi' else SingleThreadedExecutor()
executor.add_node(Demo())
try:
    executor.spin_once(timeout_sec=3.0)
    end = time.monotonic() + 3.0
    while time.monotonic() < end:
        executor.spin_once(timeout_sec=0.1)
except KeyboardInterrupt:
    pass
