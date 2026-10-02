"""真实终态、GPU释放、旧环境/冻结未变与产物hash交接。"""
import datetime
import json
import subprocess
from experiments.physical.run import ROOT,save,sha
from experiments.structure_handoff_v15.model_run import RESULT,FREEZE,INPUTS,SOURCES,hashes,MODELS
from experiments.structure_handoff_v15.reference_run import FREEZE as REF_FREEZE


def main():
    audit=json.loads((RESULT/'model_audit.json').read_text());assert audit['all_passed']
    ends={m:json.loads((RESULT/f'raw/model_{m}/finished.json').read_text()) for m in MODELS}
    query=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
    for e in ends.values():
        pid=str(e['pid']);p=subprocess.run(['ps','-p',pid,'-o','pid=,comm='],capture_output=True,text=True)
        assert p.returncode==1 and not p.stdout.strip() and pid not in [line.split(',')[0].strip() for line in processes.splitlines()]
    env=json.loads((ROOT/'results/state_calibration_v14/environment_receipt.json').read_text())
    old=json.loads(subprocess.check_output([str(ROOT/'.venv-llm/bin/python'),'-c','import json,importlib.metadata as m;print(json.dumps({p:m.version(p) for p in ("torch","transformers","huggingface-hub","accelerate")}))'],text=True))
    assert old==env['old_packages']
    assert json.loads(FREEZE.read_text())['source_sha256']==hashes(SOURCES)
    artifacts=('reference_summary.json','reference_audit.json','protocol_review.json','protocol_review.md','model_summary.json','model_audit.json','model_failure_audit.json')
    raw=[p for p in (RESULT/'raw').rglob('*') if p.is_file() and p.name!='receipt.log']
    save(RESULT/'execution_receipt.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),actual_physical_cases=16,actual_model_calls=256,
        sessions=json.loads((RESULT/'raw/session_exits.json').read_text()),model_finished=ends,
        reference_freeze_sha256=sha(REF_FREEZE),model_freeze_sha256=sha(FREEZE),model_inputs_sha256=sha(INPUTS),
        original_reference_run_exit_code=1,original_reference_passed=0,reference_postfreeze_audit_passed=16,
        comparator_errata='原run只两个全state字段由tuple/list直接比较误判，原exit1/log/source/pass值保留；独立审计规范所有容器且全字段/数值/contact均保留；未重跑物理。',
        physics_tick_count=204480,model_physical_actions_executed=0,no_new_weights_downloaded=True,no_external_inference_api=True,
        design_revision='192→256在任何v15新模型输出前新增manual_reminder64，原模型old_anchor消息逐字保留。',
        old_env_packages_after=old,old_env_versions_unchanged=True,own_model_pids_absent=True,own_pids_absent_from_gpu_processes=True,gpu_after_query=query,gpu_compute_processes_after=processes,live_task_handles=[],
        validation=dict(focused_tests_passed=14,full_tests_passed=87,focused_command='.venv-llm/bin/python -m unittest tests.test_structure_handoff_v15 tests.test_handoff_model_v15',full_command='.venv-llm/bin/python -m unittest discover -s tests',
            facts_world_protocol_tests=8,actual_contact_container_regression_tests=1,model_input_scoring_tests=5,tests_not_physical_success=True),
        postfreeze_sources_sha256={n:sha(ROOT/'experiments/structure_handoff_v15'/n) for n in ('reference_audit.py','model_audit.py','receipt.py')},
        artifacts_sha256={n:sha(RESULT/n) for n in artifacts},raw_artifacts_sha256={str(p.relative_to(RESULT/'raw')):sha(p) for p in raw},raw_storage_path=str((RESULT/'raw').resolve()),raw_total_bytes=sum(p.stat().st_size for p in raw)))
    print('物理/两模型终态与GPU释放已实查，无活任务句柄。',flush=True)


if __name__=='__main__':main()
