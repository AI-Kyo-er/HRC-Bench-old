"""只读原控制/审计归档，不改变冻结或重新执行物理。"""
import datetime
import json
import subprocess
from experiments.physical.run import ROOT,save,sha
from experiments.transport_cycle_v22.run import RESULT,FREEZE,hashes


def build():
    a=json.loads((RESULT/'control_audit_dev0.json').read_text());r=json.loads((RESULT/'control_summary_dev0.json').read_text());f=json.loads(FREEZE.read_text())
    assert a['passed']==a['total']==8 and r['control_sequence_completed']==8 and f['source_sha256']==hashes()
    episodes=a['episodes'];groups={k:{field:sum(e['groups'][k][field] for e in episodes) for field in ('records','ticks','negative_distance_records')} for k in episodes[0]['groups']}
    supported=sum(v['supported_ticks'] for e in episodes for v in e['leg_support'].values() if v['loaded']);support_ticks=sum(v['ticks'] for e in episodes for v in e['leg_support'].values() if v['loaded'])
    result=dict(total=8,strict_passed=a['passed'],physically_safe=a['physically_safe'],total_ticks=a['total_ticks'],
        decisions=sum(e['cost']['decisions'] for e in episodes),physical_attempts=sum(e['cost']['physical_attempts'] for e in episodes),
        leg_count=sum(len(e['legs']) for e in episodes),carrier_arrivals=sum(ev['kind']=='carrier_arrived' for e in episodes for ev in e['events']),
        payload_arrivals=sum(ev['kind']=='payload_arrived' for e in episodes for ev in e['events']),
        loaded_motion_ticks=support_ticks,loaded_supported_ticks=supported,loaded_support_fraction=supported/support_ticks,contact_groups=groups,
        green_max_displacement_m=max(e['green_max_displacement_m'] for e in episodes),
        costs=[dict(id=e['id'],makespan_ticks=e['makespan_ticks'],cost=e['cost']) for e in episodes],
        freeze_sha256=sha(FREEZE),not_strategy_task_or_combination_success=True,report_source_sha256=sha(ROOT/'experiments/transport_cycle_v22/report.py'))
    save(RESULT/'final_summary.json',result)
    probes={str(pid):subprocess.run(['ps','-p',str(pid),'-o','pid=,stat=,args='],capture_output=True,text=True).stdout.strip() for pid in (174522,176077)}
    assert not any(probes.values())
    raw=RESULT/'raw'
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),handles=dict(control=dict(handle=44035,pid=174522,exit_code=0),audit=dict(handle=36741,pid=176077,exit_code=0),full_tests=dict(handle=90219,exit_code=0)),
        pid_probes=probes,freeze_sha256=sha(FREEZE),source_unchanged=f['source_sha256']==hashes(),source_sha256=hashes(),assets_sha256=f['assets_sha256'],packages=f['packages'],
        audit_source_sha256=a['audit_source_sha256'],audit_source_copy_sha256=sha(raw/'audit_dev0_sources/audit.py'),
        audit_dependency_sha256={p:sha(ROOT/p) for p in ('experiments/sustained_structure_v21/audit.py','experiments/structure_foundation_v20/audit_v2.py','experiments/transport_cycle_v22/cycle.py','experiments/transport_cycle_v22/canonical.py','experiments/structure_foundation_v20/canonical.py','experiments/structure_handoff_v15/reference_audit.py')},
        tests=dict(new_focused=10,full=180,full_exit=0,nature='永久状态机/来源反例替身，物理证据来自8真实控制及全tick审计，无新模型生成。'),
        artifacts_sha256={p.name:sha(p) for p in RESULT.glob('*.json') if p.name!='execution_receipt.json'},logs_sha256={p.name:sha(p) for p in raw.glob('*.log')},
        raw_real_path=str(raw.resolve()),raw_bytes=sum(p.stat().st_size for p in raw.rglob('*') if p.is_file()),
        current_vs_historical='cycle当前编号/支撑事实才判断本行程；第一delivery/return兼容字段永久保留且独立审计不丢历史，不能作当前来源或空载载荷贡献。',
        no_gpu_model_or_download=True,no_extra_conditions_or_retries=True,clock='240Hz共同t0=240到固定序列结束，包括抓放/停车/等待；交流零tick但各耗1决策。',
        scalar_audit_roundoff='独立numpy/Python范数复算允许1e-12；规范完整物理/所有事件布尔/请求序列/metadata精确，无成功/接触门槛放宽。',
        limitations='仅8指定物理控制，两seed实例，无模型/任务策略/结构泛化。当前blue抓放要求无活动载台；未覆盖从无关支撑在运动期间取blue。')
    save(RESULT/'execution_receipt.json',receipt);print('归档',result['strict_passed'],result['total_ticks'],receipt['raw_bytes'],flush=True)


if __name__=='__main__':build()
