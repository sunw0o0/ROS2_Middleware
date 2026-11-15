"""Qt Creator 로 만든 mainwindow.ui 를 불러와서 버튼으로 손끝을 움직이는 IK 조종기.

앞/뒤/오른쪽/왼쪽/위/아래 버튼 = 목표점을 한 칸씩 옮기고, 그때마다 IK 를 풀어
/joint_states 로 보낸다. 그리퍼 방향은 처음 자세 그대로 유지한다.
버튼을 누르고 있으면 계속 움직인다.
"""
import math
import os
import sys

import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from PyQt5 import QtCore, QtGui, QtWidgets, uic

from .ik_node import DEG, MM, IkNode, excepthook
from .kinematics import Chain, parse_joints

STEP_MM = 10.0   # 버튼 한 번에 움직이는 거리


class ManiWindow(QtWidgets.QMainWindow):
    def __init__(self, node, ui_path):
        super().__init__()
        uic.loadUi(ui_path, self)
        self.setWindowTitle('IK 조종기')
        self.node = node
        self.chain = None
        self.q = None
        self.other = []
        self.p_target = None
        self.R_target = None

        # .ui 의 위젯 이름 -> 역할
        self.joint_labels = [self.label_27, self.label_40, self.label_34,
                             self.label_42, self.label_30, self.label_32]
        self.T_labels = [
            [self.label_22, self.label_23, self.label_24, self.label_25],
            [self.label_14, self.label_15, self.label_16, self.label_17],
            [self.label_6, self.label_7, self.label_10, self.label_4],
            [self.label_18, self.label_19, self.label_20, self.label_21],
        ]
        mono = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        for lab in self.joint_labels + [l for row in self.T_labels for l in row]:
            lab.setFont(mono)
            lab.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            lab.setMinimumWidth(90)
            lab.setText('-')

        # (버튼, 축 0=x 1=y 2=z, 부호)  "+ 방향" 열이 +, "- 방향" 열이 -
        self.buttons = [
            (self.pushButton, 0, +1),    # 앞
            (self.pushButton_2, 0, -1),  # 뒤
            (self.pushButton_4, 1, +1),  # 오른쪽 (+y)
            (self.pushButton_3, 1, -1),  # 왼쪽 (-y)
            (self.pushButton_5, 2, +1),  # 위
            (self.pushButton_6, 2, -1),  # 아래
        ]
        for b, ax, sg in self.buttons:
            b.setAutoRepeat(True)          # 누르고 있으면 계속
            b.setAutoRepeatDelay(300)
            b.setAutoRepeatInterval(80)
            b.setEnabled(False)
            b.clicked.connect(lambda _=False, a=ax, s=sg: self.jog(a, s))

        self.statusbar.showMessage('robot_description 을 기다리는 중... (robot_state_publisher 가 켜져 있어야 해요)')

        self.ros_timer = QtCore.QTimer(self)
        self.ros_timer.timeout.connect(self._ros_tick)
        self.ros_timer.start(10)
        self.pub_timer = QtCore.QTimer(self)
        self.pub_timer.timeout.connect(self._publish)

    # ------------------------------------------------------------ ROS
    def _ros_tick(self):
        rclpy.spin_once(self.node, timeout_sec=0)
        if self.chain is not None or self.node.urdf is None:
            return
        try:
            self.chain = Chain(self.node.urdf, self.node.base_link, self.node.tip_link)
        except ValueError as e:
            self.statusbar.showMessage(str(e))
            self.node.urdf = None
            return
        arm = set(self.chain.names)
        self.other = [j.name for j in parse_joints(self.node.urdf)
                      if j.movable and not j.mimic and j.name not in arm]
        self.q = self.chain.clamp(np.zeros(self.chain.n))
        T, _ = self.chain.fk(self.q)
        self.p_target = T[:3, 3].copy()
        self.R_target = T[:3, :3].copy()   # 그리퍼 방향은 이 상태로 고정
        for b, _, _ in self.buttons:
            b.setEnabled(True)
        self._refresh()
        self._status('준비 완료. 버튼을 누르면 손끝이 %d mm 씩 움직여요.' % STEP_MM, True)
        self.pub_timer.start(33)

    def _publish(self):
        names = self.chain.names + self.other
        values = list(self.q) + [0.0] * len(self.other)
        self.node.publish_joints(names, values)

    # ------------------------------------------------------------ 동작
    def jog(self, axis, sign):
        p = self.p_target.copy()
        p[axis] += sign * STEP_MM / MM
        tol = dict(tol_p=5e-4, tol_r=math.radians(1.0))   # 조그용 허용 오차: 0.5 mm, 1도
        note = ''
        # 1차: 그리퍼 방향을 유지한 채, 지금 자세에서 이어서 풀기 (자세가 갑자기 바뀌지 않게)
        q, ok, ep, er, _ = self.chain.ik(p, self.q, R_target=self.R_target, restarts=0, **tol)
        if not ok:
            # 2차: 방향 유지는 포기하고 위치만 맞추기
            q, ok, ep, er, _ = self.chain.ik(p, self.q, R_target=None, restarts=0, **tol)
            if ok:
                T, _ = self.chain.fk(q)
                self.R_target = T[:3, :3].copy()
                note = '   (그리퍼 방향을 유지할 수 없어 방향이 조금 바뀌었어요)'
        if not ok:
            self._status('더 이상 갈 수 없어요 (팔이 닿지 않거나 관절 제한). 다른 방향으로 움직여 보세요.', False)
            self.node.publish_target(self.chain.base_link, p, False)
            return
        self.q = np.asarray(q, dtype=float)
        self.p_target = p
        self.node.publish_target(self.chain.base_link, p, True)
        self._refresh()
        self._status('목표 (%.1f, %.1f, %.1f) mm   위치 오차 %.3f mm' % (*(p * MM), ep * MM) + note, True)

    def _status(self, msg, ok):
        self.statusbar.setStyleSheet('' if ok else 'color: #c8433a;')
        self.statusbar.showMessage(msg)

    def _refresh(self):
        for lab, v in zip(self.joint_labels, self.q):
            lab.setText('%8.1f°' % (v * DEG))
        for lab in self.joint_labels[len(self.q):]:
            lab.setText('-')
        T, _ = self.chain.fk(self.q)
        for r in range(4):
            for c in range(4):
                if r == 3:
                    txt = '1' if c == 3 else '0'
                elif c == 3:
                    txt = '%.1f' % (T[r, 3] * MM)
                else:
                    v = T[r, c]
                    txt = '%.3f' % (0.0 if abs(v) < 5e-4 else v)
                self.T_labels[r][c].setText(txt)


def main(args=None):
    sys.excepthook = excepthook
    rclpy.init(args=args)
    node = IkNode()
    ui_path = os.path.join(get_package_share_directory('ik_gui'), 'ui', 'mainwindow.ui')
    app = QtWidgets.QApplication(sys.argv)
    w = ManiWindow(node, ui_path)
    w.show()
    try:
        app.exec_()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
