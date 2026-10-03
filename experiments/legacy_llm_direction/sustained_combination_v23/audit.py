"""独立全tick循环/presence/服务/输入重建；不改评分或重跑物理。"""
import argparse
import copy
import gzip
import hashlib
import json
import math
from experiments.physical.run import ROOT,save,sha
from experiments.sustained_combination_v23.run import RESULT,freeze_path,hashes
from experiments.sustained_combination_v23.protocol import CONFIG,SYSTEM,candidates,WORKSPACE,public_ledger
from experiments.sustained_structure_v21.service import InspectionService
from experiments.sustained_structure_v21.audit import independent_sample,classify,SERVICE_EVENTS
from experiments.structure_foundation_v20.audit_v2 import GROUPS,stable_region,support
from experiments.transport_cycle_v22.cycle import CycleLedger
from experiments.transport_cycle_v22.audit import independent_facts,command
from experiments.transport_cycle_v22.canonical import physics,equal,content_equal


def profile(motion,tick,previous):
    if motion is None:return previous
    travel=abs(motion['target']-motion['origin']);t=max(0,(tick-motion['start_tick'])/240);duration=travel/.08+.5
    if t<.5:d=.08*t*t
    elif t<duration-.5:d=.08*(t-.25)
    elif t<duration:d=travel-.08*(duration-t)**2
    else:d=travel
    return motion['origin']+(1 if motion['target']>motion['origin'] else -1)*d


def episode_audit(folder):
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
    command_err=presence_command_err=fk_err=presence_fk_err=0.;prev_command=.6;prev_presence=.45
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
            messages_exact=row['messages']==[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(obs,ensure_ascii=False))],
            history_prefix_immutable=previous_history is None or obs['history']==previous_history,menu_same12=obs['candidates']==candidates(),workspace=obs['workspace']==WORKSPACE,
            budget=obs['remaining_decisions']==48-row['sequence'],objects_exact=content_equal(physical_obs['objects'],before['objects']),
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
            else:actual=stable_region(after,item,target)
            placements.append(dict(sequence=row['sequence'],choice=choice,actual=bool(actual),finger_contacts=result.get('finger_contacts',0),lifted_z=result.get('lifted_z'),passed=bool(actual and result['success'] and result.get('finger_contacts',0)>0 and result.get('lifted_z',0)>.12)))
    ledger=public_ledger(history);cf=independent_facts(final,ids,cycle);latest=cycle.legs[-1] if cycle.legs else None
    partner=bool(latest and latest['direction']=='return' and latest['payload_event'] is not None and cf['far'] and cf['payload_stable'])
    actual_score=dict(facts=dict(check_completed=service.completed,no_active_child=not ledger['child_active'],red_left=stable_region(final,'red','left'),green_right=stable_region(final,'green','right'),
        carrier_current_far=cf['far'] and cycle.active is None,blue_role_completed=partner if ledger['blue_role']=='partner_return' else stable_region(final,'blue',ledger['goals']['blue'])))
    actual_score['task_success']=all(actual_score['facts'].values()) and summary['termination_reason']=='declared_done'
    safe=all(v['records']==0 for k,v in groups.items() if k.startswith('forbidden'))
    proposals=[e for e in history if e['kind']=='proposal'];replies=[e for e in history if e['kind']=='proposal_reply'];accepts=[e for e in history if e['kind']=='check_request_reply' and e['decision']=='accepted']
    checks=dict(runtime_source_unchanged=json.loads(freeze_path('control' if 'control' in summary['case'] else 'reference').read_text())['source_sha256']==hashes(),no_infrastructure_failure=summary['failure'] is None,
        all_inputs=all(r['passed'] for r in input_checks),all_actual_grasp_places=all(r['passed'] for r in placements),requests_exact=all(r['passed'] for r in request_checks) and ri==len(request_rows),
        cycle_recomputed=events_ok and content_equal(cycle.snapshot(),final['cycle']),current_facts_recomputed=facts_ok,cycle_public_events=recorded_cycle==cycle.events,
        service_samples=samples_ok,service_trace_count=sample_count==summary['end_tick']-summary['common_start_tick'] and exhausted,service_events=content_equal(recorded_service,events),service_final=content_equal(service.snapshot(),summary['service']),
        presence_recomputed=presence_ok,presence_same_tick_FK=presence_fk_err<1e-6,carrier_same_tick_FK=fk_err<1e-6,presence_profile=presence_command_err<1e-12,carrier_profile=command_err<1e-12,
        proposal_once_after_check=len(proposals)==len(replies)==1 and bool(accepts) and proposals[0]['event_sequence']>accepts[0]['event_sequence'] and replies[0]['proposal_id']==proposals[0]['proposal_id'],
        task_score_exact=actual_score==summary['score'],expected_task=actual_score['task_success']==summary['expected_task_success'],after_terminal_immutable=summary['after_terminal_immutable'],
        full_canonical=dict(sha256=h.hexdigest(),ticks=total)==summary['canonical_physics'],final_physics_exact=equal(final,summary['final_state']),contact_fields_complete=missing==0,
        all_forbidden_zero=safe,loaded_support_all=all(v['ticks']==v['supported_ticks'] for v in leg_support.values() if v['loaded']),non_target_preserved=non_target_max<.01)
    name=summary['case'].get('control')
    if name=='C0':
        facts=actual_score['facts'];checks['isolated_unfinished_check']=not facts['check_completed'] and service.qualified_ticks==60 and all(facts[k] for k in ('red_left','green_right','carrier_current_far','blue_role_completed'))
        checks['actual_far_before_reload']=summary['checkpoints']['far_before_reload']['state']['presence']['far'] and summary['checkpoints']['far_before_reload']['service']['qualified_ticks']==60
    elif name=='C1':
        facts=actual_score['facts'];checks['isolated_missing_return']=facts['check_completed'] and facts['no_active_child'] and facts['red_left'] and facts['green_right'] and not facts['carrier_current_far'] and not facts['blue_role_completed']
    elif name in ('R2','R3'):
        checks['actual_early_return_before_check']=summary['checkpoints']['early_return']['state']['current_carrier_facts']['far'] and summary['checkpoints']['early_return']['state']['current_carrier_facts']['payload_stable'] and summary['checkpoints']['early_return']['service']['acceptances']==0
        checks['actual_second_forward_recovered']=summary['checkpoints']['recovered_forward']['current_carrier_facts']['near'] and summary['checkpoints']['recovered_forward']['current_carrier_facts']['payload_stable'] and len(cycle.legs)==4
    return dict(id=summary['case']['id'],case=summary['case'],passed=all(checks.values()),physically_safe=safe,task_success=actual_score['task_success'],actual_score=actual_score,checks=checks,
        total_ticks=total,makespan_ticks=summary['makespan_ticks'],cost=summary['cost'],qualified_ticks=service.qualified_ticks,service=service.snapshot(),
        public_role=ledger['blue_role'],events=cycle.events,service_events=events,presence_events=presence_events,leg_support=leg_support,groups=groups,contact_evidence=contact_evidence,
        max_non_target_interval_displacement_m=non_target_max,input_checks=input_checks,placements=placements,request_checks=request_checks,
        profile_errors=dict(carrier=command_err,presence=presence_command_err),same_tick_FK=dict(carrier=fk_err,presence=presence_fk_err))


def audit(stage):
    f=json.loads(freeze_path(stage).read_text());assert f['source_sha256']==hashes();reports=[]
    for case in f['cases']:
        report=episode_audit(RESULT/'raw'/'dev0'/stage/case['id']);reports.append(report);print(report['id'],report['passed'],report['task_success'],[k for k,v in report['checks'].items() if not v],flush=True)
    result=dict(stage=stage,total=len(reports),passed=sum(r['passed'] for r in reports),task_success=sum(r['task_success'] for r in reports),physically_safe=sum(r['physically_safe'] for r in reports),total_ticks=sum(r['total_ticks'] for r in reports),
        episodes=reports,freeze_sha256=sha(freeze_path(stage)),runtime_source_sha256=hashes(),audit_source_sha256=sha(ROOT/'experiments/sustained_combination_v23/audit.py'))
    save(RESULT/f'{stage}_audit_dev0.json',result);assert result['passed']==len(reports);print('独立审计通过',stage,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('control','reference'));audit(p.parse_args().stage)
