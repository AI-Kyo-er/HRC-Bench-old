"""冻结后独立复核：左右区域/目标首满足从真实trace重算，不用legacy左字段。"""
import copy
import gzip
import json
import math
import tempfile
from pathlib import Path
from experiments.physical.run import ROOT,save,sha
from experiments.transport_goal_v17.run import RESULT,FREEZE,hashes
from experiments.responsive_transport_v16.world import CONFIG
from experiments.responsive_transport_v16.canonical import trace_digest,physics_equal
from experiments.structure_v8.audit import audit_trace


def actual_regions(objects,item):
    obj=objects[item];p=obj['position'];speed=math.sqrt(sum(v*v for v in obj['velocity']));x=.59+.06*('red','blue','green').index(item)
    return [t for t,y in (('left',-.25),('right',.25)) if math.dist(p[:2],[x,y])<.035 and .025<p[2]<.055 and speed<.04]


def strip_declared_goal(observation):
    o=copy.deepcopy(observation)
    for event in o['history']:
        if event['kind']=='accepted_goals':event['goals']['blue']='DECLARATION_ONLY'
    return o


def availability_for_input(summary,snapshot,tick):
    return (summary['initial_state'] if tick==summary['common_start_tick'] else snapshot)['availability']


def audit():
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes()
    rows=[];sources={n:sha(ROOT/n) for n in ('experiments/transport_goal_v17/audit.py','experiments/responsive_transport_v16/canonical.py','experiments/structure_v8/audit.py')}
    for case in f['cases']:
        folder=RESULT/'raw/controls'/case['id'];s=json.loads((folder/'summary.json').read_text());decisions=json.loads((folder/'decisions.json').read_text())
        # 旧接触复核仅在临时派生summary中传left诊断字段；绝不改原summary。
        with tempfile.TemporaryDirectory(dir=RESULT/'raw') as name:
            tmp=Path(name);save(tmp/'summary.json',dict(s,goal_first_ticks=s['legacy_left_only_goal_first_ticks']));(tmp/'ticks.jsonl.gz').symlink_to((folder/'ticks.jsonl.gz').resolve())
            contact=audit_trace(tmp,CONFIG)
        checkpoints={d['before_tick']:None for d in decisions};generic_first={};first_command=None;first_declared=None;last=None;count=0
        with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
            for line in stream:
                state=json.loads(line);count+=1;last=state
                if state['tick'] in checkpoints:checkpoints[state['tick']]=state
                regions={i:actual_regions(state['objects'],i) for i in ('red','blue','green')}
                for i in ('red','blue'):
                    for t in regions[i]:generic_first.setdefault(i+'_'+t,state['tick'])
                if 'left' in regions['red'] and case['command_blue'] in regions['blue'] and first_command is None:first_command=state['tick']
                if 'left' in regions['red'] and case['declared_blue'] in regions['blue'] and first_declared is None:first_declared=state['tick']
        messages_match=True;physical_match=True;history_prefix=True;previous=[]
        for d in decisions:
            obs=d['observation'];messages_match &= d['messages'][0]['content']==f['system'] and json.loads(d['messages'][1]['content'])==obs
            snap=checkpoints[d['before_tick']];physical_match &= obs['physical']['objects']==snap['objects']
            physical_match &= obs['physical_placements']=={i:actual_regions(snap['objects'],i) for i in ('red','blue','green')}
            physical_match &= obs['physical']['carrier_joint']==snap['partner_joint'] and obs['physical']['carrier_position']==snap['partner_position']
            # 初始化最后simulate记录发生在common_start_tick赋值之前；同tick初始快照保存构造完成后的注解。
            physical_match &= obs['partner_availability']==availability_for_input(s,snap,d['before_tick'])
            history_prefix &= obs['history'][:len(previous)]==previous and all(e['observed_tick']<=d['before_tick'] for e in obs['history'])
            previous=obs['history']
        regions={i:actual_regions(last['objects'],i) for i in ('red','blue','green')}
        physically_satisfied='left' in regions['red'] and case['command_blue'] in regions['blue'];goal_compliant='left' in regions['red'] and case['declared_blue'] in regions['blue']
        blue=decisions[-1];feedback=blue['result']['feedback'];selected_only=str(regions['blue']) in feedback and '约定' not in feedback
        checks=dict(source_unchanged=True,four_commands_exhausted=len(decisions)==4 and s['cost']['decisions']==4,all_valid=all(d['result']['valid'] for d in decisions),
            actual_two_skills_success=s['cost']['physical_attempts']==2 and s['cost']['physical_failures']==0 and all(e['success'] for e in s['executions']),
            physical_command_success=physically_satisfied and physically_satisfied==s['physical_command_success'],goal_compliance_recomputed=goal_compliant==s['declared_goal_compliant']==(case['declared_blue']==case['command_blue']),
            selected_actual_region_feedback_only=selected_only,all_messages_exact_observation=messages_match,physical_inputs_match_same_tick=physical_match,immutable_history_prefix_no_future=history_prefix,
            contacts_match_original=contact==s['contact_delivery_audit'],four_forbidden_contacts_zero=all(contact['groups'][g]['records']==0 for g in ('forbidden_robot_carrier','forbidden_other_object_carrier','carrier_static','non_target_robot')),
            support_all=contact['support_coverage']==1,delivery_independent=contact['all_delivery_facts_match_independent_recomputation'] and contact['event_history_consistent'] and contact['event_persists_after_pickup'],
            green_preserved=contact['max_green_displacement_m']<.01,canonical_full_matches=trace_digest(folder/'ticks.jsonl.gz')==s['canonical_full_trace'],last_physical_matches_saved=physics_equal(last,s['final_state']))
        rows.append(dict(id=case['id'],case=case,checks=checks,passed=all(checks.values()),contact=contact,actual_final_regions=regions,declared_goal_compliant=goal_compliant,
            initial_annotation_source='common_start_tick赋值前最后trace注解与构造后initial_state区分；对象/载台物理仍逐tick精确比对。',
            generic_first_region_ticks=generic_first,first_command_joint_satisfaction_tick=first_command,first_declared_joint_satisfaction_tick=first_declared,
            legacy_left_only_ticks_unused_for_general_scoring=s['legacy_left_only_goal_first_ticks'],decisions_sha256=sha(folder/'decisions.json')))
        print(case['id'],rows[-1]['passed'],[k for k,v in checks.items() if not v],flush=True)
    pairs=[]
    for seed in (90,91):
        for command in ('left','right'):
            for mode in ('direct','careful'):
                pair=[r for r in rows if r['case']['seed']==seed and r['case']['command_blue']==command and r['case']['mode']==mode]
                folders=[RESULT/'raw/controls'/r['id'] for r in pair];ss=[json.loads((p/'summary.json').read_text()) for p in folders];dd=[json.loads((p/'decisions.json').read_text()) for p in folders]
                comparisons=dict(initial_physical=physics_equal(ss[0]['initial_state'],ss[1]['initial_state']),whole_trace=trace_digest(folders[0]/'ticks.jsonl.gz')==trace_digest(folders[1]/'ticks.jsonl.gz'),
                    public_observation_except_initial_declared_goal=all(strip_declared_goal(a['observation'])==strip_declared_goal(b['observation']) for a,b in zip(*dd)),
                    feedback=all(a['result']['feedback']==b['result']['feedback'] for a,b in zip(*dd)),opposite_goal_compliance=pair[0]['declared_goal_compliant']!=pair[1]['declared_goal_compliant'])
                pairs.append(dict(seed=seed,command=command,mode=mode,comparisons=comparisons,passed=all(comparisons.values())))
    report=dict(total=16,passed=sum(r['passed'] for r in rows),pairs=pairs,physical_command_success=16,declared_goal_compliant=sum(r['declared_goal_compliant'] for r in rows),total_ticks=sum(r['contact']['total_ticks'] for r in rows),
        audit_source_sha256=sources,freeze_sha256=sha(FREEZE),episodes=rows,goal_oracle_retained='result.success及评分仍按声明目标判断；本轮指定控制绝不读它提前结束。仅解除blue错误目标过滤，其余语义前提保留。')
    save(RESULT/'control_audit.json',report);assert report['passed']==16 and report['declared_goal_compliant']==8 and all(p['passed'] for p in pairs)
    print('独立审计通过',report['total_ticks'],flush=True)

if __name__=='__main__':audit()
