"""仅派生描述性分组与回执；真实句柄终态单独核验后填写。"""
import datetime
import json
import subprocess
from experiments.physical.run import ROOT,save,sha
from experiments.sustained_model_v19.run import RESULT,FREEZE,hashes

def report(run_exit_code,audit_handle,audit_exit_code):
    assert run_exit_code==audit_exit_code==0
    a=json.loads((RESULT/'model_audit.json').read_text());s=json.loads((RESULT/'model_summary.json').read_text());assert a['all_inputs_and_scores_pass']
    grouped=[]
    for view in ('full_history','public_ledger_aid'):
        for field,values in (('initial_blue',('left','right')),('update',('none','accepted','rejected')),('availability',('ready','temporarily_busy'))):
            for value in values:
                subset=[r for r in a['episodes'] if r['view']==view and r['record'][field]==value]
                grouped.append(dict(view=view,field=field,value=value,total=len(subset),goal_compliant=sum(r['goal_compliant'] for r in subset),safety_qualified_success=sum(r['safety_qualified_task_success'] for r in subset),
                    decisions=sum(r['cost']['decisions'] for r in subset),real_wrong_placements=sum(len(r['real_wrong_blue_placements']) for r in subset),invalid=sum(r['cost']['invalid'] for r in subset)))
    support=[r['contacts']['support_coverage'] for r in a['episodes'] if r['contacts']['transport_ticks']]
    durations={view:dict(success_completion_ticks=[r['makespan_ticks'] for r in a['episodes'] if r['view']==view and r['safety_qualified_task_success']],
        failure_until_termination_ticks=[r['makespan_ticks'] for r in a['episodes'] if r['view']==view and not r['safety_qualified_task_success']]) for view in ('full_history','public_ledger_aid')}
    pair_details=[]
    for i,pair in enumerate(a['pairs']):
        members=[a['episodes'][i],a['episodes'][i+12]]
        assert members[0]['record']==members[1]['record']==pair['case']
        pair_details.append(dict(case=pair['case'],both_success=pair['full'] and pair['aid'],
            views={r['view']:dict(id=r['id'],success=r['safety_qualified_task_success'],goal_compliant=r['goal_compliant'],
                cost=r['cost'],episode_until_termination_ticks=r['makespan_ticks'],
                success_completion_ticks=r['makespan_ticks'] if r['safety_qualified_task_success'] else None,
                failure_until_termination_ticks=None if r['safety_qualified_task_success'] else r['makespan_ticks']) for r in members}))
    common_success=[r for r in pair_details if r['both_success']]
    common_costs={v:dict(total=len(common_success),completion_ticks=[r['views'][v]['success_completion_ticks'] for r in common_success],
        summed_costs={k:sum(r['views'][v]['cost'][k] for r in common_success) for k in a['episodes'][0]['cost']}) for v in ('full_history','public_ledger_aid')}
    result=dict(identification=dict(total=12,correct=sum(r['correct'] for r in a['identification']),not_autonomous_gate=True),groups=a['groups'],factor_groups=grouped,
        pair_transitions={label:sum(r['full']==x and r['aid']==y for r in a['pairs']) for label,x,y in (('both_success',True,True),('full_only',True,False),('aid_only',False,True),('both_fail',False,False))},
        all_twelve_paired_success_and_cost=pair_details,both_success_subset_costs=common_costs,
        durations_by_success=durations,total_calls=a['total_calls'],parse_errors=a['parse_errors'],truncated=a['truncated'],max_actual_input_tokens=a['max_input_tokens'],total_output_tokens=a['total_output_tokens'],
        total_physical_ticks=a['total_physical_ticks'],contacts_records=a['contacts_records'],support_coverage_started=min(support) if support else None,
        max_green_displacement_m=max(r['contacts']['max_green_displacement_m'] for r in a['episodes']),model_wall_seconds=a['model_wall_seconds'],metadata=s['metadata'],
        interpretation='识别为明确指令映射；24自主闭环为单seed开发条件，账本额外帮助；不作组合/结构泛化或显著性推断。仿真推理期间暂停，合法慢策略实际成本分列。失败直到终止时长不是任务完成时间，不能将漏动作后较早结束算效率改善。')
    save(RESULT/'final_summary.json',result)
    query=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),run=dict(handle=98899,pid=121752,exit_code=run_exit_code),audit=dict(handle=audit_handle,exit_code=audit_exit_code),
        freeze_sha256=sha(FREEZE),runtime_source_sha256=hashes(),runtime_source_unchanged=hashes()==json.loads(FREEZE.read_text())['source_sha256'],
        audit_source_sha256=a['audit_source_sha256'],report_source_sha256=sha(ROOT/'experiments/sustained_model_v19/report.py'),
        artifacts_sha256={name:sha(RESULT/name) for name in ('model_summary.json','model_audit.json','final_summary.json','raw/failure_audit.json','raw/gpu_preflight.json','raw/identification_calls.json')},
        tests=dict(focused=8,focused_exit_code=0,full_at_freeze=129,full_handle=37212,full_exit_code=0,full_log_sha256=sha(RESULT/'raw/tests_full.log'),
            post_audit_regression=2,post_audit_regression_exit=0,post_audit_log_sha256=sha(RESULT/'raw/tests_audit.log'),
            shared_final_full=146,shared_final_full_handle=17124,shared_final_full_exit=0,
            shared_final_full_log='results/structure_foundation_v20/raw/tests_full_final.log',
            shared_final_full_log_sha256=sha(ROOT/'results/structure_foundation_v20/raw/tests_full_final.log')),
        preliminary_audits=dict(identification=dict(handle=83588,exit_code=0,source_sha256=sha(RESULT/'raw/identification_preaudit_sources/audit.py'),
                report_sha256=sha(RESULT/'raw/identification_preaudit.json')),
            full_history_original=dict(handle=53627,exit_code=1,source_sha256=sha(RESULT/'raw/full_history_audit_failed/audit.py'),
                report_sha256=sha(RESULT/'raw/full_history_audit_failed/full_history_audit.json'),
                failure='事后汇总变量selected被局部blue方向字符串覆盖；逐例输入/物理检查全部true，非模型或物理运行失败。原报告及源保留。'),
            full_history_corrected=dict(handle=80262,exit_code=0,source_sha256=sha(RESULT/'raw/full_history_audit_v1_sources/audit.py'),
                report_sha256=sha(RESULT/'full_history_audit.json'),change='仅派生局部变量selected_destination及聚合results_passed；冻结运行源/模型输入与输出未改/未重跑。')),
        cpu_freeze_handle=81918,cpu_freeze_exit_code=0,raw_path=str((RESULT/'raw').resolve()),raw_bytes=sum(p.stat().st_size for p in (RESULT/'raw').rglob('*') if p.is_file()),
        postrun_gpu_query=query,runner_pid_absent=subprocess.run(['ps','-p','121752','-o','pid='],capture_output=True,text=True).returncode==1,
        model_metadata=s['metadata'],model_download_receipt_sha256=sha(ROOT/'results/reasoning_baseline_v17/download_receipt.json'),no_download=True,
        inputs='识别12与24初始输入/案例及动态构造源先冻；未来自主输入不伪预冻，事后按实际物理/公开历史逐步重建。',
        concurrency='v18所有运行/独立审计已exit0后才启动GPU；期间按后续独立授权并行v20 CPU指定控制/审计，无额外GPU/model调用；共享主机负载下墙钟不作性能比较。',
        inference_and_physics='物理DT只在world.step推进，推理墙钟另列；包含技能停留/停车，不能称实时异步流畅度。')
    save(RESULT/'execution_receipt.json',receipt);print('归档',result['groups'],result['identification'],flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run-exit',type=int,required=True);p.add_argument('--audit-handle',type=int,required=True);p.add_argument('--audit-exit',type=int,required=True);args=p.parse_args();report(args.run_exit,args.audit_handle,args.audit_exit)
