from types import SimpleNamespace

from hrc_pilot.native_scene_catalog import resolve_goal,scene_regions
from hrc_pilot.native_goal_evidence import NativeJointEvidence


def test_native_region_goal_resolves_receiver_from_site_parent_not_string_guess():
    env=SimpleNamespace(env=SimpleNamespace(parsed_problem={'goal_state':[['on','wine_1','rack_1_top_region']]},
        obj_body_id={'wine_1':0,'rack_1':1},object_sites_dict={'rack_1_top_region':SimpleNamespace(parent_name='rack_1')}))
    assert resolve_goal(env)['receiver_id']=='rack_1'


def test_inventory_regions_do_not_require_cookie_or_plate():
    r=scene_regions({'cheese_1':(0,0,.92),'bowl_1':(.1,.1,.93),'cabinet_1':(0,.2,.9)},['cheese_1','bowl_1'])
    assert 'cheese_1_personal' in r and 'cabinet_1_personal' not in r


def test_joint_completion_requires_actual_change_and_continuous_stability():
    score=NativeJointEvidence({'kind':'open','receiver_id':'cabinet','joint_names':['drawer']})
    def r(t,q):return {'time_s':t,'articulated_joints':{'drawer':q}}
    assert not score.update(r(0,0),r(.05,0),True)
    assert not score.update(r(.05,0),r(.10,.1),True)
    for t in [.15,.20,.25]:assert not score.update(r(t-.05,.1),r(t,.1),True)
    assert score.update(r(.25,.1),r(.30,.1),True)
    assert 'released_stable_placement' not in score.records[-1]
