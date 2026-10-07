"""独立核对两次模型推理、原始意图来源及动作层未修改个人目标。"""
import json
import numpy as np

from .native_autonomous_human import validate_targets
from types import SimpleNamespace


def verify_reflective_records(planners,motors):
    assert planners and motors
    targets=[];revision=0;intention='';previous_time=-1.
    for identifier,row in enumerate(planners):
        assert row['planner_decision_id']==identifier and row['time_s']>previous_time
        previous_time=row['time_s'];public=json.loads(row['public_input'].split('\n',1)[1])
        assert public['time_s']==row['time_s']
        if 'raw_model_output' in row:
            expected=row['raw_model_output'].rsplit('</think>',1)[-1].strip() if '</think>' in row['raw_model_output'] else ''
            assert row['raw_output']==expected and row['thinking_enabled']
        assert row['public_input'].startswith('阶段：意图反思\n')
        assert public['your_previous_personal_targets']==targets
        assert not {'task_success','human_goal_success','personal_evidence'}.intersection(public)
        assert '只进行较长期意图反思' in row['system_prompt']
        allow_pairs=row.get('target_decoder') in {'dict_or_pair_v1','dict_or_pair_relative_v1'}
        relative=public['action_interface'].get('relative_placement_destinations',{}) if row.get('target_decoder')=='dict_or_pair_relative_v1' else ()
        if row['validation_error'] is None:
            raw=row['raw_output'];value=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
            chosen,error=validate_targets(value['personal_targets'],SimpleNamespace(objects=public['objects_xyz'],regions=public['regions_xyz']),allow_pair_arrays=allow_pairs,relative_destinations=relative)
            assert error is None
            if sorted(chosen,key=lambda t:t['object_id'])!=sorted(targets,key=lambda t:t['object_id']):revision+=1
            targets=chosen;intention=value['long_term_intention'][:500]
            assert row['active_intention_plan']['personal_targets']==targets
            assert row['active_intention_plan']['decision_kind']==value['decision_kind']
        else:
            raw=row['raw_output'];invalid=False
            try:
                value=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
                _,target_error=validate_targets(value.get('personal_targets'),SimpleNamespace(objects=public['objects_xyz'],regions=public['regions_xyz']),allow_pair_arrays=allow_pairs,relative_destinations=relative)
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
        assert row['human_policy_architecture'] in {'reflective_intent_then_motor','grounded_reflective_intent_then_motor'}
        if 'raw_model_output' in row:assert row['raw_output']==row['raw_model_output'] and not row['thinking_enabled']
        assert row['public_input'].startswith('阶段：当前动作\n')
        public=json.loads(row['public_input'].split('\n',1)[1]);planner=planners[row['planner_decision_id']]
        assert row['planner_decision_id']==max(p['planner_decision_id'] for p in planners if p['time_s']<=row['time_s'])
        assert planner['time_s']<=row['time_s'] and public['planner_decision_id']==planner['planner_decision_id']
        assert row['personal_goal_state']==planner['retained_or_accepted_personal_goal_state']
        if public.get('human_input_contract')=='current_intentions_and_measured_geometry_v2':
            state=row['personal_goal_state'];assert public['your_current_personal_targets']==state['personal_targets']
            assert 'your_previous_personal_targets' not in public and 'your_previous_generated_plan' not in public
            assert public['agent_identity']=={'self':'human','other':'robot'}
            expected={k:planner['active_intention_plan'].get(k) for k in ['decision_kind','long_term_intention','personal_targets','plan']}
            expected.update(source='own_model_generated_intentions_not_world_measurements',generated_at_sim_time_s=planner['time_s'])
            assert public['active_intention_plan']==expected
            assert not {'observed_changes','assumption_corrections'}.intersection(public['active_intention_plan'])
            geometry=public['your_target_geometry'];assert len(geometry)==len(state['personal_targets'])
            for target,g in zip(state['personal_targets'],geometry):
                assert all(g[k]==v for k,v in target.items())
                obj,dest=target['object_id'],target['destination'];relative=dest.startswith('on:')
                point=public['objects_xyz'][dest.split(':',1)[1]] if relative else public['regions_xyz'][dest]
                np.testing.assert_allclose(g['destination_xyz'],point,atol=1e-9)
                np.testing.assert_allclose(g['measured_xy_distance_m'],np.linalg.norm(np.asarray(public['objects_xyz'][obj])[:2]-np.asarray(point)[:2]),atol=1e-9)
                assert g['visible_radius_m']==(.03 if relative else .025) and g['measurement_time_s']==public['time_s']
        else:
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
