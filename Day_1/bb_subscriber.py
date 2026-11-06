import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import String


class BBSubscriber(Node):
    def __init__(self):
        super().__init__('bb_subscriber')

        config_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        stream_qos = QoSProfile(                          # 추가
            depth=10,                                     # 추가
            reliability=ReliabilityPolicy.BEST_EFFORT,    # 추가
            durability=DurabilityPolicy.VOLATILE,         # 추가
        )                                                 # 추가

        self.create_subscription(String, '/bb_d150/config', self.config_cb, config_qos)
        self.create_subscription(String, '/bb_d150/stream', self.stream_cb, stream_qos)  # 추가

    def config_cb(self, msg):
        self.get_logger().info(f'[config] {msg.data}')

    def stream_cb(self, msg):                             # 추가
        self.get_logger().info(f'[stream] {msg.data}')    # 추가


rclpy.init()
rclpy.spin(BBSubscriber())
