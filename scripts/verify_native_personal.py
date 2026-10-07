#!/usr/bin/env python3
"""重建人自选目标、公开提案、实际私有/公开边界和个人目标物理测量。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

from hrc_pilot.native_autonomous_human import validate_targets
from hrc_pilot.native_personal_evidence import evaluate_personal_goals
from hrc_pilot.protocol import Message
from hrc_pilot.reflective_human_verification import verify_reflective_records


def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def verify_episode(directory, *, require_shelf_release=False, require_table_release=False, allow_relative_relations=False):
    context=read(directory/'personal_context.json');assert context['human_assigned_targets'] is None and context['timed_work_updates']==[]
    trace=rows(directory/'trace.jsonl');control=rows(directory/'human_control.jsonl')
    human=rows(directory/'human_policy_io.jsonl');dialogue=rows(directory/'public_dialogue.jsonl');calls=rows(directory/'model_calls.jsonl')
    reflective=(directory/'human_planner_io.jsonl').exists() and bool(rows(directory/'human_planner_io.jsonl'))
    reflection=verify_reflective_records(rows(directory/'human_planner_io.jsonl'),human) if reflective else None
    targets=[];revision=0;intention=''
    for d in human:
        public=json.loads(d['public_input'].split('\n',1)[1]);state=d['personal_goal_state']
        assert public['task_source']=='no_human_assignment_or_timed_goal_schedule'
        assert public['your_current_assignments']==[]
        if not reflective:assert public['your_previous_personal_targets']==targets
        assert public['personal_context']==context['context']
        if 'preferred_personal_objects' in context:assert public['preferred_personal_object_ids']==context['preferred_personal_objects']
        assert not {'personal_evidence','human_goal_success','task_success'}.intersection(public)
        if d.get('human_policy_architecture')=='deliberative_joint_intention_action':
            assert not reflective and d['thinking_enabled'] and d['neural_calls_for_this_decision']==1
            assert public['human_input_contract']=='joint_intention_action_v1'
            assert public['agent_identity']=={'self':'human','other':'robot'}
            raw=d['raw_model_output']
            assert d['raw_output']==(raw.rsplit('</think>',1)[-1].strip() if '</think>' in raw else '')
            assert public['previous_model_choices']['source']=='own_past_model_choices_not_current_world_facts'
        if reflective:
            targets=state['personal_targets'];revision=state['revision'];intention=state['long_term_intention']
        elif d['parse_error'] is None:
            value=json.loads(d['raw_output'][d['raw_output'].find('{'):d['raw_output'].rfind('}')+1])
            if 'personal_targets' in value:
                expected,error=validate_targets(value['personal_targets'],SimpleNamespace(objects=public['objects_xyz'],regions=public['regions_xyz']),
                    relative_destinations=public['action_interface'].get('relative_placement_destinations',{}) if allow_relative_relations else ())
                assert state['target_validation_error']==error
                if error is None:
                    if sorted(expected,key=lambda t:t['object_id'])!=sorted(targets,key=lambda t:t['object_id']):revision+=1
                    targets=expected
            else:assert state['target_validation_error']=='没有提供personal_targets，保留你先前的意图'
            proposal=value.get('negotiation_proposal');expected_messages=[]
            if isinstance(proposal,dict) and proposal.get('kind') in {'request_space','request_help','offer_help','revise_arrangement'} and isinstance(proposal.get('text'),str):
                message=proposal['text'].strip()[:180]
                if message:expected_messages=[Message('human','negotiation_proposal',f'{proposal["kind"]}: {message}').__dict__]
            assert d['negotiation_proposal_messages']==expected_messages
            text=value.get('long_term_intention')
            if isinstance(text,str) and text.strip():intention=text.strip()[:500]
        assert state['personal_targets']==targets and state['revision']==revision and state['long_term_intention']==intention
    assert all(m['value']=='robot' for m in dialogue if m['kind']=='assignment')
    assert not any(m['kind'] in {'activity_change','reassignment','correction'} for m in dialogue)
    emitted=[m for d in human for m in d['negotiation_proposal_messages']]
    assert emitted==[m for m in dialogue if m['kind']=='negotiation_proposal']
    communicated=[m['text'] for m in dialogue if m['kind'] in {'policy_message','negotiation_proposal'}]
    proposal_uses=0
    coordinated=(directory/'robot_planner_io.jsonl').exists()
    robot_plans=rows(directory/'robot_planner_io.jsonl') if coordinated else []
    plans_by_id={r['decision_id']:r for r in robot_plans}
    if coordinated:
        from hrc_pilot.robot_coordination import PUBLIC_KEYS
        for r in robot_plans:
            request=r['public_input'];assert set(request)==PUBLIC_KEYS-{'images'}
            assert request['robot_task']==context['robot_instruction']
            assert request['human_task']=='Human has private personal preferences; infer their current needs from public speech and visible actions.'
            assert not {'personal_targets','personal_context','preferred_personal_objects','personal_evidence','task_success'}.intersection(request)
            for message in request['dialogue']:
                assert any(all(m.get(k)==v for k,v in message.items()) for m in dialogue)
    for c in calls:
        if not coordinated:assert c['prompt'].startswith(context['robot_instruction'])
        assert c['model_input_keys']==['observation/image','observation/wrist_image','observation/state','prompt']
        if not coordinated:assert c['action_source']=='learned_vla'
        else:
            plan=plans_by_id[c['planner_decision_id']]
            if c['action_source']=='learned_vla':assert c['prompt']==plan['decision']['instruction']
            elif c['action_source']=='vlm_selected_cartesian_primitive':assert plan['decision']['mode']=='move_ee'
            else:assert plan['decision']['mode']=='hold'
        assert '\nCurrent public human work:' not in c['prompt']
        # The only language suffix is publicly emitted speech; private targets are never routed to the robot.
        for text in c['prompt'].split('\nHuman: ')[1:]:assert text in communicated
        proposal_uses+=int(any(m['text'] in c['prompt'] for m in emitted))
    rebuilt=evaluate_personal_goals(context['regions'],trace,control,human,rows(directory/'placement_evidence.jsonl'),require_shelf_release=require_shelf_release,require_table_release=require_table_release,allow_relative_relations=allow_relative_relations)
    assert read(directory/'personal_evidence.json')==rebuilt
    assert read(directory/'metrics.json')['personal_evidence']==rebuilt
    return {'episode':str(directory),'status':'verified','human_calls':len(human),'reflection_verification':reflection,
            'no_external_human_assignments_or_timed_updates':True,'raw_generated_targets_reconstructed':True,
            'private_target_not_routed_to_robot_verified':True,'public_proposal_count':len(emitted),
            'robot_calls_containing_public_proposals':proposal_uses,'personal_geometry_reconstructed':True,
            'interpretation':'核查自选目标、真实动作和公开边界；不证明偏好/主观满足的真实性、因果贡献或协商理解。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args();provenance=read(args.input_dir/'provenance.json')
    assert provenance['human_target_source']=='model_generated_from_personal_preferences'
    assert not provenance['source_files_changed_during_run']
    episodes=[verify_episode(p.parent,require_shelf_release=provenance.get('personal_goal_shelf_release_required',False),require_table_release=provenance.get('personal_goal_table_release_required',False),allow_relative_relations=provenance.get('personal_goal_relative_relations_allowed',False)) for p in sorted(args.input_dir.rglob('personal_context.json'))];assert episodes
    (args.input_dir/'personal_verification.json').write_text(json.dumps({'status':'verified','episodes':episodes},ensure_ascii=False,indent=2))
    print(f'{len(episodes)}条自主目标、公开提案和真实执行边界核查通过')


if __name__=='__main__':main()
