#!/usr/bin/env python3
"""独立核对公开渠道、实际命令、连续人动作和真实机器人动作；不冒充语义效度。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from hrc_pilot.joint_activity import ACTIVITIES
from hrc_pilot.joint_human_policy import parse_choice


def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def read(p):return json.loads(p.read_text())


def audit(root):
    ep=root/'episode';p=read(root/'provenance.json');activity=ACTIVITIES[p['activity']]
    from hrc_pilot.bounded_human_runtime import protocol_enabled,failure_aware_tool_payload,failure_aware_agenda_request
    bounded_protocol=protocol_enabled(p)
    fixture_contract=p.get('human_fixture_surface_contract')
    if fixture_contract is not None:
        from hrc_pilot.fixture_area_human_executor import CONTRACT as FIXTURE_CONTRACT
        if fixture_contract!=FIXTURE_CONTRACT:raise ValueError('未知家具面执行协议')
    if p.get('interaction_contract'):
        from hrc_pilot.interaction_contracts import CONTRACTS
        activity=CONTRACTS[p['activity']].activity
    if p.get('workspace_method'):
        from hrc_pilot.workspace_contracts import WORKSPACE_CONTRACTS
        CONTRACTS=WORKSPACE_CONTRACTS;activity=CONTRACTS[p['activity']].activity
    saved_task=read(ep/'task.json');saved_activity=saved_task['public_activity']
    assert not p['source_files_changed_during_run']
    assert p['human_executor']=='human_only_continuous_kinematic_attachment'
    trace=rows(ep/'trace.jsonl');human=rows(ep/'human_policy_io.jsonl');controls=rows(ep/'robot_control.jsonl')
    calls=rows(ep/'model_calls.jsonl');dialogue=rows(ep/'public_dialogue.jsonl');receipts=rows(ep/'human_command_receipts.jsonl')
    planner_path=ep/'robot_planner_io.jsonl'
    plans=rows(planner_path) if planner_path.exists() else []
    assert bool(plans)==(p['robot_system'] in {'visual_coordinator_plus_vla','symbolic_coordinator_plus_vla'})
    raw_human=rows(ep/'human_control.jsonl')
    tool_tokenizer=None
    if any(d.get('choice_schema_version') in {6,7,8,9,10} for d in human):
        from transformers import AutoTokenizer
        tool_tokenizer=AutoTokenizer.from_pretrained(p['human_model'],local_files_only=True,trust_remote_code=True)
    support_sim=None
    support_replay_errors=[]
    geometry_frames=[]
    if p.get('human_support_targets')=='actual_collision_geometry_cabinet_top_v1':
        from robosuite.utils.binding_utils import MjSim
        support_sim=MjSim.from_xml_file(str((ep/'scene.xml').resolve()))
    context_path=ep/'private_context.jsonl';contexts=rows(context_path) if context_path.exists() else []
    if p.get('human_decision_cadence')=='observation_events_and_periodic_reconsideration':
        from hrc_pilot.human_decision_schedule import HumanDecisionSchedule
        schedule=HumanDecisionSchedule(min_interval_s=p['human_decision_steps']/20,
            max_silence_s=max(20.,p['human_decision_steps']/20))
        checks=rows(ep/'human_schedule_checks.jsonl');selected=[]
        assert [c['step'] for c in checks]==list(range(0,p['steps'],p['human_decision_steps']))
        for check in checks:
            assert check['time_s']==check['step']/20
            visible=dialogue[:check['dialogue_count_before_human']]
            private=contexts[:check['private_context_count']]
            expected=schedule.check(trace[check['step']],visible,private)
            assert all(check[key]==value for key,value in expected.items())
            if expected['call_neural_policy']:selected.append(check['time_s'])
        assert selected==[row['time_s'] for row in human]
    expected_context=p.get('human_source','neural')=='neural' and 0<=p['context_step']<p['steps']
    if p.get('situation'):
        situation=read(ep/'situation.json')
        expected_context=any(c['time_s']<p['steps']/20 for c in situation['private_cues'])
    assert bool(contexts)==expected_context
    language_records=[]
    if p['robot_model_metadata'].get('language_token_limit'):
        import sentencepiece as spm
        from safetensors.numpy import load_file
        tokenizer=spm.SentencePieceProcessor(model_file='/data1/sieniwgroup/sieniw/models/Physical-Intelligence/openpi-cache/big_vision/paligemma_tokenizer.model')
        stats=load_file(str(Path(p['robot_model_metadata']['checkpoint'])/'policy_preprocessor_step_2_normalizer_processor.safetensors'))
    assert len(trace)==len(controls)+1 and len(human)==len(receipts)
    np.testing.assert_allclose([r['physics_time_s']-trace[0]['physics_time_s'] for r in trace],
                               np.arange(len(trace))/20,atol=1e-7)
    for human_index,(d,receipt) in enumerate(zip(human,receipts)):
        assert d['decision_id']==receipt['request_id'] and d['choice']==receipt['choice']
        source=d['private_input'];scene=d.get('observation_source_scene',source['scene']);actual=trace[round(d['time_s']*20)]
        if p.get('human_contribution_observations'):
            from hrc_pilot.contribution_observations import contribution_observations
            expected_contributions={str(previous['decision_id']):contribution_observations(previous,scene)
                                    for previous in human[:human_index][-4:]}
            assert scene['self_contribution_observations']==expected_contributions
        else:
            assert 'self_contribution_observations' not in scene
        if 'private_agenda_inference' in d:
            from hrc_pilot.private_agenda_human import agenda_request,parse_agenda,AGENDA_SCHEMA,AGENDA_SYSTEM
            inference=d['private_agenda_inference']
            previous=(human[human_index-1]['private_agenda_inference']['agenda_after'] if human_index else None)
            assert inference['agenda_before']==previous
            expected=agenda_request(scene,activity,p['profile'],previous,human[:human_index])
            if bounded_protocol:expected=failure_aware_agenda_request(expected,human[:human_index])
            assert inference['request']==expected
            payload_agenda={'messages':[{'role':'system','content':AGENDA_SYSTEM},
                {'role':'user','content':json.dumps(expected,ensure_ascii=False,separators=(',',':'))}]}
            assert inference['model_input']==payload_agenda and inference['output_schema']==AGENDA_SCHEMA
            assert inference['decoder']=='lm-format-enforcer-0.11.3' and not inference['generation_thinking']
            encoded_agenda=tool_tokenizer.apply_chat_template(payload_agenda['messages'],tokenize=True,
                add_generation_prompt=True,enable_thinking=False)
            assert encoded_agenda==inference['input_token_ids']
            assert tool_tokenizer.decode(inference['generated_token_ids'],skip_special_tokens=True).strip()==inference['raw_output']
            assert inference['chat_template_sha256']==sha256(tool_tokenizer.chat_template.encode()).hexdigest()
            if inference['parse_error'] is None:assert inference['agenda_after']==parse_agenda(inference['raw_output'])
            else:
                try:parse_agenda(inference['raw_output'])
                except (ValueError,TypeError):pass
                else:raise AssertionError('意图错误标签与原始输出不符')
                assert inference['agenda_after']==previous
            assert source['self_generated_private_agenda']==inference['agenda_after']
            assert source['private_agenda_status']==('generated_interpretation_not_world_fact' if inference['parse_error'] is None
                else 'agenda_generation_invalid_previous_interpretation_retained')
            assert d['neural_inferences']==2
        if d.get('human_observation_encoding') in {'intent_semantic_facts_v1','intent_semantic_available_targets_v2','intent_semantic_agent_dialogue_v3'}:
            from hrc_pilot.intent_observation import intent_observation
            expected_scene=intent_observation(scene)
            if d['human_observation_encoding'] in {'intent_semantic_available_targets_v2','intent_semantic_agent_dialogue_v3'}:
                from hrc_pilot.human_decision_interface import available_destinations
                expected_scene['named_destinations']=list(available_destinations(scene))
            if d['human_observation_encoding']=='intent_semantic_agent_dialogue_v3':
                expected_scene['public_partner_statements_not_execution_facts']=[m for m in scene['public_dialogue'] if m['speaker'] in {'human','robot'}]
            assert source['scene']==expected_scene
        if d.get('human_contribution_contract')=='explicit_parameter_domains_v1':
            from hrc_pilot.human_contribution_contract import contribution_interface
            assert source['human_contribution_interface']==contribution_interface(scene)
            if d['reflection_enabled']:
                assert d['reflection_input']['human_contribution_interface']==contribution_interface(scene)
        if d.get('choice_schema_version') in {6,7,8,9,10}:
            from hrc_pilot.tool_joint_human import tool_model_input,retained_private_notes
            assert source['own_retained_private_notes']==retained_private_notes(human[:human_index])
            payload=tool_model_input(d['system_prompt'],source,human[:human_index],scene)
            if bounded_protocol:payload=failure_aware_tool_payload(payload,human[:human_index])
            if d['choice_schema_version']==7:
                from hrc_pilot.structured_tool_joint_human import structured_speech_payload
                payload=structured_speech_payload(payload)
                assert source['human_measured_object_contacts']==scene['measured_world'].get('object_contacts',{})
            if d['choice_schema_version'] in {8,9,10}:
                from hrc_pilot.human_decision_interface import decision_tool,decision_interface
                payload['tools']=[decision_tool(scene)]
                interface=decision_interface(scene)
                if d['choice_schema_version'] in {9,10}:
                    from hrc_pilot.constrained_human_decision import constrained_tool,constrained_interface,decision_json_schema
                    payload['tools']=[constrained_tool(scene)];interface=constrained_interface(scene)
                    expected_schema=decision_json_schema(scene)
                    if bounded_protocol:
                        from hrc_pilot.bounded_human_protocol import bounded_output_schema
                        payload['tools'][0]['function']['parameters']=bounded_output_schema(payload['tools'][0]['function']['parameters'])
                        expected_schema=bounded_output_schema(expected_schema)
                    assert d['output_json_schema']==expected_schema
                    assert d['raw_output']==d['caller_prefix']+d['actual_generated_json']+d['caller_suffix']
                    assert tool_tokenizer.decode(d['actual_generated_token_ids'],skip_special_tokens=True).strip()==d['actual_generated_json']
                    from hrc_pilot.human_output_verification import verify_recorded_constrained_output
                    verify_recorded_constrained_output(d,scene)
                    if d['choice_schema_version']==10:
                        whole=d['whole_generated_token_ids'];close=tool_tokenizer.encode('</think>',add_special_tokens=False)[0]
                        index=whole.index(close);prefix=tool_tokenizer.encode(d['caller_prefix'],add_special_tokens=False)
                        assert whole[:index]==d['reasoning_token_ids']
                        assert whole[index+1:index+1+len(prefix)]==prefix
                        assert whole[index+1+len(prefix):]==d['actual_generated_token_ids']
                        assert tool_tokenizer.decode(whole,skip_special_tokens=False)==d['actual_raw_generated_text']
                        assert tool_tokenizer.decode(d['reasoning_token_ids'],skip_special_tokens=False)==d['reasoning_text']
                        if d['reasoning_close_forced']:assert len(d['reasoning_token_ids'])==d['reasoning_token_limit']
                assert source['human_decision_interface']==interface
                assert 'human_contribution_interface' not in source
                assert source['human_measured_object_contacts']==scene['measured_world'].get('object_contacts',{})
                from hrc_pilot.human_support_targets import cabinet_placement_targets
                from hrc_pilot.geometry_frame_replay import replay_recorded_geometry
                frame=replay_recorded_geometry(support_sim.model._model,support_sim.data._data,actual)
                geometry_frames.append({'time_s':d['time_s'],**frame})
                if p.get('workspace_method'):
                    from hrc_pilot.activity_workspace import body_target_on_surface
                    layout=read(root/'workspace_layout.json');surfaces=layout['zone_surface_positions']
                    assert scene['table_surface_positions']==surfaces
                    assert all(scene['regions_xyz'][name]==point for name,point in surfaces.items())
                    if p.get('human_area_placement'):
                        from hrc_pilot.placement_areas import table_placement_areas,area_placement
                        areas=table_placement_areas(layout)
                        if fixture_contract:
                            from hrc_pilot.fixture_area_human_executor import fixture_placement_areas
                            assert layout.get('fixture_surface_contract')==fixture_contract
                            areas.update(fixture_placement_areas(support_sim.model,support_sim.data,
                                list(scene['objects_xyz']),scene['regions_xyz']))
                        else:
                            assert layout.get('fixture_surface_contract') is None
                        assert layout['placement_areas']==areas==scene['public_placement_areas']
                    else:
                        assert 'public_placement_areas' not in scene
                    table=receipt.get('table_surface_placement')
                    if table:
                        assert receipt['accepted'] and table['destination']==d['choice']['destination']
                        if 'area_placement' in receipt:
                            allocation=receipt['area_placement'];dest=table['destination']
                            assert p.get('human_area_placement') and dest in areas
                            plan_index=round((allocation['planning_physics_time_s']-trace[0]['physics_time_s'])*20)
                            assert 0<=plan_index<=round(d['time_s']*20)
                            planned=trace[plan_index]
                            from hrc_pilot.libero_native import perceived_object_contacts
                            for payload_name in allocation['payload_names']:
                                contact=perceived_object_contacts(planned)[payload_name]
                                assert not contact['robot_hand_contact']
                                assert (table['object_id'] in contact['contact_entities'] or
                                    (planned['human_execution']['held_object']==table['object_id'] and
                                     payload_name in planned['human_execution']['carried_objects']))
                            replay_recorded_geometry(support_sim.model._model,support_sim.data._data,planned)
                            resolved=area_placement(support_sim.model,support_sim.data,table['object_id'],
                                areas[dest],list(planned['objects']),payload_names=allocation['payload_names'],
                                preferred_xy=allocation['preferred_xy'])
                            np.testing.assert_allclose(allocation['body_target_xyz'],resolved['body_target_xyz'],atol=.0002,rtol=0)
                            replay_recorded_geometry(support_sim.model._model,support_sim.data._data,actual)
                            expected=body_target_on_surface(support_sim.model,support_sim.data,table['object_id'],
                                [*allocation['body_target_xyz'][:2],areas[dest]['surface_z_m']])
                        else:
                            expected=body_target_on_surface(support_sim.model,support_sim.data,table['object_id'],
                                surfaces[table['destination']])
                        np.testing.assert_allclose(table['resolved_object_body_xyz'],expected,atol=.0002,rtol=0)
                        assert table['surface_xyz']==surfaces[table['destination']]
                names=[n for n in ['wine_bottle_1','cream_cheese_1','akita_black_bowl_1','plate_1'] if n in scene['objects_xyz']]
                expected_targets=cabinet_placement_targets(support_sim.model,support_sim.data,names)
                if p.get('human_relation_targets')=='measured_reference_collision_surface_v1':
                    from hrc_pilot.human_relation_targets import relation_placement_targets
                    relations=relation_placement_targets(support_sim.model,support_sim.data,list(scene['objects_xyz']))
                    assert set(relations)==set(scene['relation_targets'])
                    for name,relation in relations.items():
                        saved=scene['relation_targets'][name]
                        for key in ['object_id','relation','reference_object_id','support_collision_geom','source']:
                            assert relation[key]==saved[key]
                        np.testing.assert_allclose(relation['target_xyz'],saved['target_xyz'],atol=.0002,rtol=0)
                        expected_targets[name]=relation['target_xyz']
                for name,point in expected_targets.items():
                    delta=float(np.max(np.abs(np.asarray(point)-scene['regions_xyz'][name])))
                    support_replay_errors.append({'time_s':d['time_s'],'target':name,'max_axis_error_m':delta})
                    # 独立对齐实际缓存几何；目标容差保持原值，不为失败样本放宽。
                    np.testing.assert_allclose(point,scene['regions_xyz'][name],atol=.0002,rtol=0)
            if d.get('human_history_encoding')=='current_full_scene_and_compact_factual_experience_v1':
                from hrc_pilot.private_agenda_human import compact_action_history
                payload=compact_action_history(payload)
            assert payload==d['native_tool_model_input']
            assert d['chat_template_sha256']==sha256(tool_tokenizer.chat_template.encode()).hexdigest()
            encoded=tool_tokenizer.apply_chat_template(payload['messages'],tools=payload['tools'],
                tokenize=True,add_generation_prompt=True,enable_thinking=d.get('generation_thinking',True))
            if d['choice_schema_version'] in {9,10}:encoded+=tool_tokenizer.encode(d.get('caller_input_prefix',d['caller_prefix']),add_special_tokens=False)
            assert encoded==d['native_tool_input_token_ids']
        if p.get('human_source','neural')=='neural':
            assert source['activity']==saved_activity
            assert 'private_background' not in source['activity']
        assert not {'task_success','score','future_context'}.intersection(scene)
        if receipt.get('automatic_buffer'):
            buffer=receipt['automatic_buffer']
            assert p.get('human_auto_buffer') and receipt['accepted']
            assert d['choice']['action']=='relocate'
            assert buffer['owned_object']==actual['human_execution']['held_object']
            assert buffer['owned_object']!=d['choice']['object_id']
            assert buffer['public_region']==buffer['owned_object']+'_personal'
            assert buffer['public_region'] in scene['regions_xyz']
        for obj,xyz in scene['objects_xyz'].items():np.testing.assert_allclose(xyz,actual['objects'][obj])
        np.testing.assert_allclose(scene['robot_eef_xyz'],actual['robot_ee'])
        if 'measured_world' in scene:
            from hrc_pilot.joint_world import observable_world
            version=scene['measured_world'].get('measurement_version',1)
            if p.get('human_carried_observation'):
                assert version==5 and p['world_measurement_version']==5
                from hrc_pilot.carried_world_observation import observable_carried_world
                expected_world=observable_carried_world(actual,scene['regions_xyz'],scene['measured_world']['drawer'])
            else:
                assert version!=5
                expected_world=observable_world(actual,scene['regions_xyz'],scene['measured_world']['drawer'],
                                               measurement_version=version)
            assert set(scene['measured_world']).issubset(expected_world)
            assert all(scene['measured_world'][k]==expected_world[k] for k in scene['measured_world'])
        assert all(m in dialogue and m['time_s']<=d['time_s'] for m in scene['public_dialogue'])
        assert all(c in contexts and c['time_s']<=d['time_s'] for c in scene['private_context'])
        if d['parse_error'] is None and p.get('human_source','neural')=='neural':
            if d.get('choice_schema_version') in {6,7,8,9,10}:
                if d['choice_schema_version'] in {9,10}:
                    from hrc_pilot.constrained_human_decision import parse_constrained_decision
                    choice,normalization,call=parse_constrained_decision(d['raw_output'],scene)
                elif d['choice_schema_version']==8:
                    from hrc_pilot.human_decision_interface import parse_decision
                    choice,normalization,call=parse_decision(d['raw_output'],scene)
                else:
                    if d['choice_schema_version']==7:
                        from hrc_pilot.structured_tool_joint_human import parse_structured_tool_choice as parse_tool
                    else:
                        from hrc_pilot.tool_joint_human import parse_tool_choice as parse_tool
                    choice,normalization,call=parse_tool(d['raw_output'],scene['objects_xyz'],scene['regions_xyz'])
                assert choice==d['choice'] and normalization==d['contribution_normalization'] and call==d['selected_tool_call']
            elif d.get('choice_schema_version') in {4,5}:
                from hrc_pilot.human_contribution_contract import parse_contribution
                choice,normalization=parse_contribution(d['raw_output'],scene['objects_xyz'],scene['regions_xyz'],
                                                        schema_version=d['choice_schema_version'])
                assert choice==d['choice'] and normalization==d['contribution_normalization']
            elif d.get('choice_schema_version')==3:
                from hrc_pilot.semantic_joint_human import parse_semantic_choice
                assert parse_semantic_choice(d['raw_output'],scene['objects_xyz'],scene['regions_xyz'])==d['choice']
            else:
                assert parse_choice(d['raw_output'],scene['objects_xyz'],scene['regions_xyz'],
                                    schema_version=d.get('choice_schema_version',1))==d['choice']
            if d.get('reflection_enabled'):
                assert d['neural_inferences']==2 and d['reflection_input']['scene']==source['scene']
                assert d['reflection_input']['candidate_choice_to_review']==d['candidate_raw_output']
    emitted=[(d['time_s'],d['choice']['message'],d['decision_id']) for d in human if d['choice'].get('message')]
    assert emitted==[(m['time_s'],m['text'],m['human_decision_id']) for m in dialogue if m['speaker']=='human']
    for plan in plans:
        request=plan['public_input']
        assert not {'private_context','personal_background','own_memory','private_intention','score'}.intersection(request)
        expected_task=(saved_task['native_robot_task']+'\nShared activity: '+saved_activity['public_description']
                       if p.get('robot_language')=='native_with_activity' else saved_activity['public_description'])
        if p.get('interaction_contract'):
            expected_task=json.dumps(CONTRACTS[p['activity']].public(),ensure_ascii=False)
        assert request['robot_task']==expected_task
        if p['robot_system']=='symbolic_coordinator_plus_vla':
            assert request['available_vla_operation']==('' if p.get('interaction_contract') else saved_task['native_robot_task'])
            actual=trace[round(plan['time_s']*20)]
            for name,xyz in request['observed_world']['objects_xyz'].items():
                np.testing.assert_allclose(xyz,actual['objects'][name])
            assert 'private_context' not in request['observed_world']
            assert 'human_intention' not in request['observed_world']
            if p.get('human_area_placement'):
                assert request['observed_world']['public_placement_areas']==read(root/'workspace_layout.json')['placement_areas']
        if p['robot_system']=='visual_coordinator_plus_vla':
            current=next(c for c in calls if c['step']==round(plan['time_s']*20))
            assert plan['image_sha256']=={'initial':calls[0]['exterior_rgb_sha256'],
                'current':current['exterior_rgb_sha256'],'wrist':current['wrist_rgb_sha256']}
            np.testing.assert_allclose(request['state'],current['state'])
            if p.get('coordinator_metadata',{}).get('policy')=='neural_visual_native_skill_coordination':
                from hrc_pilot.native_skill_coordinator import native_operation,encode_selected_operation
                operation=native_operation(request['robot_task'])
                assert request['available_vla_operation']==operation==saved_task['native_robot_task']
                decision,error,adapter=encode_selected_operation(plan['raw_output'],operation)
                assert decision==plan['decision'] and error==plan['parse_error']
                assert adapter['generated_instruction']==plan['generated_instruction']
                assert adapter['model_selected_operation']==plan['model_selected_operation']
        if p.get('robot_skill_bank'):
            from hrc_pilot.robot_skill_bank import SKILLS,encode_skill_selection
            operations=dict(SKILLS)
            if p.get('robot_withdraw_operation'):
                from hrc_pilot.robot_skill_bank import WITHDRAW_OPERATION
                operations.update(WITHDRAW_OPERATION)
            assert request['available_vla_operations']==operations
            decision,error,adapter=encode_skill_selection(plan['raw_output'],request['available_vla_operations'])
            assert decision==plan['decision'] and error==plan['parse_error']
            assert adapter['model_selected_skill_id']==plan['model_selected_skill_id']
            assert adapter['generated_instruction']==plan['generated_instruction']
        assert all(any(m['speaker']==message['speaker'] and m['kind']==message['kind'] and m['text']==message['text']
                       and m['time_s']<=plan['time_s'] for m in dialogue) for message in request['dialogue'])
    received=0
    for c in calls:
        visible=dialogue[:c['visible_dialogue_count']]
        assert all(m['time_s']<=c['time_s'] for m in visible)
        if p.get('reference_vla_instruction'):
            assert p['human_source']=='reference'
            assert c['action_source']=='actual_vla_reference_instruction'
            assert c['prompt']==p['reference_vla_instruction']
        elif p['robot_system']=='direct_vla_public_dialogue':
            # 依据保存的设置兼容旧开发记录，不能倒改旧输入。
            recent=([m for m in visible if m['speaker'] in {'human','robot'}][-2:]
                    if p['robot_model_metadata'].get('language_token_limit') else visible[-12:])
            spoken='\n'.join(f'{m["speaker"]}: {m["text"]}' for m in recent)
            task=read(ep/'task.json')
            base=(task['native_robot_task']+'\nShared activity: '+saved_activity['public_description']
                  if p.get('robot_language')=='native_with_activity' else saved_activity['public_description'])
            expected=(task['native_robot_task'] if p.get('robot_language')=='task_only' else
                      base+'\nActual public conversation:\n'+spoken)
            assert c['prompt']==expected
            received+=sum(m['speaker']=='human' for m in visible[-12:])
        if c['action_source']=='actual_vla_coordinator_instruction':
            assert c['prompt']==plans[c['coordinator_decision_id']]['decision']['instruction']
        if 'language_input_evidence' in c:
            evidence=c['language_input_evidence']
            assert not evidence['truncated'] and evidence['token_count']<=evidence['token_limit']
            assert sum(evidence['token_mask'])==evidence['token_count']
            state=np.asarray(c['state'],dtype=np.float32)
            normalized=(state-stats['observation.state.mean'])/(stats['observation.state.std']+1e-8)
            discretized=np.digitize(normalized,bins=np.linspace(-1,1,257)[:-1])-1
            clean=c['prompt'].strip().replace('_',' ').replace('\n',' ')
            full=f'Task: {clean}, State: '+ ' '.join(map(str,discretized))+';\nAction: '
            expected_ids=tokenizer.encode(full,add_bos=True)
            actual_ids=np.asarray(evidence['token_ids'])[np.asarray(evidence['token_mask'],dtype=bool)].tolist()
            assert actual_ids==expected_ids
            assert evidence['decoded_actual_input']==tokenizer.decode(expected_ids)
            language_records.append({'time_s':c['time_s'],'token_count':len(actual_ids),'truncated':False})
        np.testing.assert_allclose(np.load(ep/f'observation_{c["step"]:06d}_state.npy'),c['state'])
        from PIL import Image
        for suffix,field in [('', 'exterior_rgb_sha256'),('_wrist','wrist_rgb_sha256')]:
            pixels=np.asarray(Image.open(ep/f'observation_{c["step"]:06d}{suffix}.png').convert('RGB'))
            assert sha256(pixels.tobytes()).hexdigest()==c[field]
        actions=np.load(ep/f'observation_{c["step"]:06d}_actions.npy')
        np.testing.assert_allclose(actions,np.asarray(c['raw_action_chunk'])[:c['executed_action_count']])
    for control,actual,next_actual in zip(controls,trace,trace[1:]):
        c=calls[control['model_call_id']]
        chunk_index=control['step']-c['step']
        np.testing.assert_allclose(control['action'],c['raw_action_chunk'][chunk_index])
        np.testing.assert_allclose([control['pre_physics_time_s'],control['post_physics_time_s']],
                                  [actual['physics_time_s'],next_actual['physics_time_s']],atol=1e-7)
        assert control['source']==c['action_source']
    velocities=np.asarray([r['hand_velocity'] for r in raw_human])
    speed=float(np.linalg.norm(velocities,axis=1).max())
    assert speed<=.200001 and all(r['robot_pose_writes']==0 for r in raw_human)
    assert all(r['human_attached_object_pose_write'] is None or r['human_attached_object_pose_write']==r['held_object'] for r in raw_human)
    times=np.asarray([r['physics_time_s'] for r in raw_human]);positions=np.asarray([r['hand_xyz'] for r in raw_human])
    assert np.all(np.diff(times)>0)
    sampled=float((np.linalg.norm(np.diff(positions,axis=0),axis=1)/np.diff(times)).max())
    assert sampled<=.200001
    from hrc_pilot.fixture_receipt_verification import verify_fixture_receipts
    fixture_receipt_checks=verify_fixture_receipts(p,trace,human,receipts,support_sim,saved_task['regions'])
    robot_received_human_calls=sum('human:' in c['prompt'] for c in calls)
    review=[{'time_s':d['time_s'],'private_intention':d['choice'].get('intention'),
             'public_message':d['choice'].get('message'),'actual_action':d['choice']['action'],
             'policy_generation_parse_error':d.get('parse_error'),
             'action_is_generation_failure_fallback':d.get('parse_error') is not None,
             'execution_accepted':receipts[i]['accepted'],'execution_error':receipts[i]['error']}
            for i,d in enumerate(human)]
    human_neural_calls=(sum(d.get('neural_inferences',1) for d in human)
                        if p.get('human_source','neural')=='neural' else 0)
    result={'status':'verified','world_initializations':1,'human_neural_calls':human_neural_calls,
        'human_decision_rows':len(human),'human_source':p.get('human_source','neural'),
        'human_policy_parse_error_count':sum(d.get('parse_error') is not None for d in human),
        'verified_schema_generation_failure_count':sum(d.get('parse_error') is not None
            and d.get('choice_schema_version') in {9,10} for d in human),
        'robot_action_blocks':len(calls),'actual_robot_control_steps':len(controls),
        'robot_actual_vla_calls':sum(c['action_source'] in {'actual_vla_public_dialogue','actual_vla_coordinator_instruction','actual_vla_reference_instruction'} for c in calls),
        'robot_visual_coordinator_calls':len(plans),
        'robot_coordinator_calls_with_public_human_speech':sum(any(m['speaker']=='human' for m in r['public_input']['dialogue']) for r in plans),
        'robot_actual_vla_calls_with_human_speech':sum(c['action_source'] in {'actual_vla_public_dialogue','actual_vla_coordinator_instruction'}
            and 'human:' in c.get('language_input_evidence',{}).get('decoded_actual_input',c['prompt']) for c in calls),
        'robot_calls_with_actual_human_speech':robot_received_human_calls,
        'human_calls_with_actual_robot_measurement':len(human),'human_peak_reference_speed_m_s':speed,
        'human_peak_sampled_kinematic_speed_m_s':sampled,'human_executor_rejection_count':sum(not r['accepted'] for r in receipts),
        'human_attached_object_pose_write_samples':sum(r['human_attached_object_pose_write'] is not None for r in raw_human),
        'private_context_notifications':contexts,'behavior_review':review,
        'interpretation':'验证实际观测、公开渠道和执行一致；不证明真人策略、共同任务完成、语义变化或cobalance。'}
    if fixture_contract:
        result['fixture_surface_receipt_verification']={'contract':fixture_contract,'receipts':fixture_receipt_checks,
            'scope':'实际接受点或拒绝按原规划帧重放；不认证意图、路径、安全或任务成功。'}
    if support_replay_errors:
        result['support_geometry_replay']={'tolerance_m':.0002,
            'max_axis_error_m':max(r['max_axis_error_m'] for r in support_replay_errors),
            'samples':support_replay_errors,
            'recorded_geometry_frames':geometry_frames,
            'scope':'先按独立物体位置重建缓存或已forward的物理帧，再核对柜顶几何；目标容差未放宽，不等于任务完成。'}
    if any('private_agenda_inference' in row for row in human):
        assert all('private_agenda_inference' in row for row in human)
        assert p['private_agenda_shared_with_robot'] is False
        assert p['human_neural_inferences_per_decision']==2
        result['human_private_agenda_calls']=len(human)
        result['human_private_agenda_parse_errors']=sum(row['private_agenda_inference']['parse_error'] is not None for row in human)
        result['private_agenda_interpretation']='两次真实生成的token与输入已核对；私人需要不经后台变成正确动作，不认证人物拟真。'
    write_path=root/'interaction_verification.json';write_path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    if p['robot_model_metadata'].get('language_token_limit'):
        (root/'language_observation_verification.json').write_text(json.dumps({
            'status':'verified' if language_records else 'not_applicable_no_vla_inference',
            'max_tokens':p['robot_model_metadata']['language_token_limit'],'truncated_calls':0,
            'actual_vla_language_receipts':len(language_records),'calls':language_records,
            'interpretation':'用真实checkpoint归一化和tokenizer独立重建并逐token核对服务端实际输入；无VLA调用的原语块不计输入证明。'},ensure_ascii=False,indent=2))
    return {k:v for k,v in result.items() if k not in {'behavior_review','private_context_notifications'}}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    print(json.dumps(audit(parser.parse_args().input_dir),ensure_ascii=False))
