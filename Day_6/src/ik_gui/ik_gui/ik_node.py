"""ROS 쪽 기능만 모아 둔 노드.

- /robot_description 을 받아서 URDF 를 넘겨주고
- 계산한 관절각을 /joint_states 로 보내고 (RViz 의 팔이 움직임)
- 목표점을 /ik_target 마커(공)로 보낸다.
"""
import math
import traceback

from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from visualization_msgs.msg import Marker

MM = 1000.0              # m -> mm
DEG = 180.0 / math.pi    # rad -> deg


def excepthook(t, v, tb):
    """PyQt5 는 버튼 콜백 안의 예외로 프로그램을 끄므로, 에러만 출력하고 계속 실행."""
    traceback.print_exception(t, v, tb)


class IkNode(Node):
    def __init__(self):
        super().__init__('mani_ui')
        self.declare_parameter('base_link', 'mani_base_link')
        self.declare_parameter('tip_link', 'gripper_base_link')
        self.base_link = self.get_parameter('base_link').value
        self.tip_link = self.get_parameter('tip_link').value
        self.urdf = None
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(String, 'robot_description', self._on_desc, qos)
        self.js_pub = self.create_publisher(JointState, 'joint_states', 10)
        self.marker_pub = self.create_publisher(Marker, 'ik_target', 10)

    def _on_desc(self, msg):
        if self.urdf is None:
            self.urdf = msg.data
            self.get_logger().info('robot_description 받음')

    def publish_joints(self, names, values):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(names)
        msg.position = [float(v) for v in values]
        self.js_pub.publish(msg)

    def publish_target(self, frame, p, ok):
        m = Marker()
        m.header.frame_id = frame
        m.header.stamp = self.get_clock().now().to_msg()
        m.ns, m.id, m.type, m.action = 'ik_target', 0, Marker.SPHERE, Marker.ADD
        m.pose.position.x, m.pose.position.y, m.pose.position.z = (float(v) for v in p)
        m.pose.orientation.w = 1.0
        m.scale.x = m.scale.y = m.scale.z = 0.03
        m.color.a = 0.85
        m.color.r, m.color.g, m.color.b = (0.2, 0.85, 0.3) if ok else (0.95, 0.25, 0.2)
        self.marker_pub.publish(m)
