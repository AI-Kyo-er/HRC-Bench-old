"""独立低载台真实摩擦投递；控制共享，载台每物理tick自主推进。"""
import copy
import gzip
import json
import math
from pathlib import Path

import numpy as np
import pybullet as p
import pybullet_data

from experiments.physical.world import DT, ITEMS
from experiments.structure_v5.world_v3 import AuditedReworkWorld

CONFIG_PATH = Path(__file__).with_name('transport_config_v1.json')
CONFIG = json.loads(CONFIG_PATH.read_text())


def profile_distance(seconds):
    velocity, ramp, travel = CONFIG['nominal_velocity_m_s'], CONFIG['ramp_seconds'], CONFIG['travel_m']
    duration = travel / velocity + ramp
    t = max(0, seconds)
    if t < ramp:
        return velocity * t * t / (2 * ramp)
    if t < duration - ramp:
        return velocity * (t - ramp / 2)
    if t < duration:
        remain = duration - t
        return travel - velocity * remain * remain / (2 * ramp)
    return travel


class TransportWorld(AuditedReworkWorld):
    def __init__(self, seed=0, trace_path=None, render_dir=None):
        # 独立场景初始化，不调用旧场景后再重置/迁移blue。
        self.client = p.connect(p.DIRECT)
        self.tick, self.phase = 0, 'initialization'
        self.trace = gzip.open(trace_path, 'wt') if trace_path else None
        self.render_dir = Path(render_dir) if render_dir else None
        self.frames = 0
        self.rework_source_side = None
        self.parking_waypoint_errors = []
        self.robot_target_item = None
        self.delivery_start_tick = None
        self.delivery_event = None
        self.goal_first_ticks = {}
        self.support_audit = {'ticks': 0, 'records': 0, 'max_normal_force': 0, 'transport_ticks': 0,
                              'transport_supported_ticks': 0, 'max_relative_xy_error': 0}
        self.contact_audit = {'robot_partner_ticks': 0, 'max_normal_force': 0, 'phases': {}, 'total_ticks': 0}
        self.object_partner_audit = {'ticks': 0, 'records': 0, 'max_normal_force': 0, 'phases': {}}
        self.non_target_robot_audit = {'ticks': 0, 'records': 0, 'max_normal_force': 0, 'items': {}}
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.client)
        p.setGravity(0, 0, -9.81, physicsClientId=self.client)
        p.setTimeStep(DT, physicsClientId=self.client)
        p.setPhysicsEngineParameter(numSolverIterations=100, deterministicOverlappingPairs=1, physicsClientId=self.client)
        self.table = p.loadURDF('plane.urdf', physicsClientId=self.client)
        self.robot = p.loadURDF('franka_panda/panda.urdf', useFixedBase=True, physicsClientId=self.client)
        self.home = [0, -.4, 0, -2.5, 0, 2.1, .8]
        for j, q in enumerate(self.home):
            p.resetJointState(self.robot, j, q, physicsClientId=self.client)
        for j in (9, 10):
            p.resetJointState(self.robot, j, .04, physicsClientId=self.client)
            p.changeDynamics(self.robot, j, lateralFriction=2, spinningFriction=.01, physicsClientId=self.client)
        self.orientation = p.getQuaternionFromEuler([math.pi, 0, 0])
        self.objects = {}
        rng = np.random.default_rng(seed)
        for item, y, color in zip(ITEMS, (-.16, 0, .16), ((.9, .15, .1, 1), (.1, .25, .9, 1), (.1, .8, .2, 1))):
            xy = np.array([.42, y]) + rng.uniform(-.006, .006, 2)
            xyz = CONFIG['blue_center_start'] if item == 'blue' else [*xy, .023]
            self.objects[item] = self.box([.022, .022, .022], xyz, .06, color)
            p.changeDynamics(self.objects[item], -1, lateralFriction=CONFIG['blue_friction'],
                             spinningFriction=.01, rollingFriction=.001, physicsClientId=self.client)
        self.trays = {}
        for name, y in (('left', -.25), ('right', .25)):
            self.trays[name] = self.box([.10, .085, .005], [.65, y, .005], 0, (.7, .65, .5, 1))
            for dy in (-.085, .085):
                self.box([.1, .005, .009], [.65, y + dy, .019], 0, (.6, .5, .35, 1))
        size = CONFIG['carrier_half_extents']
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=size, physicsClientId=self.client)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=size, rgbaColor=[.7, .2, .7, 1], physicsClientId=self.client)
        self.partner = p.createMultiBody(baseMass=0, basePosition=[.65, 0, CONFIG['carrier_center_start'][2]], linkMasses=[1],
            linkCollisionShapeIndices=[col], linkVisualShapeIndices=[vis], linkPositions=[[0, 0, 0]],
            linkOrientations=[[0, 0, 0, 1]], linkInertialFramePositions=[[0, 0, 0]],
            linkInertialFrameOrientations=[[0, 0, 0, 1]], linkParentIndices=[0],
            linkJointTypes=[p.JOINT_PRISMATIC], linkJointAxis=[[0, 1, 0]], physicsClientId=self.client)
        p.resetJointState(self.partner, 0, .6, physicsClientId=self.client)
        p.changeDynamics(self.partner, 0, lateralFriction=CONFIG['carrier_friction'], physicsClientId=self.client)
        self.partner_target, self.grip = .6, .04
        self.command_joints(self.home)
        self.simulate(180)
        self.initial_state = copy.deepcopy(self.state())

    def start_delivery(self):
        if self.delivery_start_tick is not None:
            raise RuntimeError('自主运输只启动一次。')
        self.delivery_start_tick = self.tick

    def delivery_facts(self):
        joint = p.getJointState(self.partner, 0, physicsClientId=self.client)
        carrier = np.array(p.getLinkState(self.partner, 0, computeForwardKinematics=True, physicsClientId=self.client)[0])
        blue = np.array(p.getBasePositionAndOrientation(self.objects['blue'], physicsClientId=self.client)[0])
        blue_velocity = np.array(p.getBaseVelocity(self.objects['blue'], physicsClientId=self.client)[0])
        support = p.getContactPoints(self.objects['blue'], self.partner, physicsClientId=self.client)
        supported = any(c[8] <= CONFIG['support_contact_max_distance'] and c[9] > CONFIG['support_contact_min_force'] for c in support)
        relative = blue - carrier
        relative_velocity = blue_velocity - np.array([0, joint[1], 0])
        facts = dict(carrier_joint=joint[0], carrier_speed=joint[1], relative_position=relative.tolist(),
            blue_speed=float(np.linalg.norm(blue_velocity)), relative_speed=float(np.linalg.norm(relative_velocity)),
            supported=supported, support_records=len(support),
            support_force=sum(c[9] for c in support), support_min_distance=min((c[8] for c in support), default=None))
        facts['satisfied'] = bool(self.delivery_start_tick is not None and
            abs(joint[0]) < CONFIG['carrier_goal_joint_tolerance'] and abs(joint[1]) < CONFIG['carrier_speed_limit'] and
            np.linalg.norm(relative[:2]) < CONFIG['blue_relative_xy_tolerance'] and
            CONFIG['blue_relative_z_range'][0] < relative[2] < CONFIG['blue_relative_z_range'][1] and
            facts['blue_speed'] < CONFIG['blue_world_speed_limit'] and facts['relative_speed'] < CONFIG['blue_relative_speed_limit'] and supported)
        return facts

    def state(self):
        state = super().state()
        state.update(partner_velocity=p.getJointState(self.partner, 0, physicsClientId=self.client)[1],
            partner_command=self.partner_target, delivery_start_tick=self.delivery_start_tick,
            delivery_event=copy.deepcopy(self.delivery_event), delivery_facts=self.delivery_facts(),
            robot_target_item=self.robot_target_item)
        return state

    def simulate(self, ticks):
        for _ in range(ticks):
            if self.delivery_start_tick is not None:
                elapsed = (self.tick + 1 - self.delivery_start_tick) * DT
                self.partner_target = CONFIG['travel_m'] - profile_distance(elapsed)
            p.setJointMotorControl2(self.partner, 0, p.POSITION_CONTROL, targetPosition=self.partner_target,
                force=100, maxVelocity=CONFIG['nominal_velocity_m_s'], physicsClientId=self.client)
            p.stepSimulation(physicsClientId=self.client)
            self.tick += 1
            facts = self.delivery_facts()
            if self.delivery_event is None and facts['satisfied']:
                self.delivery_event = dict(first_tick=self.tick, time_since_start=(self.tick-self.delivery_start_tick)*DT,
                                           facts=copy.deepcopy(facts), content='实际承载、相对位姿/速度及载台到位共同首次满足交付。')
            state = self.state()
            contacts = state['contacts']
            self.contact_audit['total_ticks'] += 1
            robot_contacts = [c for c in contacts if {c['body_a'], c['body_b']} == {self.robot, self.partner}]
            if robot_contacts:
                self.contact_audit['robot_partner_ticks'] += 1
                self.contact_audit['max_normal_force'] = max(self.contact_audit['max_normal_force'], max(c['normal_force'] for c in robot_contacts))
                phases = self.contact_audit['phases']; phases[self.phase] = phases.get(self.phase, 0)+1
            forbidden_bodies = {self.objects['red'], self.objects['green']}
            other_contacts = [c for c in contacts if (c['body_a'] == self.partner and c['body_b'] in forbidden_bodies) or (c['body_b'] == self.partner and c['body_a'] in forbidden_bodies)]
            if other_contacts:
                self.object_partner_audit['ticks'] += 1
                self.object_partner_audit['records'] += len(other_contacts)
                self.object_partner_audit['max_normal_force'] = max(self.object_partner_audit['max_normal_force'], max(c['normal_force'] for c in other_contacts))
            support = [c for c in contacts if {c['body_a'], c['body_b']} == {self.objects['blue'], self.partner}]
            self.support_audit['ticks'] += int(bool(support))
            self.support_audit['records'] += len(support)
            self.support_audit['max_normal_force'] = max(self.support_audit['max_normal_force'], max((c['normal_force'] for c in support), default=0))
            if self.delivery_start_tick is not None and (self.delivery_event is None or self.delivery_event['first_tick'] == self.tick):
                self.support_audit['transport_ticks'] += 1
                self.support_audit['transport_supported_ticks'] += int(facts['supported'])
                self.support_audit['max_relative_xy_error'] = max(self.support_audit['max_relative_xy_error'], float(np.linalg.norm(facts['relative_position'][:2])))
            non_target = []
            for item, body in self.objects.items():
                if item != self.robot_target_item:
                    found = [c for c in contacts if {c['body_a'], c['body_b']} == {self.robot, body}]
                    if found:
                        self.non_target_robot_audit['items'][item] = self.non_target_robot_audit['items'].get(item, 0) + 1
                        non_target.extend(found)
            if non_target:
                self.non_target_robot_audit['ticks'] += 1
                self.non_target_robot_audit['records'] += len(non_target)
                self.non_target_robot_audit['max_normal_force'] = max(self.non_target_robot_audit['max_normal_force'], max(c['normal_force'] for c in non_target))
            for item in ('red', 'blue'):
                if item not in self.goal_first_ticks and self.at_goal(item, 'left'):
                    self.goal_first_ticks[item] = self.tick
            if self.trace:
                self.trace.write(json.dumps(state)+'\n')
            if self.render_dir and self.tick % 48 == 0:
                self.capture()

    def pick_place(self, item, destination, route='direct'):
        self.robot_target_item = item
        try:
            return super().pick_place(item, destination, route)
        finally:
            self.robot_target_item = None

    def wait_delivery(self):
        before = self.tick
        self.phase = 'wait_delivery'
        for _ in range(CONFIG['wait_budget_ticks']):
            if self.delivery_event is not None:
                break
            self.simulate(1)
        return dict(success=self.delivery_event is not None, ticks=self.tick-before,
                    delivery_event=copy.deepcopy(self.delivery_event))
