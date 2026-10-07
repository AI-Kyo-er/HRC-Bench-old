import json

import pytest

from hrc_pilot.joint_video_captions import captions_are_current,ensure_research_captions,make_captions,stamp,wrap_line


def data():
    trace=[{'time_s':t,'human_execution':{'phase':'transfer_translate','held_object':'cream_cheese_1'}}
           for t in [0.,.05,.1]]
    human=[{'time_s':0.,'choice':{'action':'wait','message':'Task complete.'}}]
    plans=[{'time_s':0.,'decision':{'mode':'execute'},'model_selected_skill_id':'cream_in_bowl'}]
    contexts=[{'time_s':.1,'text':'来客取消饮品。'}]
    timeline={'fps':20,'frames':[{'benchmark_time_s':t,'video_time_s':t+10} for t in [0.,.05,.1]]}
    return trace,human,plans,contexts,timeline,[{'source':'actual_vla_coordinator_instruction'}]*2


def test_choice_is_not_completion_and_actual_motion_and_private_cue_have_correct_timing():
    result=make_captions(*data())
    before,after=result.split('00:00:10.100 -->')
    assert '人选择：等候；实际：搬运／持有奶酪' in before
    assert '来客' not in before and '来客取消饮品。' in after
    assert 'Task complete' not in result
    assert '00:00:10.000 --> 00:00:10.100' in result


def test_unbound_video_state_is_rejected():
    args=list(data());args[4]['frames'][1]['benchmark_time_s']=.08
    with pytest.raises(ValueError,match='实际轨迹'):
        make_captions(*args)


def test_timestamp_rounding_carries_across_minutes():
    assert stamp(59.9996)=='00:01:00.000'


def test_chinese_context_is_wrapped_without_losing_the_tail():
    text='来客说马上到达，想先喝桌边酒瓶中的饮品，点心可以稍后取用。'
    wrapped=wrap_line(text)
    assert wrapped.replace('\n','')==text
    assert all(len(line)<=24 for line in wrapped.splitlines())


def test_caption_generation_preserves_raw_inputs_and_detects_stale_or_added_sources(tmp_path):
    ep=tmp_path/'episode';ep.mkdir();trace,human,plans,contexts,timeline,controls=data()
    for name,value in [('trace.jsonl',trace),('human_policy_io.jsonl',human),
                       ('robot_planner_io.jsonl',plans),('robot_control.jsonl',controls)]:
        (ep/name).write_text(''.join(json.dumps(row)+'\n' for row in value))
    (ep/'video_timeline.json').write_text(json.dumps(timeline))
    (ep/'demo.mp4').write_bytes(b'trusted-video-gate-fixture-not-a-decoder-test')
    for name in ['summary.json','provenance.json','interaction_verification.json','independent_video_verification.json']:
        (tmp_path/name).write_text('{"status":"verified"}')
    before={p:p.read_bytes() for p in ep.iterdir()}
    ensure_research_captions(tmp_path)
    assert all(p.read_bytes()==content for p,content in before.items())
    assert captions_are_current(tmp_path)
    (ep/'private_context.jsonl').write_text(json.dumps(contexts[0])+'\n')
    assert not captions_are_current(tmp_path)
    ensure_research_captions(tmp_path)
    assert captions_are_current(tmp_path)
    (ep/'human_policy_io.jsonl').write_text('')
    assert not captions_are_current(tmp_path)


def test_previous_caption_does_not_override_failed_verification(tmp_path):
    (tmp_path/'summary.json').write_text('{}')
    (tmp_path/'interaction_verification.json').write_text('{"status":"failed"}')
    with pytest.raises(ValueError,match='独立核验'):
        ensure_research_captions(tmp_path)
