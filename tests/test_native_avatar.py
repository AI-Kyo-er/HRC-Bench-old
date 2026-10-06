import xml.etree.ElementTree as ET

import numpy as np
import pytest

from hrc_pilot.native_avatar import AvatarRig, DEFAULT_AVATAR, add_avatar


pytestmark=pytest.mark.skipif(not (DEFAULT_AVATAR/'avatar.json').exists(),reason='需要已导出的本地VICO资产')


def test_skinned_vertices_match_mujoco_bind_and_animated_poses():
    mujoco=pytest.importorskip('mujoco')
    if tuple(map(int,mujoco.__version__.split('.')[:2]))<(3,0):pytest.skip('原生蒙皮使用MuJoCo3')
    rig=AvatarRig();root=ET.fromstring('<mujoco><asset/><worldbody/></mujoco>');add_avatar(root,rig)
    model=mujoco.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'));data=mujoco.MjData(model)
    scene=mujoco.MjvScene(model,maxgeom=1000);option=mujoco.MjvOption();camera=mujoco.MjvCamera()
    from scipy.spatial.transform import Rotation
    for pose in [None,rig.pose(0,np.array([.25,.60,1.12]),initialise=True)]:
        if pose is not None:
            for i in range(65):
                idx=model.body_mocapid[model.body(f'hrc_avatar_j{i:02d}').id]
                data.mocap_pos[idx]=pose[i,:3,3]
                data.mocap_quat[idx]=Rotation.from_matrix(pose[i,:3,:3]).as_quat()[[3,0,1,2]]
        mujoco.mj_forward(model,data)
        mujoco.mjv_updateScene(model,data,option,None,camera,mujoco.mjtCatBit.mjCAT_ALL,scene)
        expected=rig.data['vertices']+rig.base if pose is None else rig.deformed_vertices(pose)
        np.testing.assert_allclose(scene.skinvert.reshape(-1,3),expected,atol=3e-6)


def test_reach_preserves_bone_lengths_and_follows_physical_contact_target():
    rig=AvatarRig();start=np.array([.25,.60,1.12]);end=np.array([.05,.25,.92])
    reference=rig.pose(0,start,initialise=True)
    mapping={node:i for i,node in enumerate(rig.nodes)}
    pairs=[(mapping[rig.parents[node]],i) for i,node in enumerate(rig.nodes) if rig.parents[node] in mapping]
    lengths=np.array([np.linalg.norm(reference[a,:3,3]-reference[b,:3,3]) for a,b in pairs])
    for step in range(1,81):
        target=start+(end-start)*min(step/60,1)
        pose=rig.pose(step/20,target)
        actual=np.array([np.linalg.norm(pose[a,:3,3]-pose[b,:3,3]) for a,b in pairs])
        np.testing.assert_allclose(actual,lengths,atol=1e-6)
    assert np.linalg.norm(pose[rig.names.index('RightHandIndex4'),:3,3]-end)<.015
    for name in ['Spine','Spine1','Spine2']:
        node=rig.nodes[rig.names.index(name)]
        from scipy.spatial.transform import Rotation
        angle=np.linalg.norm(Rotation.from_matrix(rig.idle_rotations(120)[node].T@rig.local[node]).as_rotvec())
        assert angle<.101


def test_walking_skin_grounding_and_transition_are_continuous():
    rig=AvatarRig();target=np.array([.25,.60,1.12])
    rig.pose(0,target,initialise=True)
    previous=None
    for step in range(1,41):
        delta=np.array([0,.01,0]) if step<31 else np.zeros(3)
        rig.base+=delta
        pose=rig.pose(step/20,target+np.array([0,min(step,30)*.01,0]),body_delta=delta,walking=step<31)
        assert abs(rig.deformed_vertices(pose)[:,2].min())<.005
        if previous is not None:assert np.max(np.linalg.norm(pose[:,:3,3]-previous[:,:3,3],axis=1))<.07
        previous=pose
