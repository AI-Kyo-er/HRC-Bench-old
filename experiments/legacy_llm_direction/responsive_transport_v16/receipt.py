"""只读终态、旧冻结未变与存储/source回执。"""
import datetime
import json
import os
import subprocess
from experiments.physical.run import ROOT,save,sha,versions,asset_hashes
from experiments.responsive_transport_v16.run import RESULT,CONTROL_FREEZE,REFERENCE_FREEZE,hashes


def main():
    control=json.loads((RESULT/'control_audit.json').read_text());reference=json.loads((RESULT/'reference_audit.json').read_text());assert control['all_passed'] and reference['all_passed']
    for freeze in (CONTROL_FREEZE,REFERENCE_FREEZE):
        f=json.loads(freeze.read_text());assert f['source_sha256']==hashes() and f['packages']==versions() and f['assets_sha256']==asset_hashes()
    r=json.loads(REFERENCE_FREEZE.read_text());assert r['control_freeze_sha256']==sha(CONTROL_FREEZE) and r['control_summary_sha256']==sha(RESULT/'control_summary.json') and r['control_audit_sha256']==sha(RESULT/'control_audit.json')
    old=json.loads((ROOT/'experiments/structure_v8/cases/reference_freeze.json').read_text());assert all(sha(ROOT/n)==v for n,v in old['source_sha256'].items())
    pid=71266;ps=subprocess.run(['ps','-p',str(pid),'-o','pid=,comm='],capture_output=True,text=True);assert ps.returncode==1 and not ps.stdout.strip()
    raw=[p for p in (RESULT/'raw').rglob('*') if p.is_file() and p.name!='receipt.log'];artifacts=('control_summary.json','control_audit.json','reference_summary.json','reference_audit.json')
    source_snapshots=RESULT/'raw/frozen_sources';source_snapshots.mkdir(exist_ok=True)
    for name,value in r['source_sha256'].items():
        p=source_snapshots/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes());assert sha(p)==value
    # 保存两个实际执行的派生audit版本，不用事后sourcehash冒充控制审计版本。
    earlier=RESULT/'raw/postfreeze_audit_sources/controls_audit.py';assert sha(earlier)==control['auditor_source_sha256']
    current=RESULT/'raw/postfreeze_audit_sources/reference_audit.py';current.write_bytes((ROOT/'experiments/responsive_transport_v16/audit.py').read_bytes());assert sha(current)==reference['auditor_source_sha256']
    raw=[p for p in (RESULT/'raw').rglob('*') if p.is_file() and p.name!='receipt.log']
    save(RESULT/'execution_receipt.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),actual_control_cases=10,actual_reference_cases=16,actual_total_ticks=184280,
        sessions=dict(controls=dict(id=80580,exit_code=0,cases=10),control_audit=dict(id=94467,exit_code=0),reference=dict(id=7221,pid=pid,exit_code=0,cases=16),reference_audit=dict(id=42441,exit_code=0),full_tests=dict(id=65164,exit_code=0,passed=97),focused_tests=dict(exit_code=0,passed=10)),
        own_reference_pid_absent=True,live_task_handles=[],gpu_programs_started=0,models_called=0,downloads_started=0,external_inference_apis_called=False,
        environment_path=str((ROOT/'.venv-llm').resolve()),packages=versions(),assets_sha256=asset_hashes(),old_v8_runtime_sources_unchanged=True,
        active_control_freeze_sha256=sha(CONTROL_FREEZE),reference_freeze_sha256=sha(REFERENCE_FREEZE),runtime_sources_unchanged=True,
        unexecuted_control_freeze_v0_sha256=sha(ROOT/'experiments/responsive_transport_v16/cases/control_freeze.json'),
        pre_execution_design_corrections='保留首份未执行freeze/源：移除公开8秒未来timer文字；在任何v16真实物理输出前按v8已知时长增加wait_ready，参考12→16；adaptive改名availability_greedy，10控制曲线/时窗不变。',
        initial_test_failure='FactsWorld父pick自增1tick与新替身3180叠加，导致3181vs3180；原失败源/log保存，替身后续模拟改3179使总3180，协议未按结果改动。',
        physical_failures_or_retries=0,no_runtime_freeze_source_mutations=True,
        postfreeze_audit_versions='控制审计源快照SHA对应control_audit；随后只增加参考四策略派生成本/输入表，参考audit独立SHA，未覆盖已绑定控制产物或冻结运行源。',
        validation=dict(focused_command='.venv-llm/bin/python -m unittest tests.test_responsive_transport_v16',focused_passed=10,full_command='.venv-llm/bin/python -m unittest discover -s tests',full_passed=97,focused_tests_are_facts_or_saved_schema_not_physical=True),
        raw_storage_path=str((RESULT/'raw').resolve()),raw_total_bytes=sum(p.stat().st_size for p in raw),raw_artifacts_sha256={str(p.relative_to(RESULT/'raw')):sha(p) for p in raw},
        artifacts_sha256={n:sha(RESULT/n) for n in artifacts},postfreeze_sources_sha256={n:sha(ROOT/'experiments/responsive_transport_v16'/n) for n in ('audit.py','receipt.py')}))
    print('10控制+16参考均实际exit0，184280tick审计通过，旧v8源未变，无活句柄/模型/GPU/下载。',flush=True)


if __name__=='__main__':main()
