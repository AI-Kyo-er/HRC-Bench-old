"""机械臂与公开模型动作规范的可审计数值转换。"""
from __future__ import annotations

import numpy as np


def hand_rotation(quaternion):
    """Genesis wxyz 四元数到旋转矩阵。"""
    q = np.asarray(quaternion, dtype=float)
    if q.shape != (4,) or not np.isfinite(q).all() or np.linalg.norm(q) < 1e-8:
        raise ValueError("需要有限且非零的 wxyz 四元数")
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def select_grasp_candidate(point, positions, *, excluded=(), radius=0.055):
    candidates = [(float(np.linalg.norm(np.asarray(position) - point)), name)
                  for name, position in positions.items() if name not in excluded]
    if not candidates:
        return None
    distance, name = min(candidates)
    return name if distance <= radius else None


def droid_action_to_joint_target(action, qpos):
    """按 DROID 的每步 0.2 rad 标度转换，不把归一化速度误当绝对位置。

    官方 RobotIKSolver 先统一限制速度向量，再乘 max_joint_delta=0.2。
    官方客户端先逐维裁剪并将夹爪二值化；0 是打开，1 是闭合。
    该转换必须以 15 Hz 调用。Genesis 指关节最大值为每侧 0.04 m。
    """
    values = np.asarray(action, dtype=float)
    current = np.asarray(qpos, dtype=float)
    if values.shape != (8,) or current.shape != (9,) or not np.isfinite(values).all() or not np.isfinite(current).all():
        raise ValueError("DROID 动作必须为 8 个有限值，Franka 状态必须为 9 个有限值")
    velocity = np.clip(values[:7], -1.0, 1.0)
    target = current.copy()
    target[:7] += 0.2 * velocity
    target[-2:] = 0.0 if values[-1] > 0.5 else 0.04
    return tuple(float(value) for value in target)


def position_action_to_joint_target(action):
    """仿真适配模型的7维绝对关节位置与连续夹爪闭合比例。"""
    values = np.asarray(action, dtype=float)
    if values.shape != (8,) or not np.isfinite(values).all():
        raise ValueError("位置动作必须为8个有限值")
    fingers = 0.04 * (1 - np.clip(values[-1], 0, 1))
    return tuple(float(value) for value in np.r_[values[:7], fingers, fingers])
