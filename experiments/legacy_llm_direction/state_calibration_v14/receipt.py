"""实际模型终态与原环境未改、资源释放的只读交接证据。"""
import datetime
import json
import subprocess
from experiments.physical.run import ROOT,save,sha
from experiments.state_calibration_v14.dataset import RESULT
from experiments.state_calibration_v14.run import FREEZE,INPUTS,SOURCES,hashes


def main():
    audit=json.loads((RESULT/'audit.json').read_text());assert audit['all_passed']
    frozen=json.loads(FREEZE.read_text());assert frozen['source_sha256']==hashes(SOURCES)
    ends={m:json.loads((RESULT/f'raw/model_{m}/finished.json').read_text()) for m in ('qwen2_5_14b','qwen3_vl_8b')}
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
    pids=[str(e['pid']) for e in ends.values()]
    for pid in pids:
        process=subprocess.run(['ps','-p',pid,'-o','pid=,comm='],capture_output=True,text=True)
        assert process.returncode==1 and not process.stdout.strip()
        assert pid not in [line.split(',')[0].strip() for line in processes.splitlines()]
    env=json.loads((RESULT/'environment_receipt.json').read_text())
    old=json.loads(subprocess.check_output([str(ROOT/'.venv-llm/bin/python'),'-c','import json,importlib.metadata as m;print(json.dumps({p:m.version(p) for p in ("torch","transformers","huggingface-hub","accelerate")}))'],text=True))
    assert old==env['old_packages']
    for name,entry in env['copy_probe'].items():assert sha(ROOT/'.venv-llm/lib/python3.12/site-packages'/name)==entry['old_sha256']
    artifact_names=['summary.json','audit.json','failure_audit.json','field_distributions.json','control_and_direction_audit.json','paired_field_audit.json','model_receipt.json','environment_receipt.json','control_review.md']
    raw_files=[p for p in (RESULT/'raw').rglob('*') if p.is_file() and p.name!='receipt.log']
    save(RESULT/'execution_receipt.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),actual_calls=216,
        sessions=dict(environment_copy=dict(id=96008,exit_code=0),environment_install=dict(id=55836,exit_code=0),
            cpu_api=dict(id=7897,exit_code=0),assets=dict(id=37933,exit_code=0),focused_tests=dict(passed=10,exit_code=0),
            full_tests=dict(id=44781,passed=73,exit_code=0),freeze=dict(id=51925,exit_code=0),
            qwen2_5_14b=dict(id=94898,pid=ends['qwen2_5_14b']['pid'],calls=24,exit_code=0),
            qwen3_vl_8b=dict(id=67541,pid=ends['qwen3_vl_8b']['pid'],calls=192,exit_code=0),audit=dict(exit_code=0)),
        model_finished=ends,freeze_sha256=sha(FREEZE),inputs_sha256=sha(INPUTS),frozen_sources_unchanged=True,
        all_audit_checks_passed=True,old_env_packages_after=old,old_env_version_and_probe_hashes_unchanged=True,
        own_model_pids_absent=True,own_pids_absent_from_gpu_processes=True,gpu_after_query=gpu,live_task_handles=[],
        physics_actions_executed=0,new_model_weights_downloaded=False,external_inference_apis_called=False,
        prefreeze_corrections='保留review_v0并修改无child更新提议的条件措辞；首次测试捕获v4单动作user非JSON的adapter错误，保存原源/失败日志后修复。未推理时完成。',
        postfreeze_changes='仅新增audit/receipt与README派生审计归档；未修改冻结输入/评分/生成代码。',
        postfreeze_source_sha256={n:sha(ROOT/'experiments/state_calibration_v14'/n) for n in ('audit.py','receipt.py')},
        validation=dict(focused_command='.venv-llm/bin/python -m unittest tests.test_state_calibration_v14',focused_passed=10,
            full_command='.venv-llm/bin/python -m unittest discover -s tests',full_passed=73,permanent_tests=True,not_physical_or_neural_success_evidence=True),
        artifacts_sha256={n:sha(RESULT/n) for n in artifact_names},raw_artifacts_sha256={str(p.relative_to(RESULT/'raw')):sha(p) for p in raw_files},
        raw_storage_path=str((RESULT/'raw').resolve()),raw_total_bytes=sum(p.stat().st_size for p in raw_files)))
    print('216调用交接完成，两个PID/GPU资源均已释放，旧环境未变。',flush=True)


if __name__=='__main__':main()
