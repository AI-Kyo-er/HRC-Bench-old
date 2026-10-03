"""最终开发控制通过后冻结六例；所有响应决定只读公开观察。"""
import argparse
import copy
import json

from experiments.physical.run import ROOT, save, sha, versions, asset_hashes
from experiments.structure_v5.run import keyframe, prefix_digest
from experiments.structure_v8.world_v2 import TransportWorld, CONFIG_PATH, CONFIG
from experiments.structure_v8.controls_v2 import review, offline_contacts
from experiments.structure_v8.protocol import Episode, cases, reference, SYSTEM
from experiments.structure_v8.audit import audit_trace

RESULT=ROOT/'results/structure_v8'
FREEZE=ROOT/'experiments/structure_v8/cases/reference_freeze.json'
SOURCES=['experiments/physical/world.py','experiments/physical/protocol.py','experiments/physical/run.py',
    'experiments/physical_v3_2/world.py','experiments/structure_v5/world.py','experiments/structure_v5/world_v2.py',
    'experiments/structure_v5/world_v3.py','experiments/structure_v5/run.py','experiments/structure_v5/audit.py',
    'experiments/structure_v8/world_v2.py','experiments/structure_v8/controls_v2.py',
    'experiments/structure_v8/protocol.py','experiments/structure_v8/audit.py','experiments/structure_v8/run.py',
    'experiments/structure_v8/transport_config_v1.json']


def source_hashes():
    return {n:sha(ROOT/n) for n in SOURCES}


def freeze():
    if FREEZE.exists(): raise RuntimeError('禁止覆盖冻结。')
    control=json.loads((RESULT/'control_dev2_summary.json').read_text())
    audit=json.loads((RESULT/'control_contact_audit.json').read_text())
    if not control['all_passed'] or control['source_sha256']!={n:sha(ROOT/n) for n in control['source_sha256']}:
        raise RuntimeError('最终控制未通过或源改变。')
    if not all(r['audit']['safety_pass'] and r['audit']['event_history_consistent'] and r['audit']['online_match'] and
               r['audit']['support_coverage']==1 and r['audit']['missing_distance_or_position_pair_records']==0 and
               r['audit']['recomputed_first_delivery_tick'] is not None and r['audit']['same_tick_current_FK_joint_max_y_error_m']<1e-6 and
               r['audit']['all_delivery_facts_match_independent_recomputation'] and r['audit']['goal_first_ticks_match'] for r in audit['dev2']):
        raise RuntimeError('最终真实投递/接触审计未过。')
    save(FREEZE,dict(version='structure-v8-delivery-reference-dev2',cases=cases(),candidate_count=20,system=SYSTEM,
        source_sha256=source_hashes(),config=CONFIG,config_sha256=sha(CONFIG_PATH),packages=versions(),assets_sha256=asset_hashes(),
        control_artifacts_sha256={n:sha(RESULT/n) for n in ('control_dev2_summary.json','control_contact_audit.json')},
        metrics='t0自动运输起点到blue最后释放并停车；red技能与实际运输区间交集含停留/停车；首次交付由支持/相对位姿速度共同满足永久锁存。',
        interpretation='脚本公共约定、机械伙伴代理、规则可行性/真实协调成本机制；不声称组合泛化、新调度理论或人体流畅度。'))
    print('v8冻结',sha(FREEZE),flush=True)


def rollout(case,folder):
    folder.mkdir(parents=True)
    world=TransportWorld(case['seed'],trace_path=folder/'ticks.jsonl.gz')
    rows=[]
    try:
        episode=Episode(case,world)
        rendered=case['seed']==70
        if rendered:keyframe(world,folder/'frames')
        for _ in range(case['step_budget']):
            if episode.success():break
            observation=episode.observation();messages=episode.messages()
            assert json.loads(messages[1]['content'])==json.loads(json.dumps(observation))
            # policy仅选择固定响应/保守算法；响应算法不接收case/condition。
            choice=reference(observation,case['policy'])
            before=world.tick;result=episode.act(choice)
            rows.append(dict(observation=observation,messages=messages,
                prediction=dict(response=json.dumps({'choice':choice}),policy=case['policy']),
                result=result,before_tick=before,after_tick=world.tick))
            print(case['id'],len(rows),choice,result['feedback'],flush=True)
            if rendered:keyframe(world,folder/'frames')
        summary=review(world,episode.initial_state,episode.robot_intervals,episode.executions,episode.cost['wait_ticks'])
        summary.update(case=case,checkpoint=episode.checkpoint,cost=episode.cost,public_final_history=episode.history,
                       protocol_success=episode.success())
        save(folder/'decisions.json',rows)
    finally:
        world.close()
    summary['contact_audit_raw_ticks']=offline_contacts(folder,summary)
    summary['independent_contact_delivery_audit']=audit_trace(folder_with_summary(folder,summary),CONFIG)
    a=summary['independent_contact_delivery_audit']
    summary['prefix_checkpoint_trace_sha256']=prefix_digest(folder/'ticks.jsonl.gz',summary['checkpoint']['tick'])
    summary['passed']=bool(summary['success'] and summary['protocol_success'] and summary['green_preserved'] and
        all(e['success'] for e in summary['executions']) and a['safety_pass'] and a['event_history_consistent'] and
        a['event_persists_after_pickup'] and a['online_match'] and a['support_coverage']==1 and
        a['missing_distance_or_position_pair_records']==0 and a['same_tick_current_FK_joint_max_y_error_m']<1e-6 and
        a['all_delivery_facts_match_independent_recomputation'] and a['goal_first_ticks_match'] and
        summary['non_target_robot_online']['records']==0)
    save(folder/'summary.json',summary)
    return summary


def folder_with_summary(folder,summary):
    # 先归档闭环事实供只读审计，审计不会写任务成功/移动物体。
    save(folder/'summary.json',summary)
    return folder


def run():
    frozen=json.loads(FREEZE.read_text())
    if frozen['source_sha256']!=source_hashes() or frozen['packages']!=versions() or frozen['assets_sha256']!=asset_hashes():
        raise RuntimeError('冻结环境/源不一致。')
    output=RESULT/'raw/reference';output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise RuntimeError('禁止覆盖reference。')
    rows=[rollout(c,output/c['id']) for c in frozen['cases']]
    pairs=[]
    for seed in (70,71):
        same=[r for r in rows if r['case']['seed']==seed]
        by_id={r['case']['id'].rsplit(f'_{seed}',1)[0].removeprefix('A_delivery_'):r for r in same}
        wait=by_id['shared_wait'];overlap=by_id['shared_overlap'];exclusive=by_id['exclusive_response']
        pairs.append(dict(seed=seed,ids=[r['case']['id'] for r in same],
            checkpoint_physical_exact_match=all(r['checkpoint']==same[0]['checkpoint'] for r in same),
            full_physical_prefix_exact_match=len({r['prefix_checkpoint_trace_sha256'] for r in same})==1,
            exclusive_and_shared_wait_full_trajectory_sha_equal=exclusive['independent_contact_delivery_audit']['trace_sha256']==wait['independent_contact_delivery_audit']['trace_sha256'],
            actual_delivery_event_exact_match=all(r['delivery_event']==same[0]['delivery_event'] for r in same),
            shared_wait_makespan_ticks=wait['closed_task_makespan_ticks'],shared_overlap_makespan_ticks=overlap['closed_task_makespan_ticks'],
            shared_wait_wait_ticks=wait['wait_ticks'],shared_overlap_wait_ticks=overlap['wait_ticks'],
            observed_makespan_difference_ticks=wait['closed_task_makespan_ticks']-overlap['closed_task_makespan_ticks'],
            red_skill_transport_overlap_ticks=overlap['red_skill_transport_overlap_ticks'],
            red_controller_same='careful',blue_controller_same='direct',
            makespan_includes_final_robot_parking=True))
    summary=dict(version=frozen['version'],total=len(rows),passed=sum(r['passed'] for r in rows),
        success=sum(r['success'] for r in rows),total_ticks=sum(r['independent_contact_delivery_audit']['total_ticks'] for r in rows),
        robot_carrier_ticks=sum(r['independent_contact_delivery_audit']['groups']['forbidden_robot_carrier']['ticks'] for r in rows),
        other_object_carrier_ticks=sum(r['independent_contact_delivery_audit']['groups']['forbidden_other_object_carrier']['ticks'] for r in rows),
        carrier_static_ticks=sum(r['independent_contact_delivery_audit']['groups']['carrier_static']['ticks'] for r in rows),
        non_target_robot_ticks=sum(r['independent_contact_delivery_audit']['groups']['non_target_robot']['ticks'] for r in rows),
        expected_blue_carrier_records=sum(r['independent_contact_delivery_audit']['groups']['expected_blue_carrier']['records'] for r in rows),
        pairs=pairs,cost={k:sum(r['cost'][k] for r in rows) for k in rows[0]['cost']},
        freeze_sha256=sha(FREEZE),source_sha256=source_hashes(),interpretation=frozen['interpretation'])
    save(output/'summary.json',summary);save(RESULT/'reference_summary.json',summary)
    print('v8六例汇总',json.dumps(summary,ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('freeze','run'));args=parser.parse_args()
    freeze() if args.stage=='freeze' else run()


if __name__=='__main__':main()
