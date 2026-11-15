"""URDF 체인으로 FK / 수치 IK (감쇠 최소제곱, damped least squares) 를 계산하는 모듈.

ROS 없이 numpy 만으로 동작한다. 길이 단위는 URDF 와 같은 m, 각도는 rad.
"""
import math
import xml.etree.ElementTree as ET

import numpy as np


# ---------------------------------------------------------------- 회전 유틸
def rpy_to_R(r, p, y):
    """URDF rpy (고정축 X->Y->Z, 즉 R = Rz(y) Ry(p) Rx(r))."""
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ])


def R_to_rpy(R):
    """회전행렬 -> (roll, pitch, yaw). 슬라이드의 Z-Y-X 공식과 같다."""
    pitch = math.atan2(-R[2, 0], math.hypot(R[0, 0], R[1, 0]))
    if abs(math.cos(pitch)) < 1e-9:
        return math.atan2(R[0, 1], R[1, 1]), pitch, 0.0
    roll = math.atan2(R[2, 1], R[2, 2])
    yaw = math.atan2(R[1, 0], R[0, 0])
    return roll, pitch, yaw


def axis_angle_R(axis, th):
    """로드리게스 공식: axis(단위벡터) 둘레로 th 만큼 회전."""
    k = np.asarray(axis, dtype=float)
    n = np.linalg.norm(k)
    if n < 1e-12:
        return np.eye(3)
    k = k / n
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


def rot_error(R_target, R_now):
    """두 회전의 차이를 회전벡터(축 x 각도)로. 0 이면 방향이 같다."""
    Re = R_target @ R_now.T
    c = max(-1.0, min(1.0, (np.trace(Re) - 1) / 2))
    ang = math.acos(c)
    v = np.array([Re[2, 1] - Re[1, 2], Re[0, 2] - Re[2, 0], Re[1, 0] - Re[0, 1]])
    if ang < 1e-9:
        return 0.5 * v
    if math.pi - ang < 1e-4:  # 180도 근처: Re + I = 2 a a^T 에서 축 a 를 꺼낸다
        M = Re + np.eye(3)
        col = M[:, int(np.argmax(np.linalg.norm(M, axis=0)))]
        return col / np.linalg.norm(col) * ang
    return ang / (2 * math.sin(ang)) * v


def homog(R, p):
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = p
    return T


# ---------------------------------------------------------------- URDF 파싱
class Joint:
    def __init__(self, el):
        self.name = el.get('name')
        self.type = el.get('type')
        self.parent = el.find('parent').get('link')
        self.child = el.find('child').get('link')
        o = el.find('origin')
        xyz = [float(v) for v in (o.get('xyz', '0 0 0') if o is not None else '0 0 0').split()]
        rpy = [float(v) for v in (o.get('rpy', '0 0 0') if o is not None else '0 0 0').split()]
        self.T_origin = homog(rpy_to_R(*rpy), xyz)
        a = el.find('axis')
        ax = np.array([float(v) for v in (a.get('xyz') if a is not None else '1 0 0').split()])
        self.axis = ax / np.linalg.norm(ax) if np.linalg.norm(ax) > 0 else np.array([1.0, 0, 0])
        lim = el.find('limit')
        if self.type == 'continuous' or lim is None or lim.get('lower') is None:
            self.lower, self.upper = -math.pi, math.pi
        else:
            self.lower, self.upper = float(lim.get('lower')), float(lim.get('upper'))
            if self.lower >= self.upper:   # limit 이 0,0 처럼 비어 있으면 회전 범위 전체로
                self.lower, self.upper = -math.pi, math.pi
        self.mimic = el.find('mimic') is not None

    @property
    def movable(self):
        return self.type in ('revolute', 'continuous', 'prismatic')

    def motion(self, q):
        """관절값 q 에 따른 움직임 (origin 뒤에 곱한다)."""
        if self.type == 'prismatic':
            return homog(np.eye(3), self.axis * q)
        if self.type in ('revolute', 'continuous'):
            return homog(axis_angle_R(self.axis, q), np.zeros(3))
        return np.eye(4)


def parse_joints(urdf_xml):
    root = ET.fromstring(urdf_xml)
    return [Joint(j) for j in root.iter('joint')]


# ---------------------------------------------------------------- 체인
class Chain:
    def __init__(self, urdf_xml, base_link, tip_link):
        self.all_joints = parse_joints(urdf_xml)
        by_child = {j.child: j for j in self.all_joints}
        path, link = [], tip_link
        while link != base_link:
            if link not in by_child:
                raise ValueError(f'"{tip_link}" 에서 "{base_link}" 까지 이어지는 조인트를 찾지 못했어요 ("{link}" 에서 끊김).')
            j = by_child[link]
            path.append(j)
            link = j.parent
        self.joints = list(reversed(path))                     # base -> tip 순서 (fixed 포함)
        self.movable = [j for j in self.joints if j.movable]   # IK 변수
        self.names = [j.name for j in self.movable]
        self.lower = np.array([j.lower for j in self.movable])
        self.upper = np.array([j.upper for j in self.movable])
        self.base_link, self.tip_link = base_link, tip_link

    @property
    def n(self):
        return len(self.movable)

    def clamp(self, q):
        return np.minimum(np.maximum(q, self.lower), self.upper)

    def fk(self, q):
        """q 에 대한 tip 의 4x4 변환과, 각 움직이는 관절의 (원점, 축 방향, 종류)."""
        T = np.eye(4)
        k = 0
        info = []
        for j in self.joints:
            T = T @ j.T_origin
            if j.movable:
                info.append((T[:3, 3].copy(), T[:3, :3] @ j.axis, j.type))
                T = T @ j.motion(q[k])
                k += 1
        return T, info

    def jacobian(self, q):
        T, info = self.fk(q)
        p_tip = T[:3, 3]
        J = np.zeros((6, self.n))
        for i, (o, a, typ) in enumerate(info):
            if typ == 'prismatic':
                J[:3, i] = a
            else:
                J[:3, i] = np.cross(a, p_tip - o)
                J[3:, i] = a
        return T, J

    def ik(self, p_target, q0, R_target=None, max_iter=300, tol_p=1e-4, tol_r=1e-3,
           restarts=8, rot_weight=0.2, seed=0):
        """감쇠 최소제곱 반복 IK.

        반환: (q, 수렴 여부, 위치 오차[m], 회전 오차[rad], 반복 횟수)
        q0 에서 먼저 시작하고, 수렴하지 않으면 무작위 시작값으로 다시 시도한다.
        """
        rng = np.random.default_rng(seed)
        starts = [self.clamp(np.asarray(q0, dtype=float))]
        for _ in range(restarts):
            starts.append(rng.uniform(np.maximum(self.lower, -math.pi), np.minimum(self.upper, math.pi)))
        best = None
        total_it = 0
        for q in starts:
            q = q.copy()
            for it in range(max_iter):
                total_it += 1
                T, J = self.jacobian(q)
                e_p = p_target - T[:3, 3]
                if R_target is None:
                    e = e_p
                    Jw = J[:3]
                    e_r = 0.0
                else:
                    e_rv = rot_error(R_target, T[:3, :3])
                    e = np.concatenate([e_p, rot_weight * e_rv])
                    Jw = np.vstack([J[:3], rot_weight * J[3:]])
                    e_r = float(np.linalg.norm(e_rv))
                err_p = float(np.linalg.norm(e_p))
                if best is None or err_p + 0.05 * e_r < best[2] + 0.05 * best[3]:
                    best = (q.copy(), False, err_p, e_r, total_it)
                if err_p < tol_p and e_r < tol_r:
                    return q, True, err_p, e_r, total_it
                lam = 0.02 + 2.0 * err_p           # 멀리 있을 땐 조심스럽게, 가까우면 빠르게
                dq = Jw.T @ np.linalg.solve(Jw @ Jw.T + lam * lam * np.eye(Jw.shape[0]), e)
                m = np.max(np.abs(dq))
                if m > 0.2:
                    dq *= 0.2 / m
                q = self.clamp(q + dq)
        return best


def quat_to_R(x, y, z, w):
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def R_to_quat(R):
    """회전행렬 -> (x, y, z, w)."""
    tr = np.trace(R)
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return ((R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, 0.25 * s)
    i = int(np.argmax(np.diag(R)))
    if i == 0:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        return (0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s, (R[2, 1] - R[1, 2]) / s)
    if i == 1:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        return ((R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s, (R[0, 2] - R[2, 0]) / s)
    s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
    return ((R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s, (R[1, 0] - R[0, 1]) / s)
