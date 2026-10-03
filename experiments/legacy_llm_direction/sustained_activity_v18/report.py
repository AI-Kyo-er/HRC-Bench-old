"""独立派生成本与执行回执；不改运行源/评分，不产生新动作。"""
import datetime
import json
import os
import subprocess
from pathlib import Path
from experiments.physical.run import ROOT,save,sha
from experiments.sustained_activity_v18.run import RESULT,freeze_path,hashes


def report():
    stages={stage:json.loads((RESULT/f'{stage}_audit.json').read_text()) for stage in ('recovery','negative','reference')}
    costs=[]
    for r in stages['reference']['episodes']:
        s=json.loads((RESULT/'raw/reference'/r['id']/'summary.json').read_text());red=next(i for i in s['robot_intervals'] if i['item']=='red');delivery=s['delivery_event']['first_tick'];start=s['delivery_start_tick']
        costs.append(dict(id=r['id'],case=r['case'],decisions=s['cost']['decisions'],makespan_ticks=s['closed_activity_makespan_ticks'],makespan_seconds=s['closed_activity_makespan_seconds'],
            first_joint_physical_satisfaction_tick=r['actual_joint_goal_first_tick'],first_satisfaction_from_t0_ticks=r['actual_joint_goal_first_tick']-s['common_start_tick'],
            delivery_actual_first_tick=delivery,delivery_start_tick=start,delivery_from_t0_ticks=delivery-s['common_start_tick'],red_transport_overlap_ticks=max(0,min(red['end'],delivery)-max(red['start'],start)),
            red_overlap_includes_skill_dwell_and_parking=True,wait_ready_ticks=s['cost']['wait_ready_ticks'],wait_delivery_ticks=s['cost']['wait_delivery_ticks'],
            availability_actual_and_observed_events=s['availability_events'],requests=s['cost']['requests'],accepted_requests=s['cost']['accepted_requests'],rejected_requests=s['cost']['rejected_requests'],
            duplicate_requests=s['cost']['duplicate_requests'],yields=s['cost']['yields'],declarations=s['cost']['declarations'],physical_attempts=s['cost']['physical_attempts'],physical_failures=s['cost']['physical_failures']))
    total_contacts={g:sum(e['contacts']['groups'][g]['records'] for a in stages.values() for e in a['episodes']) for g in ('expected_blue_carrier','forbidden_robot_carrier','forbidden_other_object_carrier','carrier_static','non_target_robot')}
    summary=dict(total_episodes=56,total_ticks=sum(a['total_ticks'] for a in stages.values()),stage_counts={k:dict(total=a['total'],passed=a['passed'],goal_compliant=a['goal_compliant'],total_ticks=a['total_ticks']) for k,a in stages.items()},
        contacts_records=total_contacts,reference_costs=costs,reference_totals={k:sum(r[k] for r in costs) for k in ('decisions','requests','accepted_requests','rejected_requests','duplicate_requests','yields','declarations','physical_attempts','physical_failures')},
        support_coverage_started=min(e['contacts']['support_coverage'] for a in stages.values() for e in a['episodes'] if e['contacts']['transport_ticks']),
        max_green_displacement_m=max(e['contacts']['max_green_displacement_m'] for a in stages.values() for e in a['episodes']),
        all_current_sources_match_freezes=all(json.loads(freeze_path(stage).read_text())['source_sha256']==hashes() for stage in stages),
        report_source_sha256=sha(ROOT/'experiments/sustained_activity_v18/report.py'),
        interpretation='52符合目标（恢复4+参考48），负面4故意不符合；56/56是控制/审计通过而非任务成功率；busy仅资源占用，两seed非结构留出。')
    save(RESULT/'final_summary.json',summary)
    handles={'recovery':dict(run=7895,run_pid=110913,run_exit_code=0,audit=88556,audit_exit_code=0),
             'negative':dict(run=58754,run_exit_code=0,audit=68313,audit_pid=113982,audit_exit_code=0),
             'reference':dict(run=90454,run_pid=113917,run_exit_code=0,audit=49509,audit_pid=118364,audit_exit_code=0)}
    # reference audit真实句柄与终态由调用者核验后填入，不能由结果文件臆测退出。
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),handles=handles,freeze_sha256={k:sha(freeze_path(k)) for k in stages},source_sha256=hashes(),
        audit_source_sha256={k:a['audit_source_sha256'] for k,a in stages.items()},artifact_sha256={f'{k}_{n}.json':sha(RESULT/f'{k}_{n}.json') for k in stages for n in ('summary','audit')},
        tests=dict(focused=11,full=121,full_handle=17232,full_exit_code=0,full_log_sha256=sha(RESULT/'raw/tests_full.log'),initial_schema_failure='旧事实替身objects为区域字符串/None，补position/velocity schema后通过；失败源/log保留。'),
        raw_real_path=str((RESULT/'raw').resolve()),raw_bytes=sum(p.stat().st_size for p in (RESULT/'raw').rglob('*') if p.is_file()),no_new_model_or_download=True,
        concurrency='恢复控制/CPU实现与v17 GPU末段重叠；参考批次开始时GPU已退出，负面审计与参考CPU短暂重叠；不据墙钟比较速度。',
        timer='实际已发生availability tick和observed_tick分列，初始busy不提供未来恢复时刻；busy不是人体暂离。',
        simulation_time='共同t0到明确声明终止，包括最后技能停车；仿真在高层计算时暂停，推理墙钟和通信决策独立，不称真实异步团队流畅度。')
    save(RESULT/'execution_receipt.json',receipt);print('派生归档',summary['stage_counts'],summary['reference_totals'],flush=True)

if __name__=='__main__':report()
