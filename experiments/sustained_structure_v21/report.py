"""只读既有审计的派生回执；不改变任何运行/评分冻结。"""
import datetime
import json
import subprocess
from experiments.physical.run import ROOT,save,sha
from experiments.sustained_structure_v21.run import RESULT,hashes,freeze_path
from experiments.sustained_structure_v21.run_r1 import hashes as r1_hashes,freeze_path as r1_freeze


def build():
    files={'C':'C_audit_dev0.json','N':'N_audit_dev0.json','H':'H_audit_r1.json','C_return':'C_return_audit_r1.json'}
    audits={k:json.loads((RESULT/v).read_text()) for k,v in files.items()}
    assert audits['C']['passed']==6 and audits['N']['passed']==24 and audits['H']['passed']==4 and audits['C_return']['passed']==2
    stages={k:{field:a[field] for field in ('total','passed','task_success','physically_safe','total_ticks')} for k,a in audits.items()}
    originals=[audits[k] for k in ('C','N','H')]
    ncost=[]
    for presence in ('stay','retain','withdraw'):
        for policy in ('public_ledger_progress','conservative_wait'):
            rows=[r for r in audits['N']['episodes'] if r['case']['presence']==presence and r['case']['policy']==policy]
            ncost.append(dict(presence=presence,policy=policy,episodes=len(rows),makespan_ticks=sorted({r['makespan_ticks'] for r in rows}),
                decisions=sorted({r['cost']['decisions'] for r in rows}),check_requests=sorted({r['cost']['requests_check'] for r in rows}),
                wait_ticks=sorted({r['cost']['wait_ticks'] for r in rows}),physical_attempts=sorted({r['cost']['physical_attempts'] for r in rows})))
    summary=dict(stages=stages,original_36={field:sum(a[field] for a in originals) for field in ('total','passed','task_success','physically_safe','total_ticks')},
        additional_return_controls=stages['C_return'],N_cost=ncost,H_pairs=audits['H']['pairs'],
        C_failures=[dict(id=r['id'],failed_checks=[k for k,v in r['checks'].items() if not v],groups=r['groups'],contact_evidence=r['first_peak_contact_evidence']) for r in audits['C']['episodes'] if not r['passed']],
        original_failed_C_not_replaced=True,not_model_or_combination_generalization=True,
        report_source_sha256=sha(ROOT/'experiments/sustained_structure_v21/report.py'))
    save(RESULT/'final_summary.json',summary)
    freezes={k:freeze_path(k) if k in ('C','N') else r1_freeze(k) for k in files}
    checks={}
    for k,path in freezes.items():
        f=json.loads(path.read_text());checks[k]=dict(source_unchanged=f['source_sha256']==(hashes() if k in ('C','N') else r1_hashes()),freeze_sha256=sha(path))
    assert all(v['source_unchanged'] for v in checks.values())
    probes={str(pid):subprocess.run(['ps','-p',str(pid),'-o','pid=,stat=,args='],capture_output=True,text=True).stdout.strip() for pid in (158174,161141,164438,164504,165988,166722,167812,170057)}
    assert not any(probes.values()),'等待自己的原audit终态，不重启。'
    raw=RESULT/'raw';raw_bytes=sum(p.stat().st_size for p in raw.rglob('*') if p.is_file())
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stages=stages,freeze_checks=checks,
        handles={'C':dict(run=32322,run_pid=158174,run_exit=0,audit=6218,audit_pid=161141,audit_exit=1),
        'N':dict(run=16688,run_pid=164438,run_exit=0,audit=66016,audit_pid=170057,audit_exit=0),
        'C_return':dict(run=79317,run_pid=164504,run_exit=0,audit=22365,audit_pid=165988,audit_exit=0),
        'H':dict(run=7691,run_pid=166722,run_exit=0,audit=20550,audit_pid=167812,audit_exit=0)},pid_probes=probes,
        tests=dict(initial_focused=20,initial_full=166,initial_full_handle=24762,initial_full_exit=0,r1_focused=4,final_full=170,final_full_handle=97488,final_full_exit=0,
                   nature='协议/service/FakeWorld回归；实际安全/贡献来自独立全tick物理审计，不来自替身。',
                   first_failure='公开reference测试替身缺transport accepted事件；只补合法公共fixture，失败源/log保留raw/prefreeze_test_failure。'),
        audit_versions=dict(C=audits['C']['audit_source_sha256'],N=audits['N']['audit_source_sha256'],
            C_return=audits['C_return']['audit_source_sha256'],H=audits['H']['audit_source_sha256'],
            note='C_return审计结束后、H首次审计前，audit_r1只将自己的green源区保持由浮点全等改为原配置1cm；H配对完整物理仍精确相等。旧C_return源保存raw/C_return_audit_sources；H源保存raw/H_audit_sources。',
            preservation='1cm连续非目标区间位移在C首次独立事后audit加入，源/config定义公开冻结已有1cm；不是runtime任务评分或接触标准放宽。'),
        source_sha256=hashes(),r1_source_sha256=r1_hashes(),assets_sha256=json.loads(freezes['C'].read_text())['assets_sha256'],packages=json.loads(freezes['C'].read_text())['packages'],
        artifacts_sha256={p.name:sha(p) for p in RESULT.glob('*.json') if p.name!='execution_receipt.json'},
        logs_sha256={p.name:sha(p) for p in raw.glob('*.log')},raw_real_path=str(raw.resolve()),raw_bytes=raw_bytes,
        no_gpu_model_download=True,concurrency='C/实现初段与已授权v19 GPU尾段重叠；N与C_return/H各独立CPU物理/审计重叠。不比较墙钟速度。',
        clock='240Hz仿真tick；makespan共同t0=240至完成声明，含抓放/停车及真实等待；高层/推理墙钟不推进仿真。',
        actual_events_vs_obligations='actual_contribution_events核实际检查/返回/载荷返回，obligation_flags和vacuous_obligation_satisfaction单列；无义务条件真不代表物理贡献发生。')
    save(RESULT/'execution_receipt.json',receipt)
    print('归档',summary['original_36'],raw_bytes,flush=True)


if __name__=='__main__':build()
