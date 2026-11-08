import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

QOS = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)   # 3단계에서 BEST_EFFORT로 바꿈


class Pong(Node):
    def __init__(self):
        super().__init__('pong')
        self.pub = self.create_publisher(String, '/pong', QOS)
        self.create_subscription(String, '/ping', self.pub.publish, QOS)


rclpy.init()
try:
    rclpy.spin(Pong())
except KeyboardInterrupt:
    pass
