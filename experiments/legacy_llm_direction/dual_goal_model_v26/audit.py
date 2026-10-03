"""独立全tick循环/presence/服务/输入重建；不改评分或重跑物理。"""
import argparse
import copy
import gzip
import hashlib
import json
import math
from experiments.physical.run import ROOT,save,sha
from experiments.dual_goal_model_v26.run import RESULT,FREEZE,hashes
from experiments.dual_goal_v25.protocol import CONFIG,SYSTEM,candidates,WORKSPACE as OLD_WORKSPACE
from experiments.dual_goal_model_v26.inputs import NEW_NOTE,messages,parse_output,public_aid
WORKSPACE=copy.deepcopy(OLD_WORKSPACE);WORKSPACE["notes"]=NEW_NOTE
from experiments.sustained_structure_v21.service import InspectionService
from experiments.sustained_structure_v21.audit import independent_sample,classify,SERVICE_EVENTS
from experiments.structure_foundation_v20.audit_v2 import GROUPS,stable_region,support
from experiments.transport_cycle_v22.cycle import CycleLedger
from experiments.transport_cycle_v22.audit import independent_facts,command
from experiments.transport_cycle_v22.canonical import physics,equal,content_equal


def audit_ledger(history):
    # 独立重新实现公开事务归约，不读case/未来回复/预定F或运行ledger。
    blue=green_rule=None;red=None;pending={};confirmation_pending=True;active=completed=False;progress=0
    for event in history:
        kind=event['kind']
        if kind=='accepted_activity':blue=event['goals']['blue'];red=event['goals']['red'];green_rule=copy.deepcopy(event['green_requirement'])
        elif kind=='confirmation_announced':confirmation_pending=True
        elif kind=='proposal':
            assert event['proposal_id'] not in pending;pending[event['proposal_id']]=event
        elif kind=='proposal_reply':
            proposal=pending.pop(event['proposal_id']);assert event['decision'] in ('accept','reject') and proposal['binding']=='outer_blue'
            if event['decision']=='accept':blue=proposal['destination']
            confirmation_pending=False
        elif kind=='check_request_reply':
            progress=event['qualified_ticks']
            if event['decision']=='accepted':active=True
        elif kind=='partner_check_handoff':active=False;completed=True;progress=event['qualified_ticks']
    green=green_rule['destination'] if green_rule['mode']=='direct' else blue if green_rule['relation']=='same' else ('right' if blue=='left' else 'left')
    return dict(goals=dict(red=red,blue=blue,green=green),green_requirement=green_rule,confirmation_pending=confirmation_pending,pending_proposals=pending,child_active=active,check_completed=completed,check_progress_observed=progress)


def tray_supported(state,item,target,ids):
    return any({c['body_a'],c['body_b']}=={ids['objects'][item],ids['trays'][target]} and c['contact_distance']<=.0001 and c['normal_force']>.001 for c in state['contacts'])


def update_boundary(summary,proposals,replies,service_events):
    if len(proposals)!=1 or len(replies)!=1:return False
    p,r=proposals[0],replies[0];handoffs=[e for e in service_events if e['kind']=='partner_check_handoff']
    tick=summary['common_start_tick'] if summary['case']['timing']=='before_check' else handoffs[0]['actual_tick'] if handoffs else None
    return p['actual_tick']==r['actual_tick']==tick and p['observed_tick']==r['observed_tick'] and p['observed_tick']>=tick and r['event_sequence']==p['event_sequence']+1


def confirmation_trace(summary,proposals,replies,service_events):
    generated=summary['case']['timing']=='before_check' or any(e['kind']=='partner_check_handoff' for e in service_events)
    if not generated:return not proposals and not replies
    return update_boundary(summary,proposals,replies,service_events) and replies[0]['proposal_id']==proposals[0]['proposal_id']


def profile(motion,tick,previous):
    if motion is None:return previous
    travel=abs(motion['target']-motion['origin']);t=max(0,(tick-motion['start_tick'])/240);duration=travel/.08+.5
    if t<.5:d=.08*t*t
    elif t<duration-.5:d=.08*(t-.25)
    elif t<duration:d=travel-.08*(duration-t)**2
    else:d=travel
    return motion['origin']+(1 if motion['target']>motion['origin'] else -1)*d


def episode_audit(folder,tokenizer):
    summary=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text());ids=summary['body_ids']
    events=[];holder=[None];presence_motion=[None];presence_events=[]
    def replay_presence(destination):
        state=holder[0];motion=dict(start_tick=state['tick'],origin=state['presence']['joint'],target=.45 if destination=='near' else 1.05,destination=destination)
        presence_motion[0]=copy.deepcopy(motion);return motion
    clause=next(e['clause'] for e in summary['public_history'] if e['kind']=='accepted_presence_clause')
    service=InspectionService(clause,events.append,replay_presence);cycle=CycleLedger()
    boundaries={t:None for row in rows for t in (row['before_tick'],row['after_tick'])}
    request_rows=[r for r in rows if r['choice'] in ('request_check','request_transport','request_return')];ri=0
    groups={g:dict(records=0,ticks=0,max_normal_force=0,negative_distance_records=0) for g in GROUPS};contact_evidence={};leg_support={}
    request_checks=[];samples_ok=True;events_ok=True;facts_ok=True;presence_ok=True;missing=total=sample_count=0
    command_err=presence_command_err=fk_err=presence_fk_err=0.;prev_command=.6;prev_presence=.45;first_update_queue=None;queue_before_complete=False
    h=hashlib.sha256();refs={};non_target_max=0.;final=None
    def requests_before(tick):
        nonlocal ri
        while ri<len(request_rows) and request_rows[ri]['before_tick']<tick:
            row=request_rows[ri];holder[0]=row['before_state'];before_service=service.snapshot()
            if row['choice']=='request_check':
                response=service.request(independent_sample(row['before_state'],ids));ok=content_equal(response,row['result']['check_reply']) and content_equal(before_service,row['service_before'])
            else:
                response=cycle.request('forward' if row['choice']=='request_transport' else 'return',independent_facts(row['before_state'],ids,cycle));ok=content_equal(response,row['result']['motion_reply'])
            request_checks.append(dict(sequence=row['sequence'],passed=ok));ri+=1
    with gzip.open(folder/'ticks.jsonl.gz','rt') as stream,gzip.open(folder/'service_ticks.jsonl.gz','rt') as ss:
        for line in stream:
            state=json.loads(line);holder[0]=state;total+=1;h.update(json.dumps(physics(state),sort_keys=True,separators=(',',':')).encode())
            if state['tick'] in boundaries:boundaries[state['tick']]=state
            requests_before(state['tick']);holder[0]=state
            leg=cycle.legs[cycle.active-1] if cycle.active is not None else None
            expected=command(leg,state['tick'],prev_command);command_err=max(command_err,abs(expected-state['partner_command']));prev_command=expected
            cf=independent_facts(state,ids,cycle)
            if leg is not None:
                counts=leg_support.setdefault(str(leg['id']),dict(ticks=0,supported_ticks=0,loaded=leg['loaded_at_start']))
                counts['ticks']+=1;counts['supported_ticks']+=int(cf['supported'])
            cycle.sample(cf);events_ok&=content_equal(cycle.snapshot(),state['cycle'])
            actual_facts=independent_facts(state,ids,cycle);stored=state['current_carrier_facts']
            facts_ok&=all(math.isclose(actual_facts[k],stored[k],rel_tol=0,abs_tol=1e-12) if isinstance(actual_facts[k],float) else content_equal(actual_facts[k],stored[k]) for k in actual_facts)
            expected_p=profile(presence_motion[0],state['tick'],prev_presence)
            pf=state['presence']
            if pf is not None:
                presence_command_err=max(presence_command_err,abs(expected_p-pf['target']));prev_presence=expected_p
                presence_fk_err=max(presence_fk_err,abs(pf['position'][1]-pf['joint']))
                for destination,target in (('near',.45),('far',1.05)):
                    presence_ok&=pf[destination]==(abs(pf['joint']-target)<.005 and abs(pf['velocity'])<.005)
                if presence_motion[0] is not None and pf[presence_motion[0]['destination']]:
                    presence_events.append(dict(kind='presence_'+presence_motion[0]['destination'],first_tick=state['tick'],motion=copy.deepcopy(presence_motion[0]),facts=pf))
                    presence_motion[0]=None
                presence_ok&=content_equal(presence_motion[0],state['presence_motion']) and content_equal(presence_events,state['presence_events'])
            fk_err=max(fk_err,abs(state['partner_position'][1]-state['partner_joint']))
            found=classify(state,ids);missing+=sum(any(k not in c for k in ('contact_distance','position_a','position_b')) for c in state['contacts'])
            for g,contacts in found.items():
                group=groups[g];group['records']+=len(contacts);group['ticks']+=int(bool(contacts))
                for c in contacts:
                    group['negative_distance_records']+=int(c['contact_distance']<-1e-6)
                    if g.startswith('forbidden'):
                        evidence=contact_evidence.setdefault(g,{})
                        if 'first' not in evidence:evidence['first']=dict(tick=state['tick'],contact=c,state=state)
                        if c['normal_force']>group['max_normal_force']:evidence['peak']=dict(tick=state['tick'],contact=c,state=state)
                    group['max_normal_force']=max(group['max_normal_force'],c['normal_force'])
            if state['tick']>summary['common_start_tick']:
                actual=independent_sample(state,ids);recorded=json.loads(next(ss));rebuilt=service.step(actual);sample_count+=1
                queued=[e for e in recorded['events_so_far'] if e['kind'] in ('proposal','proposal_reply')]
                if queued and first_update_queue is None:first_update_queue=dict(tick=state['tick'],events=queued)
                if queued and not rebuilt['service']['completed']:queue_before_complete=True
                samples_ok&=content_equal(recorded['facts'],actual) and recorded['sample_qualified']==rebuilt['sample_qualified'] and content_equal(recorded['service'],rebuilt['service'])
                for item in ids['objects']:
                    autonomous=item=='blue' and leg is not None and leg['loaded_at_start']
                    if item==state['robot_target_item'] or autonomous:refs.pop(item,None)
                    else:
                        refs.setdefault(item,state['objects'][item]['position']);non_target_max=max(non_target_max,math.dist(refs[item],state['objects'][item]['position']))
            final=state
        try:next(ss);exhausted=False
        except StopIteration:exhausted=True
    requests_before(summary['end_tick']+1)
    history=summary['public_history'];recorded_service=[{k:v for k,v in e.items() if k not in ('event_sequence','observed_tick')} for e in history if e['kind'] in SERVICE_EVENTS]
    recorded_cycle=[e['event'] for e in history if e['kind']=='physical_cycle_event']
    input_checks=[];previous_history=None;placements=[]
    for row in rows:
        obs=row['observation'];before=row['before_state'];after=row['after_state'];physical_obs=obs['physical']
        check=dict(before_physics=equal(before,boundaries[row['before_tick']]),after_physics=equal(after,boundaries[row['after_tick']]),
            messages_exact=row['messages']==messages(obs,summary['view']),
            history_prefix_immutable=previous_history is None or obs['history']==previous_history or (summary['stage']=='local' and obs['history'][:-1]==previous_history and obs['history'][-1]['kind']=='local_measurement_start'),menu_same12=obs['candidates']==candidates(),workspace=obs['workspace']==WORKSPACE,
            budget=obs['remaining_decisions']==row['decision_budget']-(row['sequence']-row['budget_origin']),objects_exact=content_equal(physical_obs['objects'],before['objects']),
            current_carrier_exact=content_equal(physical_obs['carrier'],before['current_carrier_facts']),presence_exact=content_equal(physical_obs['presence'],before['presence']),
            current_motion_exact=content_equal(obs['motion'],{k:before['cycle'][k] for k in ('active','legs','events')}),
            no_private_goal_or_score=not any(k in obs for k in ('score','case','current_goals','child_active','future_schedule')),
            no_future_events=all(e['actual_tick']<=e['observed_tick']<=row['before_tick'] for e in obs['history']),event_sequence=all(e['event_sequence']==i for i,e in enumerate(obs['history'])))
        previous_history=row['history_after'];input_checks.append(dict(sequence=row['sequence'],checks=check,passed=all(check.values())))
        if row['result'].get('execution',{}).get('physical_attempt'):
            result=row['result']['execution'];choice=row['choice'];item='red' if choice.startswith('careful_red') else 'green' if choice.startswith('careful_green') else 'blue';target='carrier' if choice=='reload_blue' else choice.split('_')[-1]
            cf=independent_facts(after,ids,cycle)
            if target=='carrier':actual=cf['near'] and cf['payload_stable']
            elif target=='inspection':actual=independent_sample(after,ids)['inspection']['satisfied']
            else:actual=stable_region(after,item,target) and tray_supported(after,item,target,ids)
            placements.append(dict(sequence=row['sequence'],choice=choice,claimed_success=result['success'],actual=bool(actual),finger_contacts=result.get('finger_contacts',0),lifted_z=result.get('lifted_z'),passed=bool(actual and result['success'] and result.get('finger_contacts',0)>0 and result.get('lifted_z',0)>.12)))
    ledger=audit_ledger(history);cf=independent_facts(final,ids,cycle)
    actual_score=dict(facts=dict(confirmation_closed=not ledger['confirmation_pending'] and not ledger['pending_proposals'],check_completed=service.completed,no_active_child=not ledger['child_active'],
        red_left=stable_region(final,'red','left'),blue_current_goal=stable_region(final,'blue',ledger['goals']['blue']),green_current_goal=stable_region(final,'green',ledger['goals']['green']),carrier_current_far=cf['far'] and cycle.active is None))
    actual_score['task_success']=all(actual_score['facts'].values()) and summary['termination_reason']=='declared_done'
    safe=all(v['records']==0 for k,v in groups.items() if k.startswith('forbidden'))
    proposals=[e for e in history if e['kind']=='proposal'];replies=[e for e in history if e['kind']=='proposal_reply'];accepts=[e for e in history if e['kind']=='check_request_reply' and e['decision']=='accepted']
    queue_ok=first_update_queue is None
    if summary['case']['timing']=='after_handoff' and proposals:
        clean=[{k:v for k,v in e.items() if k not in ('event_sequence','observed_tick')} for e in history if e['kind'] in ('proposal','proposal_reply')]
        queue_ok=first_update_queue is not None and first_update_queue['tick']==proposals[0]['actual_tick'] and content_equal(first_update_queue['events'],clean) and not queue_before_complete
    checks=dict(runtime_source_unchanged=json.loads(FREEZE.read_text())['source_sha256']==hashes(),no_infrastructure_failure=not (folder/'infrastructure_failure.json').exists(),
        all_inputs=all(r['passed'] for r in input_checks),successful_grasp_places_verified=all(r['passed'] for r in placements if r['claimed_success']),requests_exact=all(r['passed'] for r in request_checks) and ri==len(request_rows),
        cycle_recomputed=events_ok and content_equal(cycle.snapshot(),summary['final_state']['cycle']),current_facts_recomputed=facts_ok,cycle_public_events=recorded_cycle==cycle.events,
        service_samples=samples_ok,service_trace_count=sample_count==summary['end_tick']-summary['common_start_tick'] and exhausted,service_events=content_equal(recorded_service,events),service_final=content_equal(service.snapshot(),summary['service']),
        presence_recomputed=presence_ok,presence_same_tick_FK=presence_fk_err<1e-6,carrier_same_tick_FK=fk_err<1e-6,presence_profile=presence_command_err<1e-12,carrier_profile=command_err<1e-12,
        confirmation_generation_exact=confirmation_trace(summary,proposals,replies,events),actual_queue_generation=queue_ok,start_and_during_updates=all(audit_ledger(r['observation']['history'])==r['known_at_start'] and r['actual_updates_during_skill']==[e for e in history if e['kind'] in ('proposal','proposal_reply') and r['before_tick']<e['actual_tick']<=r['after_tick']] for r in rows),
        task_score_exact=actual_score==summary['score'],after_terminal_immutable=summary['after_terminal_immutable'],
        full_canonical=dict(sha256=h.hexdigest(),ticks=total)==summary['canonical_physics'],final_physics_exact=equal(final,summary['final_state']),contact_fields_complete=missing==0,
        all_forbidden_zero=safe,loaded_support_all=all(v['ticks']==v['supported_ticks'] for v in leg_support.values() if v['loaded']),non_target_preserved=non_target_max<.01)
    name=summary['case'].get('control')
    if name:
        old=summary['checkpoints']['old_green'];after_update=summary['checkpoints']['after_update'];before_ledger=audit_ledger(old['history']);new_ledger=audit_ledger(after_update['history'])
        checks['green_legal_before_update']=stable_region(old['state'],'green',before_ledger['goals']['green']) and tray_supported(old['state'],'green',before_ledger['goals']['green'],ids) and before_ledger['confirmation_pending']
        invalidated=not stable_region(after_update['state'],'green',new_ledger['goals']['green'])
        checks['old_goal_invalidation_exact']=invalidated==(name in ('U1','U4'))
        green_places=[p for p in placements if p['choice'].startswith('careful_green')]
        checks['green_rework_or_preservation']=len(green_places)==(2 if name=='U1' else 1)
        if name=='U4':checks['isolated_green_failure']=not actual_score['facts']['green_current_goal'] and all(v for k,v in actual_score['facts'].items() if k!='green_current_goal')
    if summary['stage']=='local':
        cut=summary['checkpoints']['local_start'];n=cut['row_boundary'];pc=cut['cost'];lc={k:summary['cost'][k]-pc[k] for k in pc}
        checks['local_real_prefix']=equal(cut['state'],boundaries[cut['state']['tick']]) and cut['service']['completed'] and cut['state']['current_carrier_facts']['far'] and cut['state']['cycle']['active'] is None
        checks['local_budget_cost_separate']=pc['decisions']==n and lc==summary['local_cost'] and rows[n]['budget_origin']==n and rows[n]['decision_budget']==12 and all(r['phase']=='prefix' for r in rows[:n]) and all(r['phase']=='model' for r in rows[n:])
        checks['local_messages_exact']=rows[n]['messages']==cut['messages']
    neural=neural_checks(summary,rows,tokenizer)
    checks['neural_inputs_outputs_costs']=all(neural['checks'].values())
    return dict(neural=neural,id=summary['record_id'],case=summary['case'],record=summary['record'],stage=summary['stage'],view=summary['view'],passed=all(checks.values()),physically_safe=safe,task_success=actual_score['task_success'],actual_score=actual_score,checks=checks,
        total_ticks=total,makespan_ticks=summary['makespan_ticks'],cost=summary['cost'],qualified_ticks=service.qualified_ticks,service=service.snapshot(),
        public_goals=ledger['goals'],confirmation_pending=ledger['confirmation_pending'],events=cycle.events,service_events=events,presence_events=presence_events,leg_support=leg_support,groups=groups,contact_evidence=contact_evidence,
        max_non_target_interval_displacement_m=non_target_max,input_checks=input_checks,placements=placements,request_checks=request_checks,
        profile_errors=dict(carrier=command_err,presence=presence_command_err),same_tick_FK=dict(carrier=fk_err,presence=presence_fk_err))



def independent_aid(o):
    l=audit_ledger(o['history']);done={i:g in o['physical_placements'][i] for i,g in l['goals'].items()}
    accepted=next(e for e in o['history'] if e['kind']=='accepted_activity')
    bindings=[{k:e[k] for k in ('kind','proposal_id','binding','destination','decision') if k in e} for e in o['history'] if e['kind'] in ('proposal','proposal_reply')]
    return dict(source='仅从同一公开已发生history与当前实际physical_placements、motion归约；额外账本计算帮助，不提供未来、评分或下一动作。',
        current_goals_from_public_history=l['goals'],green_requirement=l['green_requirement'],proposal_reply_binding=bindings,
        confirmation_pending=l['confirmation_pending'],pending_proposals=l['pending_proposals'],
        scope=dict(active=l['child_active'],check_completed=l['check_completed'],qualified_ticks_last_public=l['check_progress_observed']),
        done_under_current_goals=done,remaining_items=[i for i in l['goals'] if not done[i]],
        obligations=dict(inspection_required=accepted['inspection_required'],carrier_return_required=accepted['carrier_return_required'],current_carrier_far=o['physical']['carrier']['far'],motion_active=o['motion']['active']))


def neural_checks(summary,rows,tokenizer):
    model_rows=[r for r in rows if r['phase']=='model'];items=[];record=summary['record'];cost={k:0 for k in summary['cost']}
    for row in rows:
        choice=row['choice'];result=row['result'];cost['decisions']+=1;cost['invalid']+=int(not result['valid']);cost['no_ops']+=int(result['no_op'])
        if choice=='request_transport':cost['requests_transport']+=1
        elif choice=='request_return':cost['requests_return']+=1
        elif choice=='request_check':cost['requests_check']+=1
        elif choice=='yield':cost['yields']+=1;cost['wait_ticks']+=result['wait_ticks']
        elif choice=='declare_done':cost['declarations']+=1
        elif choice=='reload_blue':cost['reloads']+=1
        ex=result.get('execution',{});cost['physical_attempts']+=int(ex.get('physical_attempt',False));cost['physical_failures']+=int(ex.get('physical_attempt',False) and not ex['success'])
        if row['phase']!='model':continue
        p=row['prediction'];d=len(items);ids=tokenizer.apply_chat_template(row['messages'],tokenize=True,add_generation_prompt=True,enable_thinking=True)
        generated=p['generated_ids'];decoded=tokenizer.decode(generated,skip_special_tokens=True);positions=[i for i,t in enumerate(generated) if t==151668]
        official_final=tokenizer.decode(generated[positions[-1]+1:],skip_special_tokens=True).strip() if positions else None
        parsed=parse_output(decoded);u=json.loads(row['messages'][1]['content']);aid=u.pop('external_public_ledger_aid',None)
        checks=dict(input_ids_exact=p['input_ids']==ids,input_budget=len(ids)<=24576,response_exact=decoded==p['response'],
            raw_special_decode=p['response_with_special_tokens']==tokenizer.decode(generated,skip_special_tokens=False),seed=p['seed']==record['seed_base']+d,
            parse=all(p[k]==v for k,v in parsed.items()),official_last_boundary=p['final_response']==official_final,
            choice=row['choice']==p['choice'],marker_count=p['think_end_marker_count']==len(positions),counts=p['input_tokens']==len(ids) and p['output_tokens']==len(generated),
            no_probe_parameters=p['capacity_only'] is False,base_observation_exact=u==row['observation'],
            aid_exact=(aid is None if summary['view']=='full_history' else aid==independent_aid(row['observation'])),
            no_future=all(e['actual_tick']<=e['observed_tick']<=row['before_tick'] for e in u['history']),
            parse_failure_consumed=not p['parse_error'] or (not result['valid'] and row['before_tick']==row['after_tick']))
        items.append(dict(sequence=row['sequence'],model_index=d,choice=row['choice'],parse_error=p['parse_error'],checks=checks,passed=all(checks.values())))
    # 容量失败没有新生成或物理动作，不能伪造成解析失败耗步。
    capacity_path=RESULT/'raw/episodes'/summary['record_id']/'input_capacity_failure.json';capacity_ok=True
    if summary['termination_reason']=='input_capacity_failure':
        c=json.loads(capacity_path.read_text());capacity_ok=len(tokenizer.apply_chat_template(c['messages'],tokenize=True,add_generation_prompt=True,enable_thinking=True))>24576 and c['decision']==len(model_rows)
    checks=dict(all_predictions=all(x['passed'] for x in items),call_count=len(items)==summary['model_calls'],cost_exact=cost==summary['cost'],
        parse_counts=sum(x['parse_error'] is not None for x in items)==summary['parse_failures'],capacity_failure_exact=capacity_ok,
        first_model_input_exact=not model_rows or model_rows[0]['messages']==record['initial_messages'])
    return dict(checks=checks,calls=items,cost_recomputed=cost)


def audit():
    from transformers import AutoTokenizer
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes();tokenizer=AutoTokenizer.from_pretrained(f['model_spec']['path'],local_files_only=True)
    out=RESULT/'raw/audit_sources';out.mkdir(parents=True,exist_ok=True);(out/'audit.py').write_bytes((ROOT/'experiments/dual_goal_model_v26/audit.py').read_bytes())
    reports=[]
    for record in f['episodes']:
        folder=RESULT/'raw/episodes'/record['id'];r=episode_audit(folder,tokenizer);reports.append(r)
        print(r['id'],r['passed'],r['task_success'],r['physically_safe'],[k for k,v in r['checks'].items() if not v],flush=True)
    result=dict(total=len(reports),passed=sum(r['passed'] for r in reports),task_success=sum(r['task_success'] for r in reports),physically_safe=sum(r['physically_safe'] for r in reports),
        total_ticks=sum(r['total_ticks'] for r in reports),episodes=reports,freeze_sha256=sha(FREEZE),audit_source_sha256=sha(ROOT/'experiments/dual_goal_model_v26/audit.py'),
        scope='审计重建正确、技能/接触/非目标约束与任务成功分列；任务失败不自动等于审计错误，真实禁止接触仍令严格检查失败。')
    save(RESULT/'model_audit.json',result);print('全量审计完成',result['passed'],result['total'],flush=True)


if __name__=='__main__':audit()
