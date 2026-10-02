"""规范输入及实际协调成本复核；独立事后只读代码，不改任务冻结。"""
import gzip
import json
import math

from experiments.physical.run import ROOT,save,sha
from experiments.physical.protocol import candidates
from experiments.structure_v5.run import prefix_digest
from experiments.structure_v8.protocol import SYSTEM
from experiments.structure_v8.run import FREEZE,source_hashes
from experiments.structure_v8.world_v2 import CONFIG
from experiments.structure_v8.audit import audit_trace

RESULT=ROOT/'results/structure_v8'


def regions(state):
    observed={}
    for index,item in enumerate(('red','blue','green')):
        obj=state['objects'][item];position=obj['position'];speed=math.sqrt(sum(v*v for v in obj['velocity']))
        observed[item]=[t for t,y in (('left',-.25),('right',.25)) if
            math.dist(position[:2],[.59+.06*index,y])<.035 and .025<position[2]<.055 and speed<.04]
    return observed


def episode_audit(folder):
    summary=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text())
    needed={r['before_tick'] for r in rows};snapshots={}
    actual_delivery_motion_during_red=0;transport_start_joint=None;red_start_joint=red_end_joint=None
    red=next(i for i in summary['robot_intervals'] if i['item']=='red')
    with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
        for line in stream:
            s=json.loads(line)
            if s['tick'] in needed:snapshots[s['tick']]=s
            if s['tick']==summary['delivery_start_tick']:transport_start_joint=s['partner_joint']
            if s['tick']==red['start']:red_start_joint=s['partner_joint']
            if s['tick']==red['end']:red_end_joint=s['partner_joint']
            if red['start']<s['tick']<=red['end'] and s['tick']<=summary['delivery_event']['first_tick'] and abs(s['partner_velocity'])>1e-6:
                actual_delivery_motion_during_red+=1
    checks=[]
    for index,row in enumerate(rows):
        obs=row['observation'];state=snapshots[row['before_tick']];history=obs['history']
        next_history=rows[index+1]['observation']['history'] if index+1<len(rows) else summary['public_final_history']
        feedback=dict(kind='action_feedback',choice=row['result']['choice'],content=row['result']['feedback'])
        check=dict(decision=index+1,
            raw_messages_exact=row['messages'][0]==dict(role='system',content=SYSTEM) and json.loads(row['messages'][1]['content'])==obs,
            physical_objects_exact=obs['physical']['objects']==state['objects'],
            carrier_current_pose_exact=obs['physical']['carrier_position']==state['partner_position'],
            carrier_current_velocity_exact=obs['physical']['carrier_velocity']==state['partner_velocity'],
            carrier_current_FK_matches_joint=abs(obs['physical']['carrier_position'][1]-state['partner_joint'])<1e-6,
            physical_regions_exact=obs['physical_placements']==regions(state),
            only_public_fields=set(obs)=={'history','physical','physical_placements','delivery_event','delivery_region','remaining_decisions','candidates'},
            full20_menu=obs['candidates']==candidates(),
            delivery_event_not_future=obs['delivery_event']==state['delivery_event'],
            history_prefix_immutable=next_history[:len(history)]==history,
            feedback_once=next_history[len(history):].count(feedback)==1,
            budget_exact=obs['remaining_decisions']==summary['case']['step_budget']-index)
        check['passed']=all(v for k,v in check.items() if k!='decision');checks.append(check)
    contact_delivery=audit_trace(folder,CONFIG)
    t0=summary['delivery_start_tick'];event=summary['delivery_event']
    overlap=max(0,min(red['end'],event['first_tick'])-max(red['start'],t0))
    waits=sum(r['after_tick']-r['before_tick'] for r in rows if r['result']['choice']=='yield')
    # exclusive实际参考没有违例；协议拒绝的证明来自独立事实替身单测。
    agreement=next(e for e in rows[0]['observation']['history'] if e['kind']=='accepted_sequence')
    exclusive_followed=agreement['allow_overlap'] or red['start']>=event['first_tick']
    blue_interval=next(i for i in summary['robot_intervals'] if i['item']=='blue')
    return dict(id=summary['case']['id'],decisions=checks,
        contact_delivery=contact_delivery,actual_transport_moving_ticks_during_red=actual_delivery_motion_during_red,
        red_start_carrier_joint=red_start_joint,red_end_carrier_joint=red_end_joint,transport_start_carrier_joint=transport_start_joint,
        recomputed_wait_ticks=waits,recomputed_red_skill_overlap_ticks=overlap,
        recomputed_closed_makespan_ticks=rows[-1]['after_tick']-t0,
        exclusive_agreement_followed=exclusive_followed,blue_started_after_actual_delivery=blue_interval['start']>=event['first_tick'],
        passed=all(c['passed'] for c in checks) and contact_delivery==summary['independent_contact_delivery_audit'] and
            waits==summary['wait_ticks'] and overlap==summary['red_skill_transport_overlap_ticks'] and
            rows[-1]['after_tick']-t0==summary['closed_task_makespan_ticks'] and exclusive_followed and blue_interval['start']>=event['first_tick'],
        decisions_sha256=sha(folder/'decisions.json'))


def main():
    frozen=json.loads(FREEZE.read_text());assert frozen['source_sha256']==source_hashes()
    rows=[episode_audit(RESULT/'raw/reference'/c['id']) for c in frozen['cases']]
    summary=json.loads((RESULT/'reference_summary.json').read_text())
    canonical_pairs=[]
    for pair in summary['pairs']:
        seed=pair['seed']
        folders=[RESULT/f'raw/reference/A_delivery_{name}_{seed}' for name in ('exclusive_response','shared_wait')]
        digests=[prefix_digest(f/'ticks.jsonl.gz',json.loads((f/'summary.json').read_text())['end_tick']) for f in folders]
        canonical_pairs.append(dict(seed=seed, original_gzip_artifact_sha_equal=pair['exclusive_and_shared_wait_full_trajectory_sha_equal'],
            decompressed_canonical_physical_sha256=digests, full_physical_trajectory_exact_match=digests[0]==digests[1],
            errata='原字段比较压缩artifact SHA，gzip头mtime可不同；物理等同性以解压全tick规范JSON digest为准，原冻结/输出不改。'))
    report=dict(total_episodes=len(rows),total_decisions=sum(len(r['decisions']) for r in rows),
        all_passed=all(r['passed'] for r in rows) and all(p['checkpoint_physical_exact_match'] and p['full_physical_prefix_exact_match'] and
            p['actual_delivery_event_exact_match'] for p in summary['pairs']) and all(p['full_physical_trajectory_exact_match'] for p in canonical_pairs),
        episodes=rows,pairs=summary['pairs'],canonical_physical_trajectory_pairs=canonical_pairs,freeze_sha256=sha(FREEZE),
        auditor_source_sha256=sha(ROOT/'experiments/structure_v8/reference_audit.py'),
        interpretation='物理依赖及协调成本机制核验，两seed实例复现，无模型/结构留出；许可约束与shared并行收益分开。')
    save(RESULT/'input_cost_audit.json',report);assert report['all_passed']
    print('v8独立输入/成本审计',len(rows),report['total_decisions'],report['all_passed'],flush=True)


if __name__=='__main__':main()
