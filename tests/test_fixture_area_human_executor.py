import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from robosuite.utils.binding_utils import MjSim

from hrc_pilot.fixture_area_human_executor import FixtureAreaHumanExecutor, fixture_executor_override
from hrc_pilot.geometry_frame_replay import replay_recorded_geometry
from hrc_pilot.placement_areas import table_placement_areas


def real_actor(time):
    root=Path('results/continuous_v2/bounded_drink_correction_symbolic_20261009')
    if not root.exists():pytest.skip('缺少保留的柜顶真实场景')
    ep=root/'episode';sim=MjSim.from_xml_file(str((ep/'scene.xml').resolve()))
    row=next(json.loads(l) for l in (ep/'trace.jsonl').read_text().splitlines()
             if l.strip() and json.loads(l)['time_s']==time)
    replay_recorded_geometry(sim.model._model,sim.data._data,row)
    sim.data.time=row['physics_time_s']
    layout=json.loads((root/'workspace_layout.json').read_text())
    regions=json.loads((ep/'task.json').read_text())['regions']
    movable=['akita_black_bowl_1','cream_cheese_1','wine_bottle_1','plate_1']
    inner=SimpleNamespace(obj_body_id={n:sim.model.body_name2id(n+'_main') for n in row['objects']},
        objects_dict=dict.fromkeys(movable),object_states_dict={},_pre_action=lambda *a,**k:None,
        _hrc_table_surface_positions=layout['zone_surface_positions'],
        _hrc_placement_areas=table_placement_areas(layout))
    actor=FixtureAreaHumanExecutor(SimpleNamespace(sim=sim,env=inner),regions,auto_buffer=True)
    actor._display=lambda position:None
    return actor,sim,regions


def test_occupied_fixture_refusal_keeps_selected_goal_and_world_and_is_in_feedback():
    actor,sim,regions=real_actor(36)
    before=sim.data.qpos.copy();old_regions=json.loads(json.dumps(regions))
    choice={'action':'relocate','object_id':'plate_1','destination':'plate_1_on_cabinet'}
    actor.accept_choice(choice,90)
    receipt=actor.public_feedback()['last_receipt']
    assert not receipt['accepted'] and receipt['error']=='destination_area_has_no_free_placement'
    assert receipt['choice']==choice
    assert actor.held is None and actor.phase=='idle'
    np.testing.assert_array_equal(sim.data.qpos,before)
    assert regions==old_regions
    actor.accept_choice(choice,90)
    assert len(actor.receipts)==1


def test_empty_fixture_continuously_executes_same_destination_without_robot_writes():
    actor,sim,_=real_actor(0)
    indices=[sim.model.get_joint_qpos_addr('robot0_joint'+str(i)) for i in range(1,8)]
    robot=sim.data.qpos[indices].copy()
    choice={'action':'relocate','object_id':'plate_1','destination':'plate_1_on_cabinet'}
    actor.accept_choice(choice,90)
    assert actor.receipts[-1]['accepted']
    target=actor.receipts[-1]['fixture_surface_placement']['body_target_xyz']
    for _ in range(25000):
        actor.physics_step();sim.forward();sim.data.time+=actor.dt
        if actor.phase=='idle':break
    assert actor.phase=='idle' and actor.held is None
    np.testing.assert_allclose(actor.object_position('plate_1'),target,atol=.0041)
    np.testing.assert_array_equal(sim.data.qpos[indices],robot)
    assert all(r['robot_pose_writes']==0 and np.linalg.norm(r['hand_velocity'])<=.200001 for r in actor.records)


def test_override_is_only_local_process_and_restores_on_exception():
    import hrc_pilot.area_human_executor as module
    original=module.AreaHumanExecutor
    with pytest.raises(RuntimeError):
        with fixture_executor_override():
            assert module.AreaHumanExecutor is FixtureAreaHumanExecutor
            raise RuntimeError('stop this isolated caller')
    assert module.AreaHumanExecutor is original


def test_refusal_replays_actual_frame_and_rejects_a_forged_acceptance():
    from copy import deepcopy
    from hrc_pilot.fixture_area_human_executor import CONTRACT
    from hrc_pilot.fixture_receipt_verification import verify_fixture_receipts
    actor,sim,regions=real_actor(36)
    choice={'action':'relocate','object_id':'plate_1','destination':'plate_1_on_cabinet'}
    actor.accept_choice(choice,90)
    root=Path('results/continuous_v2/bounded_drink_correction_symbolic_20261009')
    trace=[json.loads(l) for l in (root/'episode/trace.jsonl').read_text().splitlines() if l.strip()]
    human=[{'decision_id':90,'time_s':36.,'choice':choice}]
    result=verify_fixture_receipts({'human_fixture_surface_contract':CONTRACT},trace,human,actor.receipts,sim,regions)
    assert result[0]['status']=='recorded_no_free_point_replayed'
    fake=deepcopy(actor.receipts);fake[0]['accepted']=True
    with pytest.raises(ValueError,match='拒绝标签'):
        verify_fixture_receipts({'human_fixture_surface_contract':CONTRACT},trace,human,fake,sim,regions)


def test_actual_refusal_reaches_intent_and_action_feedback_without_new_strategy():
    from hrc_pilot.intent_observation import intent_observation
    from hrc_pilot.tool_joint_human import execution_tool_result
    actor,sim,regions=real_actor(36)
    choice={'action':'relocate','object_id':'plate_1','destination':'plate_1_on_cabinet'}
    actor.accept_choice(choice,90)
    scene={'time_s':36.,'own_execution':actor.public_feedback(),'objects_xyz':{},'regions_xyz':regions,
           'measured_world':{},'public_dialogue':[],'private_context':[],'action_interface':{}}
    assert intent_observation(scene)['own_execution']['last_rejection_code']=='destination_area_has_no_free_placement'
    feedback=execution_tool_result(90,scene)
    assert feedback['acceptance'] is False and feedback['last_execution_error']=='destination_area_has_no_free_placement'
    assert 'next_action' not in feedback
    assert actor.public_feedback()['last_receipt']['choice']==choice
