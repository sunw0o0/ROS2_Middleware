import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import String

N = 200                                                              # 몇 번 보낼까
QOS = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)   # 3단계에서 BEST_EFFORT로 바꿈


class Ping(Node):
    def __init__(self):
        super().__init__('ping')
        self.pub = self.create_publisher(String, '/ping', QOS)
        self.create_subscription(String, '/pong', self.on_pong, QOS)
        self.create_timer(0.1, self.send)                            # 초당 10번
        self.seq, self.rtts = 0, {}

    def send(self):
        if self.seq >= N:
            return
        self.pub.publish(String(data=f"{self.seq},{time.monotonic()}"))
        self.seq += 1
        if self.seq == N:
            self.create_timer(2.0, self.report)                     # 늦게 오는 답을 2초 기다림

    def on_pong(self, msg):
        seq, t0 = msg.data.split(",")
        self.rtts[int(seq)] = (time.monotonic() - float(t0)) * 1000  # ms

    def report(self):
        v = sorted(self.rtts.values())
        if v:
            p95 = v[int(0.95 * (len(v) - 1))]
            print(f"loss {100*(N-len(v))/N:.1f}% mean {sum(v)/len(v):.1f}ms p95 {p95:.1f}ms")
        else:
            print("no reply")
        rclpy.shutdown()


rclpy.init()
try:
    rclpy.spin(Ping())
except (KeyboardInterrupt, ExternalShutdownException):
    pass
