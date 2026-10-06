"""VICO完整蒙皮在MuJoCo中的站姿、动作和有约束伸手显示。"""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation


DEFAULT_AVATAR=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/assets/native_avatar/current')


class AvatarRig:
    def __init__(self, directory=DEFAULT_AVATAR):
        self.directory=Path(directory).resolve();self.metadata=json.loads((self.directory/'avatar.json').read_text())
        with np.load(self.directory/'rig.npz') as data:self.data={key:data[key] for key in data.files}
        self.names=self.metadata['joint_names'];self.nodes=self.data['joint_nodes']
        self.parents=self.data['parents'];self.children={i:[] for i in range(len(self.parents))}
        for i,parent in enumerate(self.parents):
            if parent>=0:self.children[parent].append(i)
        self.order=[]
        def visit(i):
            self.order.append(i)
            for child in self.children[i]:visit(child)
        for i in np.flatnonzero(self.parents<0):visit(i)
        self.base=np.array([.25,.60,0.])
        self.local=self.idle_rotations(0)
        pose=self.forward(self.local)
        vertices=self.deformed_vertices(pose)
        self.base[2]-=float(vertices[:,2].min())
        self.previous=None
        self.walk_phase=0.;self.walk_blend=0.;self.last_pose_time=None
        self.stride_length=float(np.linalg.norm(self.data['walk_trans'][-1,[0,2]]-self.data['walk_trans'][0,[0,2]]))
        self.tip=self.nodes[self.names.index('RightHandIndex4')]
        chain=['Spine','Spine1','Spine2','RightShoulder','RightArm','RightForeArm','RightHand']
        self.chain=[int(self.nodes[self.names.index(name)]) for name in chain]

    def motion_rotations(self, frame, motion='idle'):
        rotations=self.data['rotations'].copy()
        values=self.data[motion+'_delta'];index=int(np.floor(frame));fraction=frame-index
        first=values[index%len(values)];second=values[(index+1)%len(values)]
        difference=Rotation.from_matrix(first.transpose(0,2,1)@second).as_rotvec()
        delta=first@Rotation.from_rotvec(difference*fraction).as_matrix()
        rotations[self.nodes]=rotations[self.nodes]@delta
        return rotations

    def idle_rotations(self, frame):return self.motion_rotations(frame)

    def forward(self, rotations):
        transforms=np.broadcast_to(np.eye(4),(len(self.parents),4,4)).copy()
        for node in self.order:
            local=np.eye(4);local[:3,:3]=rotations[node]@np.diag(self.data['scales'][node])
            local[:3,3]=self.data['translations'][node]
            parent=self.parents[node]
            transforms[node]=transforms[parent]@local if parent>=0 else local
        result=transforms[self.nodes].copy()
        result[:,:3,3]+=self.base
        result[:,:3,:3]/=np.linalg.norm(result[:,:3,:3],axis=1)[:,None,:]
        return result

    def deformed_vertices(self, poses):
        vertices=self.data['vertices'];joints=self.data['joints'];weights=self.data['weights']
        bind=self.data['bind_rotations'];position=self.data['bind_positions']
        output=np.zeros_like(vertices,dtype=float)
        for slot in range(joints.shape[1]):
            ids=joints[:,slot]
            local=np.einsum('vji,vj->vi',bind[ids],vertices-position[ids])
            posed=np.einsum('vij,vj->vi',poses[ids,:3,:3],local)+poses[ids,:3,3]
            output+=weights[:,slot,None]*posed
        return output

    def pose(self, time_s, fingertip, *, initialise=False, body_delta=None, walking=False):
        dt=.05 if self.last_pose_time is None else max(0.,time_s-self.last_pose_time)
        self.last_pose_time=time_s
        if body_delta is not None:
            # Character faces -Y: reversing the cached gait gives a slow backward
            # clearance step while the person can keep watching the workbench.
            self.walk_phase-=float(body_delta[1])/max(self.stride_length,.1)*(len(self.data['walk_delta'])-1)
        desired=1. if walking else 0.
        self.walk_blend+=float(np.clip(desired-self.walk_blend,-dt/.6,dt/.6))
        rotations=self.idle_rotations(time_s*self.metadata['motion_fps'])
        if self.walk_blend>0:
            gait=self.motion_rotations(self.walk_phase,'walk')
            relative=Rotation.from_matrix(rotations.transpose(0,2,1)@gait).as_rotvec()
            rotations=rotations@Rotation.from_rotvec(relative*self.walk_blend).as_matrix()
        # Ground the source motion before the arm IK; the skin is not a collider.
        self.base[2]-=float(self.deformed_vertices(self.forward(rotations))[:,2].min())
        neutral=rotations.copy()
        # Start from the previous articulated solution, retaining ongoing arm intent.
        if self.previous is not None:rotations[self.chain]=self.previous[self.chain]
        for iteration in range(18):
            poses=self.forward(rotations);tip=poses[self.names.index('RightHandIndex4'),:3,3]
            if np.linalg.norm(tip-fingertip)<.003:break
            # Arm first. Only use small spine compensation when the arm alone
            # cannot reach, instead of satisfying a fingertip target by folding the torso.
            active=self.chain[3:] if iteration<12 else self.chain
            for node in reversed(active):
                poses=self.forward(rotations);joint=self.nodes.tolist().index(node)
                origin=poses[joint,:3,3];tip=poses[self.names.index('RightHandIndex4'),:3,3]
                current=tip-origin;target=np.asarray(fingertip)-origin
                axis=np.cross(current,target);norm=np.linalg.norm(axis)
                if norm<1e-10:continue
                angle=np.arctan2(norm,np.dot(current,target))
                parent=self.parents[node]
                parent_joint=self.nodes.tolist().index(parent) if parent in self.nodes else None
                parent_rotation=poses[parent_joint,:3,:3] if parent_joint is not None else np.eye(3)
                world_delta=Rotation.from_rotvec(axis/norm*min(angle,.18)).as_matrix()
                rotations[node]=parent_rotation.T@world_delta@parent_rotation@rotations[node]
                relative=Rotation.from_matrix(neutral[node].T@rotations[node]).as_rotvec()
                name=self.names[joint]
                limit=.10 if name.startswith('Spine') else .35 if name=='RightShoulder' else .65 if name=='RightHand' else 2.2
                if np.linalg.norm(relative)>limit:
                    relative*=limit/np.linalg.norm(relative)
                    rotations[node]=neutral[node]@Rotation.from_rotvec(relative).as_matrix()
        if self.previous is not None and not initialise:
            for node in self.chain:
                delta=Rotation.from_matrix(self.previous[node].T@rotations[node]).as_rotvec()
                speed=1.2 if self.names[self.nodes.tolist().index(node)].startswith('Spine') else 2.8
                limit=speed/20
                if np.linalg.norm(delta)>limit:delta*=limit/np.linalg.norm(delta)
                rotations[node]=self.previous[node]@Rotation.from_rotvec(delta).as_matrix()
        self.previous=rotations.copy();self.local=rotations
        return self.forward(rotations)


def add_avatar(root, rig):
    asset=root.find('asset');world=root.find('worldbody')
    ET.SubElement(asset,'texture',name='hrc_avatar_texture',type='2d',file=str(rig.directory/rig.metadata['texture_file']))
    ET.SubElement(asset,'material',name='hrc_avatar_material',texture='hrc_avatar_texture',rgba='1 1 1 1',specular='.05',shininess='.1')
    deformable=root.find('deformable')
    if deformable is None:deformable=ET.SubElement(root,'deformable')
    ET.SubElement(deformable,'skin',name='hrc_avatar_skin',file=str(rig.directory/'alex.skn'),material='hrc_avatar_material',group='1')
    bind=rig.data['bind_positions'];rot=rig.data['bind_rotations']
    quaternion=Rotation.from_matrix(rot).as_quat()[:,[3,0,1,2]]
    for index in range(len(rig.names)):
        ET.SubElement(world,'body',name=f'hrc_avatar_j{index:02d}',mocap='true',
                      pos=' '.join(map(str,bind[index]+rig.base)),quat=' '.join(map(str,quaternion[index])))


class NativeAvatarDisplay:
    def __init__(self, env, rig):
        self.env,self.rig=env,rig
        self.mocaps=[env.sim.model.body_mocapid[env.sim.model.body_name2id(f'hrc_avatar_j{i:02d}')]
                     for i in range(len(rig.names))]
        self.records=[];self.last_time=None;self.last_base=rig.base.copy()

    def update(self, fingertip, *, initialise=False, walking=False):
        time_s=float(self.env.sim.data.time)
        delta=self.rig.base-self.last_base;self.last_base=self.rig.base.copy()
        poses=self.rig.pose(time_s,fingertip,initialise=initialise,body_delta=delta,walking=walking)
        quaternion=Rotation.from_matrix(poses[:,:3,:3]).as_quat()[:,[3,0,1,2]]
        self.env.sim.data.mocap_pos[self.mocaps]=poses[:,:3,3]
        self.env.sim.data.mocap_quat[self.mocaps]=quaternion
        actual_tip=poses[self.rig.names.index('RightHandIndex4'),:3,3]
        self.records.append({'physics_time_s':time_s,'physical_fingertip':np.asarray(fingertip).tolist(),
                             'display_fingertip':actual_tip.tolist(),'alignment_error_m':float(np.linalg.norm(actual_tip-fingertip)),
                             'body_position':self.rig.base.tolist(),'walking_blend':self.rig.walk_blend,
                             'bone_positions':poses[:,:3,3].tolist(),'bone_quaternions':quaternion.tolist()})
