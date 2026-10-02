"""实际终态、资源释放、冻结与派生语义评分的交接回执。"""
import datetime
import json
import subprocess

from experiments.physical.run import ROOT,save,sha
from experiments.state_readout_v13.run import RESULT,FREEZE,INPUTS,SPEC,DOWNLOAD,source_hashes


def main():
    finished=json.loads((RESULT/'raw/model/finished.json').read_text());pid=finished['pid']
    audit=json.loads((RESULT/'audit.json').read_text());assert audit['all_passed'] and finished['completed_calls']==128
    frozen=json.loads(FREEZE.read_text());assert frozen['source_sha256']==source_hashes()
    process=subprocess.run(['ps','-p',str(pid),'-o','pid=,comm='],capture_output=True,text=True)
    assert process.returncode==1 and not process.stdout.strip()
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
    assert str(pid) not in [line.split(',')[0].strip() for line in processes.splitlines()]
    old=json.loads((ROOT/'results/model_scale_v4/execution_receipt_v6.json').read_text())
    assets={n:sha(ROOT/'models/Qwen2.5-14B-Instruct'/n) for n in old['model_config_tokenizer_sha256']}
    assert assets==old['model_config_tokenizer_sha256']
    names=['summary.json','semantic_state_summary.json','audit.json','failure_audit.json','state_field_audit.json','old_error_observation_links.json']
    raw_names=['frozen_inputs.json','model/calls.json','model/started.json','model/finished.json','model/gpu_preflight.json',
        'model.log','freeze.log','focused_tests.log','tests.log','focused_semantic_tests.log','focused_semantic_tests_initial.log',
        'semantic.log','audit.log','semantic_rows.json','incorrect_calls.json']
    save(RESULT/'execution_receipt.json',dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sessions=dict(full_tests=dict(id=64816,exit_code=0,passed=62),focused_before_freeze=dict(exit_code=0,passed=5),
            focused_postfreeze_semantic=dict(exit_code=0,passed=6),freeze=dict(id=87604,exit_code=0),
            model=dict(id=79320,pid=pid,exit_code=0,terminal_verified_by='write_stdin'),
            semantic=dict(exit_code=0),final_audit=dict(exit_code=0)),
        actual_calls=128,action_queries=64,state_queries=64,physics_actions_executed=0,no_new_downloads=True,no_new_gate=True,
        live_task_handles=[],own_model_pid_absent=True,own_pid_absent_from_gpu_processes=True,gpu_after_query=gpu,
        started=json.loads((RESULT/'raw/model/started.json').read_text()),model=finished['model'],memory_estimate=frozen['memory_estimate'],
        official_weight_receipt_path=str(DOWNLOAD.relative_to(ROOT)),official_weight_receipt_sha256=sha(DOWNLOAD),
        eight_shard_official_sha_verification_reused=True,model_config_tokenizer_sha256=assets,
        freeze_sha256=sha(FREEZE),inputs_sha256=sha(INPUTS),model_spec_sha256=sha(SPEC),frozen_sources_unchanged=True,
        postfreeze_changes='仅新增semantic.py/audit.py/receipt.py派生语义评分、只读审计与文档；运行源/原评分/输入不改。键序澄清晚于freeze，早于成绩解释，未按结果改提示。',
        postfreeze_source_sha256={n:sha(ROOT/'experiments/state_readout_v13'/n) for n in ('semantic.py','audit.py','receipt.py')},
        all_audit_checks_passed=True,action_anchor_counts=audit['action_anchor_counts'],
        validation=dict(before_freeze_focused_command='.venv-llm/bin/python -m unittest tests.test_state_readout_v13',before_freeze_focused_passed=5,
            before_freeze_full_command='.venv-llm/bin/python -m unittest discover -s tests',before_freeze_full_passed=62,
            postfreeze_focused_same_command=True,postfreeze_focused_passed=6,postfreeze_full_suite_not_rerun=True,
            tests_are_protocol_and_parser_unit_tests_not_physical_or_neural_success=True),
        artifacts_sha256={n:sha(RESULT/n) for n in names},raw_artifacts_sha256={n:sha(RESULT/'raw'/n) for n in raw_names},
        raw_storage_path=str((RESULT/'raw').resolve()),raw_total_bytes=sum(p.stat().st_size for p in (RESULT/'raw').rglob('*') if p.is_file())))
    print('128调用回执完成，模型PID及自有GPU资源已释放，无活句柄。',flush=True)


if __name__=='__main__':main()
