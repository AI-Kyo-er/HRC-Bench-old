"""基于已完成审计和实际进程/GPU检查保存交接回执，不再调用模型。"""
import argparse
import datetime
import json
import subprocess

from experiments.physical.run import ROOT,save,sha
from experiments.structure_diagnostic_v12.run import RESULT,FREEZE,INPUTS,DOWNLOAD,SPEC


def main(audit_session):
    finished=json.loads((RESULT/'raw/model/finished.json').read_text());pid=finished['pid']
    assert finished['completed_calls']==128
    audit=json.loads((RESULT/'audit.json').read_text());assert audit['all_passed']
    process=subprocess.run(['ps','-p',str(pid),'-o','pid=,comm='],capture_output=True,text=True)
    assert process.returncode==1 and not process.stdout.strip()
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
    assert str(pid) not in [line.split(',')[0].strip() for line in processes.splitlines()]
    old=json.loads((ROOT/'results/model_scale_v4/execution_receipt_v6.json').read_text())
    current_assets={name:sha(ROOT/'models/Qwen2.5-14B-Instruct'/name) for name in old['model_config_tokenizer_sha256']}
    assert current_assets==old['model_config_tokenizer_sha256']
    names=['summary.json','audit.json','failure_audit.json','direction_error_audit.json']
    raw_names=['frozen_inputs.json','model/calls.json','model/started.json','model/finished.json','model/gpu_preflight.json',
        'model.log','freeze.log','focused_tests.log','tests.log','audit.log',
        'nonprogress_calls.json']
    save(RESULT/'execution_receipt.json',dict(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sessions=dict(focused_tests=dict(exit_code=0,passed=5),full_tests=dict(id=2466,exit_code=0,passed=57),
            freeze=dict(id=83444,exit_code=0),model=dict(id=5426,pid=pid,exit_code=0),
            final_audit=dict(id=audit_session,exit_code=0)),
        actual_calls=128,source_checkpoints=32,physics_actions_executed=0,no_new_downloads=True,no_new_gate=True,old_14b_gate_passed=False,
        live_task_handles=[],own_model_pid_absent=True,own_pid_absent_from_gpu_processes=True,gpu_after_query=gpu,
        started=json.loads((RESULT/'raw/model/started.json').read_text()),model=finished['model'],
        official_weight_receipt_path=str(DOWNLOAD.relative_to(ROOT)),official_weight_receipt_sha256=sha(DOWNLOAD),
        eight_shard_official_sha_verification_reused=True,model_config_tokenizer_sha256=current_assets,
        freeze_sha256=sha(FREEZE),inputs_sha256=sha(INPUTS),model_spec_sha256=sha(SPEC),
        postfreeze_changes='仅新增audit.py/receipt.py派生审计与归档文档；冻结运行源/评分/输入保持原样。',
        postfreeze_receipt_writer_sha256=sha(ROOT/'experiments/structure_diagnostic_v12/receipt.py'),
        all_audit_checks_passed=True,normal_full_exact_count=audit['normal_full_exact_count'],pairs_audited=len(audit['pair_checks']),
        validation=dict(focused_command='.venv-llm/bin/python -m unittest tests.test_structure_diagnostic_v12',focused_passed=5,
            full_command='.venv-llm/bin/python -m unittest discover -s tests',full_passed=57,
            permanent_tests=True),
        artifacts_sha256={n:sha(RESULT/n) for n in names},raw_artifacts_sha256={n:sha(RESULT/'raw'/n) for n in raw_names},
        raw_storage_path=str((RESULT/'raw').resolve()),raw_total_bytes=sum(p.stat().st_size for p in (RESULT/'raw').rglob('*') if p.is_file())))
    print('v12回执完成，自有模型PID/GPU资源已释放。',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--audit-session',type=int)
    main(parser.parse_args().audit_session)
