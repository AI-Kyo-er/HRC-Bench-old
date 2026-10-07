import json
from dataclasses import replace
from pathlib import Path

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.native_deliberative_human import DeliberativeArticulatedHuman
from test_native_grounded_human import observation


def test_same_neural_answer_selects_goals_and_action_without_plan_queue():
    calls=[]
    replies=iter([
        'Consider measured hand </think>'+json.dumps({'personal_targets':[
            {'object_id':'plate','destination':'personal'}],
            'long_term_intention':'整理餐具','intent':'grasp','object_id':'plate','plan':['grasp plate','place plate']}),
        'Consider new public arrangement </think>'+json.dumps({'personal_targets':[
            {'object_id':'plate','destination':'on:bowl'}],
            'long_term_intention':'改变餐具安排','intent':'place','object_id':'plate','destination':'on:bowl'})])
    def generate(prompt):calls.append(prompt);return next(replies)
    p=DeliberativeArticulatedHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),
        model_path=Path('/unused'),autonomous_context='shared_meal',generator=generate)
    p.reset(0);first=p.step(observation())
    assert first.command.intent=='grasp' and p.personal_targets[0]['destination']=='personal'
    assert len(calls)==1
    # 未到神经推理时刻不自动执行plan中的place。
    assert p.step(replace(observation(),time_s=.05)).command.intent=='grasp'
    assert len(calls)==1
    o=observation()
    held=replace(o,time_s=2,human_execution={**o.human_execution,'object_measured_in_hand':'plate',
        'relative_placement_destinations':{'on:bowl':{'receiver_object_id':'bowl','support_xyz':[.1,0,.96]}}})
    second=p.step(held)
    assert second.command.intent=='place' and second.command.destination=='on:bowl'
    assert p.personal_targets==[{'object_id':'plate','destination':'on:bowl'}]
    assert len(calls)==2 and p.audit_state()['total_neural_inferences']==2
    for row in p.policy_io:
        assert row['neural_calls_for_this_decision']==1 and row['thinking_enabled']
        assert row['raw_output']==row['raw_model_output'].rsplit('</think>',1)[-1].strip()
        public=json.loads(row['public_input'].split('\n',1)[1])
        assert public['agent_identity']=={'self':'human','other':'robot'}
        assert not {'personal_evidence','human_goal_success','task_success','your_target_geometry'}.intersection(public)


def test_incomplete_reasoning_does_not_execute_a_json_inside_thoughts():
    p=DeliberativeArticulatedHuman(CONTINUOUS_SCENARIOS['relay'],model_path=Path('/unused'),
        autonomous_context='shared_meal',generator=lambda _: 'Thinking {"intent":"grasp","object_id":"plate"}')
    p.reset(0)
    assert p.step(observation()).command.intent=='observe'
    assert p.policy_io[0]['parse_error'] and p.policy_io[0]['raw_output']==''
    assert p.personal_targets==[]
