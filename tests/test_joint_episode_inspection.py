from copy import deepcopy

import pytest

from hrc_pilot.joint_episode_inspection import make_inspection


def test_video_time_offset_does_not_leak_future_decisions_or_promote_speech_to_execution():
    trace=[{'time_s':t,'human_execution':{'phase':'transfer_translate','held_object':'bowl',
        'motion_in_progress':True,'active_motion_request_id':7,'completed_requests':[]},
        'observable_world':{'current_measured_fact_sentences':['Human is holding bowl.']}}
        for t in [0.,.05,.1]]
    human=[{'time_s':0.,'decision_id':7,'choice':{'action':'wait','message':'Done.'}},
        {'time_s':.1,'decision_id':8,'choice':{'action':'away','message':'Leaving.'},
         'private_agenda_inference':{'agenda_after':{'current_need':'Private call'}}}]
    robot=[{'time_s':.05,'decision':{'mode':'hold','message':'Placed the bowl.'}}]
    controls=[{'source':'actual_vla_coordinator_instruction'},{'source':'coordinator_selected_hold'}]
    timeline={'frames':[{'benchmark_time_s':t,'video_time_s':10+t} for t in [0.,.05,.1]]}
    original=deepcopy((trace,human,robot,controls,timeline))
    result=make_inspection(trace,human,robot,controls,timeline)
    assert (trace,human,robot,controls,timeline)==original
    first,middle,last=result['video_frames']
    assert first['video_time_s']==10 and first['human_decision_row']==0 and first['robot_decision_row']==-1
    assert middle['human_decision_row']==0 and middle['robot_decision_row']==0
    assert last['human_decision_row']==1 and last['actual_robot_action_source'] is None
    assert result['human_decisions'][0]['selected_contribution']['message']=='Done.'
    assert first['human_execution']['held_object']=='bowl' and not first['human_execution']['completed_requests']
    assert not {'score','task_success','agreement'}.intersection(result)


def test_unbound_video_frame_is_not_silently_matched_to_another_state():
    with pytest.raises(ValueError,match='实际轨迹'):
        make_inspection([],[],[],[],{'frames':[{'benchmark_time_s':0.,'video_time_s':0.}]})


def test_pending_episode_cannot_be_published_as_verified_research_inspection(tmp_path):
    import json
    from hrc_pilot.joint_episode_inspection import ensure_episode_inspection
    (tmp_path/'interaction_verification.json').write_text(json.dumps({'status':'pending'}))
    with pytest.raises(ValueError,match='完整输入'):
        ensure_episode_inspection(tmp_path)
    assert not (tmp_path/'episode_inspection.json').exists()
