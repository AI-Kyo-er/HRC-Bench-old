"""只读两个正式审计的派生汇总与配对前缀；不改变运行/评分。"""
import datetime
import gzip
import hashlib
import json
import subprocess
from experiments.physical.run import ROOT,save,sha
from experiments.transport_cycle_v22.canonical import physics
from experiments.sustained_combination_v23.run import RESULT,freeze_path,hashes


def prefix(folder,tick):
    h=hashlib.sha256();count=0
    with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
        for line in stream:
            state=json.loads(line)
            if state['tick']>tick:break
            h.update(json.dumps(physics(state),sort_keys=True,separators=(',',':')).encode());count+=1
    return dict(tick=tick,ticks=count,sha256=h.hexdigest())


def build():
    audits={stage:json.loads((RESULT/f'{stage}_audit_dev0.json').read_text()) for stage in ('control','reference')}
    assert audits['control']['passed']==8 and audits['reference']['passed']==24
    ref=audits['reference']['episodes'];pairs=[];costs=[]
    for target in ('left','right'):
        for presence in ('stay','retain','withdraw'):
            for seed in (120,121):
                es=[e for e in ref if e['case']['initial_blue']==target and e['case']['presence']==presence and e['case']['seed']==seed]
                endpoints=[next(e['actual_tick'] for e in r['service_events'] if e['kind']=='partner_check_handoff') for r in es]
                digests=[prefix(RESULT/'raw'/'dev0'/'reference'/e['id'],tick) for e,tick in zip(es,endpoints)]
                pairs.append(dict(initial_blue=target,presence=presence,seed=seed,ids=[e['id'] for e in es],handoff_prefixes=digests,full_physical_prefix_exact=digests[0]==digests[1]))
    assert all(p['full_physical_prefix_exact'] for p in pairs)
    for target in ('left','right'):
        for role in ('partner_return','robot'):
            for presence in ('stay','retain','withdraw'):
                es=[e for e in ref if e['case']['initial_blue']==target and e['public_role']==role and e['case']['presence']==presence]
                costs.append(dict(initial_blue=target,role=role,presence=presence,episodes=len(es),makespan_ticks=[e['makespan_ticks'] for e in es],
                    decisions=[e['cost']['decisions'] for e in es],physical_attempts=[e['cost']['physical_attempts'] for e in es],wait_ticks=[e['cost']['wait_ticks'] for e in es],requests_check=[e['cost']['requests_check'] for e in es]))
    all_es=[e for a in audits.values() for e in a['episodes']]
    groups={g:{k:sum(e['groups'][g][k] for e in all_es) for k in ('records','ticks','negative_distance_records')} for g in all_es[0]['groups']}
    loaded=[v for e in all_es for v in e['leg_support'].values() if v['loaded']]
    result=dict(total=32,strict_passed=sum(a['passed'] for a in audits.values()),task_success=sum(a['task_success'] for a in audits.values()),physically_safe=sum(a['physically_safe'] for a in audits.values()),
        total_ticks=sum(a['total_ticks'] for a in audits.values()),stages={k:{f:a[f] for f in ('total','passed','task_success','physically_safe','total_ticks')} for k,a in audits.items()},
        contact_groups=groups,loaded_motion_ticks=sum(v['ticks'] for v in loaded),loaded_supported_ticks=sum(v['supported_ticks'] for v in loaded),reference_costs=costs,role_pairs=pairs,
        max_non_target_interval_displacement_m=max(e['max_non_target_interval_displacement_m'] for e in all_es),
        control_outcomes=[dict(id=e['id'],passed=e['passed'],task_success=e['task_success'],actual_score=e['actual_score'],qualified_ticks=e['qualified_ticks'],makespan_ticks=e['makespan_ticks']) for e in audits['control']['episodes']],
        no_model_or_structural_generalization=True,report_source_sha256=sha(ROOT/'experiments/sustained_combination_v23/report.py'))
    save(RESULT/'final_summary.json',result)
    freeze_checks={stage:dict(freeze_sha256=sha(freeze_path(stage)),source_unchanged=json.loads(freeze_path(stage).read_text())['source_sha256']==hashes()) for stage in audits}
    assert all(v['source_unchanged'] for v in freeze_checks.values())
    # 真实句柄终态由执行者回收后写入；不从receipt宣称存活。
    probes={str(pid):subprocess.run(['ps','-p',str(pid),'-o','pid=,stat=,args='],capture_output=True,text=True).stdout.strip() for pid in (182502,184809,186035,191080)}
    assert not any(probes.values())
    raw=RESULT/'raw'
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),freeze_checks=freeze_checks,source_sha256=hashes(),assets_sha256=json.loads(freeze_path('control').read_text())['assets_sha256'],packages=json.loads(freeze_path('control').read_text())['packages'],
        handles=dict(control=dict(run=97658,run_pid=182502,run_exit=0,audit=66015,audit_pid=184809,audit_exit=0),reference=dict(run=64743,run_pid=186035,run_exit=0,audit=REFERENCE_AUDIT_HANDLE,audit_pid=REFERENCE_AUDIT_PID,audit_exit=0)),
        pid_probes=probes,tests=dict(new_focused=12,full=192,full_handle=70520,full_exit=0,nature='服务/协议/公共事实替身永久回归，实际安全和恢复只据32物理及独立全tick。'),
        audit_source_sha256={stage:a['audit_source_sha256'] for stage,a in audits.items()},audit_source_copy_sha256={stage:sha(raw/(stage+'_audit_sources')/'audit.py') for stage in audits},
        audit_dependencies_sha256={p:sha(ROOT/p) for p in ('experiments/transport_cycle_v22/audit.py','experiments/transport_cycle_v22/cycle.py','experiments/transport_cycle_v22/canonical.py','experiments/sustained_structure_v21/audit.py','experiments/sustained_structure_v21/service.py','experiments/structure_foundation_v20/audit_v2.py','experiments/structure_foundation_v20/canonical.py','experiments/structure_handoff_v15/reference_audit.py')},
        artifacts_sha256={p.name:sha(p) for p in RESULT.glob('*.json') if p.name!='execution_receipt.json'},logs_sha256={p.name:sha(p) for p in raw.glob('*.log')},
        raw_real_path=str(raw.resolve()),raw_bytes=sum(p.stat().st_size for p in raw.rglob('*') if p.is_file()),
        no_gpu_model_download=True,no_conditions_changed_or_retries=True,clock='同一240Hz/t0=240至声明，包括停车/等待；高层/交流计算零tick但每次1决策，不比较墙钟。',
        negative_controls='C0两条检查未完及对应child未终止；C1两条当前载台/载荷未接回。全部真实declare停止不事后恢复，失败到终止时长不是完成时间。',
        script_vs_policy='初始共同历史及首个实际检查接受后role提议/acceptreject是脚本；政策实际request/抓放/yield触发真实响应；无自主acceptreject动作。',
        scope='32指定开发组合。role两分支均4抓放但路径/语义不同，不据同数量/同前缀声称严格操作匹配或纯结构效应。',
        roundoff='独立范数标量1e-12；完整物理/事件/历史精确，接触和成功阈值不放宽。')
    save(RESULT/'execution_receipt.json',receipt);print('归档',result['strict_passed'],result['task_success'],result['total_ticks'],receipt['raw_bytes'],flush=True)


# 在原参考审计真实启动后填写其执行句柄，不预言运行状态。
REFERENCE_AUDIT_HANDLE=7452
REFERENCE_AUDIT_PID=191080
if __name__=='__main__':
    assert REFERENCE_AUDIT_HANDLE is not None and REFERENCE_AUDIT_PID is not None
    build()
