import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from hrc_pilot.area_human_executor import AreaHumanExecutor
from hrc_pilot.geometry_frame_replay import replay_recorded_geometry
from hrc_pilot.placement_areas import table_placement_areas


def test_real_geometry_continuous_macros_separate_three_objects_without_robot_pose_writes():
    pytest.importorskip('robosuite')
    from robosuite.utils.binding_utils import MjSim
    root = Path('results/continuous_v2/workspace_snack_detour_symbolic_20261008')
    if not root.exists():pytest.skip('缺少保留的真实场景资格材料')
    sim = MjSim.from_xml_file(str((root/'episode/scene.xml').resolve()))
    first = json.loads((root/'episode/trace.jsonl').read_text().splitlines()[0])
    replay_recorded_geometry(sim.model._model, sim.data._data, first)
    layout = json.loads((root/'workspace_layout.json').read_text())
    movable = ['akita_black_bowl_1', 'cream_cheese_1', 'wine_bottle_1', 'plate_1']
    bodies = {name: sim.model.body_name2id(name+'_main') for name in first['objects']}
    inner = SimpleNamespace(obj_body_id=bodies, objects_dict=dict.fromkeys(movable),
                            object_states_dict={}, _pre_action=lambda *args, **kwargs:None,
                            _hrc_table_surface_positions=layout['zone_surface_positions'],
                            _hrc_placement_areas=table_placement_areas(layout))
    actor = AreaHumanExecutor(SimpleNamespace(sim=sim,env=inner),layout['zone_surface_positions'],auto_buffer=True)
    # 此CPU测试只检查实际几何与连续动作，不重建保存XML之外的avatar rig元数据。
    actor._display = lambda position: None
    robot_ids = [sim.model.get_joint_qpos_addr('robot0_joint'+str(i)) for i in range(1,8)]
    robot = sim.data.qpos[robot_ids].copy();targets=[]
    for request,obj in enumerate(['akita_black_bowl_1','plate_1','wine_bottle_1']):
        choice={'action':'relocate','object_id':obj,'destination':'snack_delivery'}
        actor.accept_choice(choice,request)
        assert actor.receipts[-1]['accepted']
        targets.append(actor.receipts[-1]['area_placement']['body_target_xyz'])
        for tick in range(20000):
            if tick==100:actor.accept_choice(choice,request+10)
            actor.physics_step();sim.forward();sim.data.time+=actor.dt
            if actor.phase=='idle':break
        assert actor.phase=='idle' and actor.held is None
        np.testing.assert_allclose(actor.object_position(obj),targets[-1],atol=.0041)
    assert len({tuple(np.round(t[:2],3)) for t in targets})==3
    np.testing.assert_array_equal(sim.data.qpos[robot_ids],robot)
    assert all(r['robot_pose_writes']==0 and np.linalg.norm(r['hand_velocity'])<=.200001 for r in actor.records)
