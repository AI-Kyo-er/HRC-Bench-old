"""独立核对两次模型推理、原始意图来源及动作层未修改个人目标。"""
import json

from .native_autonomous_human import validate_targets
from types import SimpleNamespace


def verify_reflective_records(planners,motors):
    assert planners and motors
    targets=[];revision=0;intention='';previous_time=-1.
    for identifier,row in enumerate(planners):
        assert row['planner_decision_id']==identifier and row['time_s']>previous_time
        previous_time=row['time_s'];public=json.loads(row['public_input'].split('\n',1)[1])
        assert public['time_s']==row['time_s']
        assert row['public_input'].startswith('阶段：意图反思\n')
        assert public['your_previous_personal_targets']==targets
        assert not {'task_success','human_goal_success','personal_evidence'}.intersection(public)
        assert '只进行较长期意图反思' in row['system_prompt']
        allow_pairs=row.get('target_decoder')=='dict_or_pair_v1'
        if row['validation_error'] is None:
            raw=row['raw_output'];value=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
            chosen,error=validate_targets(value['personal_targets'],SimpleNamespace(objects=public['objects_xyz'],regions=public['regions_xyz']),allow_pair_arrays=allow_pairs)
            assert error is None
            if sorted(chosen,key=lambda t:t['object_id'])!=sorted(targets,key=lambda t:t['object_id']):revision+=1
            targets=chosen;intention=value['long_term_intention'][:500]
            assert row['active_intention_plan']['personal_targets']==targets
            assert row['active_intention_plan']['decision_kind']==value['decision_kind']
        else:
            raw=row['raw_output'];invalid=False
            try:
                value=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
                _,target_error=validate_targets(value.get('personal_targets'),SimpleNamespace(objects=public['objects_xyz'],regions=public['regions_xyz']),allow_pair_arrays=allow_pairs)
                invalid=bool(target_error or value.get('decision_kind') not in {'continue','revise','suspend','finish_activity'}
                    or not isinstance(value.get('long_term_intention'),str) or not value['long_term_intention'].strip()
                    or not isinstance(value.get('plan',[]),list) or any(not isinstance(p,str) for p in value.get('plan',[])))
            except (ValueError,TypeError,AttributeError):invalid=True
            assert invalid
        state=row['retained_or_accepted_personal_goal_state']
        assert state['personal_targets']==targets and state['revision']==revision and state['long_term_intention']==intention
        assert state['target_validation_error']==row['validation_error']
    emitted=[]
    for row in motors:
        assert row['human_policy_architecture']=='reflective_intent_then_motor'
        assert row['public_input'].startswith('阶段：当前动作\n')
        public=json.loads(row['public_input'].split('\n',1)[1]);planner=planners[row['planner_decision_id']]
        assert row['planner_decision_id']==max(p['planner_decision_id'] for p in planners if p['time_s']<=row['time_s'])
        assert planner['time_s']<=row['time_s'] and public['planner_decision_id']==planner['planner_decision_id']
        assert row['personal_goal_state']==planner['retained_or_accepted_personal_goal_state']
        assert public['active_intention_plan']==planner['active_intention_plan']
        assert public['your_previous_personal_targets']==row['personal_goal_state']['personal_targets']
        assert '不在此层修改personal_targets' in row['system_prompt']
        emitted.extend(row['negotiation_proposal_messages'])
        if row['parse_error'] is None:
            raw=row['raw_output'];motor=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
            validation=row['command_validation']
            assert validation['requested']['intent']==motor.get('intent','observe')
            assert validation['accepted']['intent']==row['parsed_decision']['intent']
            if validation['status']=='accepted':assert row['parsed_decision']['intent']==motor['intent']
    assert emitted==[message for p in planners for message in p['public_proposal_messages']]
    return {'status':'verified','planner_neural_calls':len(planners),'motor_neural_calls':len(motors),
            'total_neural_calls':len(planners)+len(motors),'raw_stage_outputs_separate':True,
            'planner_targets_not_overwritten_by_motor_verified':True,'plans_not_automatically_routed':True}
