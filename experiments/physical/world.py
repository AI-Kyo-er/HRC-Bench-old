"""CPU Bullet 桌面；动作只通过电机和动力学，成功由物体状态计算。"""
import math
from pathlib import Path

import numpy as np
import pybullet as p
import pybullet_data


ITEMS = ('red', 'blue', 'green')
TARGETS = ('left', 'right')
DT = 1 / 240


class World:
    def __init__(self, seed=0, occupied=False, trace_path=None, render_dir=None):
        self.client = p.connect(p.DIRECT)
        self.tick = 0
        self.phase = 'initialization'
        import gzip
        self.trace = (gzip.open(trace_path, 'wt') if str(trace_path).endswith('.gz')
                      else open(trace_path, 'w')) if trace_path else None
        self.render_dir = Path(render_dir) if render_dir else None
        if self.render_dir:
            self.render_dir.mkdir(parents=True, exist_ok=True)
        self.frames = 0
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.client)
        p.setGravity(0, 0, -9.81, physicsClientId=self.client)
        p.setTimeStep(DT, physicsClientId=self.client)
        p.setPhysicsEngineParameter(numSolverIterations=100, deterministicOverlappingPairs=1,
                                    physicsClientId=self.client)
        self.table = p.loadURDF('plane.urdf', physicsClientId=self.client)
        self.robot = p.loadURDF('franka_panda/panda.urdf', useFixedBase=True,
                                physicsClientId=self.client)
        self.home = [0, -.4, 0, -2.5, 0, 2.1, .8]
        # 唯一的关节reset仅用于初始化，运行期严格使用POSITION_CONTROL。
        for j, q in enumerate(self.home):
            p.resetJointState(self.robot, j, q, physicsClientId=self.client)
        for j in (9, 10):
            p.resetJointState(self.robot, j, .04, physicsClientId=self.client)
        self.orientation = p.getQuaternionFromEuler([math.pi, 0, 0])
        self.objects = {}
        rng = np.random.default_rng(seed)
        for item, y, color in zip(ITEMS, (-.16, 0, .16),
                                   ((.9, .15, .1, 1), (.1, .25, .9, 1), (.1, .8, .2, 1))):
            xy = np.array([.42, y]) + rng.uniform(-.006, .006, 2)
            self.objects[item] = self.box([.022, .022, .022], [*xy, .023], .06, color)
            p.changeDynamics(self.objects[item], -1, lateralFriction=1,
                             spinningFriction=.01, rollingFriction=.001,
                             physicsClientId=self.client)
        for j in (9, 10):
            p.changeDynamics(self.robot, j, lateralFriction=2, spinningFriction=.01,
                             physicsClientId=self.client)
        # 两个浅托盘；目标位置按物品索引分开，不依赖符号完成标志。
        self.trays = {}
        for name, y in (('left', -.25), ('right', .25)):
            self.trays[name] = self.box([.10, .085, .005], [.65, y, .005], 0,
                                        (.7, .65, .5, 1))
            for dy in (-.085, .085):
                self.box([.1, .005, .009], [.65, y + dy, .019], 0, (.6, .5, .35, 1))
        # 伙伴资源代理：竖直占位块沿y轴电机滑动，可真实占用/释放公共路径。
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[.035, .055, .16],
                                     physicsClientId=self.client)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[.035, .055, .16],
                                  rgbaColor=[.7, .2, .7, .75], physicsClientId=self.client)
        self.partner = p.createMultiBody(baseMass=0, basePosition=[.54, 0, .24],
            linkMasses=[1], linkCollisionShapeIndices=[col], linkVisualShapeIndices=[vis],
            linkPositions=[[0, 0, 0]], linkOrientations=[[0, 0, 0, 1]],
            linkInertialFramePositions=[[0, 0, 0]], linkInertialFrameOrientations=[[0, 0, 0, 1]],
            linkParentIndices=[0], linkJointTypes=[p.JOINT_PRISMATIC], linkJointAxis=[[0, 1, 0]],
            physicsClientId=self.client)
        p.resetJointState(self.partner, 0, 0 if occupied else .6,
                          physicsClientId=self.client)
        self.partner_target = 0 if occupied else .6
        self.grip = .04
        self.command_joints(self.home)
        self.simulate(180)
        self.capture()

    def box(self, size, position, mass, color):
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=size, physicsClientId=self.client)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=size, rgbaColor=color,
                                  physicsClientId=self.client)
        return p.createMultiBody(mass, col, vis, position, physicsClientId=self.client)

    def command_joints(self, q):
        p.setJointMotorControlArray(self.robot, list(range(7)), p.POSITION_CONTROL,
            targetPositions=q[:7], forces=[120] * 7, positionGains=[.2] * 7,
            physicsClientId=self.client)
        p.setJointMotorControlArray(self.robot, [9, 10], p.POSITION_CONTROL,
            targetPositions=[self.grip] * 2, forces=[35] * 2,
            physicsClientId=self.client)

    def state(self):
        contacts = p.getContactPoints(physicsClientId=self.client)
        return {'tick': self.tick, 'time': self.tick * DT, 'phase': self.phase,
            'joint_positions': [p.getJointState(self.robot, j, physicsClientId=self.client)[0]
                                for j in range(12)],
            'ee': list(p.getLinkState(self.robot, 11, physicsClientId=self.client)[4]),
            'objects': {name: {'position': list(p.getBasePositionAndOrientation(body,
                                physicsClientId=self.client)[0]),
                               'orientation': list(p.getBasePositionAndOrientation(body,
                                physicsClientId=self.client)[1]),
                               'velocity': list(p.getBaseVelocity(body, physicsClientId=self.client)[0])}
                        for name, body in self.objects.items()},
            'partner_position': list(p.getLinkState(self.partner, 0,
                                                    physicsClientId=self.client)[4]),
            'partner_joint': p.getJointState(self.partner, 0, physicsClientId=self.client)[0],
            'contacts': [{'body_a': c[1], 'body_b': c[2], 'link_a': c[3], 'link_b': c[4],
                          'position_a': c[5], 'normal_force': c[9]} for c in contacts]}

    def simulate(self, ticks):
        import json
        for _ in range(ticks):
            p.setJointMotorControl2(self.partner, 0, p.POSITION_CONTROL,
                targetPosition=self.partner_target, force=100, maxVelocity=.6,
                physicsClientId=self.client)
            p.stepSimulation(physicsClientId=self.client)
            self.tick += 1
            if self.trace:
                self.trace.write(json.dumps(self.state()) + '\n')
            if self.render_dir and self.tick % 48 == 0:
                self.capture()

    def capture(self):
        if not self.render_dir:
            return
        from PIL import Image
        view = p.computeViewMatrix([1.1, -1.2, 1.05], [.45, 0, .1], [0, 0, 1])
        proj = p.computeProjectionMatrixFOV(50, 4/3, .01, 3)
        data = p.getCameraImage(640, 480, view, proj, renderer=p.ER_TINY_RENDERER,
                                physicsClientId=self.client)[2]
        Image.fromarray(np.asarray(data, dtype=np.uint8).reshape(480, 640, 4)[:, :, :3]).save(
            self.render_dir / f'{self.frames:05d}.png')
        self.frames += 1

    def move(self, target, phase, ticks=160):
        self.phase = phase
        start = np.array(p.getLinkState(self.robot, 11, physicsClientId=self.client)[4])
        # 小步笛卡尔插值 + IK只给电机目标，不更改关节/物体实际位置。
        for t in range(1, ticks + 1):
            xyz = start + (np.asarray(target) - start) * t / ticks
            q = p.calculateInverseKinematics(self.robot, 11, xyz, self.orientation,
                maxNumIterations=80, residualThreshold=1e-5, physicsClientId=self.client)
            self.command_joints(q)
            self.simulate(1)
        self.simulate(80)
        error = np.linalg.norm(np.array(p.getLinkState(self.robot, 11,
                                                      physicsClientId=self.client)[4]) - target)
        return float(error)

    def set_grip(self, gap, phase):
        self.grip = gap
        self.phase = phase
        q = [p.getJointState(self.robot, j, physicsClientId=self.client)[0] for j in range(7)]
        self.command_joints(q)
        self.simulate(180)

    def move_partner(self, occupied):
        self.phase = 'partner_occupy' if occupied else 'partner_release'
        before = self.state()['partner_position']
        self.partner_target = 0 if occupied else .6
        self.simulate(420)
        reached = abs(self.state()['partner_joint'] - self.partner_target) < .02
        return {'before': before, 'after': self.state()['partner_position'], 'reached': reached,
                'direct_blocked_after': self.direct_blocked(),
                'central_waypoint_clearance': self.waypoint_clearance()}

    def waypoint_clearance(self):
        lo, hi = p.getAABB(self.partner, 0, physicsClientId=self.client)
        point = np.array([.54, 0, .26])
        distance = np.linalg.norm(np.maximum(np.maximum(np.array(lo) - point,
                                                        point - np.array(hi)), 0))
        return {'partner_aabb': [list(lo), list(hi)], 'waypoint': point.tolist(),
                'probe_radius': .055, 'aabb_sphere_clearance': float(distance - .055)}

    def direct_blocked(self):
        # 共享中央waypoint与伙伴实际AABB膨胀后的交集，通用安全前提。
        lo, hi = p.getAABB(self.partner, 0, physicsClientId=self.client)
        return all(a - .055 <= x <= b + .055 for x, a, b in zip([.54, 0, .26], lo, hi))

    def goal(self, item, destination):
        return [.59 + .06 * ITEMS.index(item), -.25 if destination == 'left' else .25, .036]

    def at_goal(self, item, destination):
        body = self.objects[item]
        xyz = np.array(p.getBasePositionAndOrientation(body, physicsClientId=self.client)[0])
        velocity = np.linalg.norm(p.getBaseVelocity(body, physicsClientId=self.client)[0])
        goal = np.array(self.goal(item, destination))
        return bool(np.linalg.norm(xyz[:2] - goal[:2]) < .035 and .025 < xyz[2] < .055
                    and velocity < .04)

    def pick_place(self, item, destination, route='direct'):
        if route == 'direct' and self.direct_blocked():
            return {'success': False, 'reason': '公共路径被实际伙伴几何体占用',
                    'physical_attempt': False, 'state': self.state()}
        body = self.objects[item]
        source = np.array(p.getBasePositionAndOrientation(body, physicsClientId=self.client)[0])
        self.set_grip(.04, 'open')
        errors = [self.move([source[0], source[1], .26], 'approach')]
        errors.append(self.move([source[0], source[1], source[2]], 'descend'))
        self.set_grip(0, 'grasp')
        finger_contacts = [c for c in p.getContactPoints(self.robot, body,
                                  physicsClientId=self.client) if c[3] in (9, 10)]
        errors.append(self.move([source[0], source[1], .26], 'lift'))
        lifted_z = p.getBasePositionAndOrientation(body, physicsClientId=self.client)[0][2]
        if lifted_z < .12:
            self.set_grip(.04, 'failed_release')
            return {'success': False, 'reason': '摩擦抓取未抬起物品', 'physical_attempt': True,
                    'finger_contacts': len(finger_contacts), 'lifted_z': lifted_z,
                    'ee_errors': errors, 'state': self.state()}
        target = self.goal(item, destination)
        if route == 'direct':
            errors.append(self.move([.54, 0, .26], 'transit_direct'))
        else:
            side = -.37 if target[1] < 0 else .37
            errors.append(self.move([source[0], side, .26], 'transit_detour'))
            errors.append(self.move([target[0], side, .26], 'transit_detour'))
        errors.append(self.move([target[0], target[1], .26], 'above_goal'))
        errors.append(self.move(target, 'place'))
        self.set_grip(.04, 'release')
        self.move([target[0], target[1], .26], 'retreat')
        # 每种策略共享的中性停车位，防止上一抓放无意阻塞伙伴滑轨。
        self.phase = 'park'
        self.command_joints(self.home)
        self.simulate(240)
        success = self.at_goal(item, destination)
        return {'success': success, 'reason': '物品静止在目标槽' if success else '落点/速度未满足目标',
                'physical_attempt': True, 'finger_contacts': len(finger_contacts),
                'lifted_z': lifted_z, 'ee_errors': errors, 'state': self.state()}

    def close(self):
        if self.trace:
            self.trace.close()
        p.disconnect(self.client)
