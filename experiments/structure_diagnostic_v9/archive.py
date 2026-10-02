"""已完成输出的失败对照与执行回执；不修改冻结、预测或评分。"""
import datetime
import json
import subprocess
from collections import Counter

from experiments.physical.run import ROOT,save,sha
from experiments.structure_diagnostic_v9.run import RESULT,FREEZE,INPUTS,SPEC,DOWNLOAD


def main():
    calls_path=RESULT/'raw/model/calls.json'
    calls=json.loads(calls_path.read_text())
    assert len(calls)==80
    failures=[]
    for full in calls:
        if full['record']['view']!='full_history' or full['score']['protocol_progress']:continue
        r=full['record']
        aid=next(a for a in calls if a['record']['source_case_id']==r['source_case_id'] and
            a['record']['stage']==r['stage'] and a['record']['view']=='public_scope_aid')
        obs=json.loads(r['messages'][1]['content'])
        aobs=json.loads(aid['record']['messages'][1]['content'])
        added=aobs.pop('external_public_scope_aid')
        assert aobs==obs and full['record']['messages'][0]==aid['record']['messages'][0]
        failures.append(dict(id=r['id'],source_case_id=r['source_case_id'],stage=r['stage'],seed=r['seed'],
            outer_blue=r['outer_blue'],reverse_menu=r['reverse_menu'],original_messages=r['messages'],
            full_prediction=full['prediction'],full_choice=full['choice'],full_score=full['score'],
            aid_messages=aid['record']['messages'],aid_prediction=aid['prediction'],aid_choice=aid['choice'],aid_score=aid['score'],
            only_observation_difference=added,
            original_physical_placements=obs['physical_placements'],source_before_tick=r['source_before_tick'],
            explanation='局部作用域已结束后再次finish，不推进；不是已观察到的错误blue目标选择。',
            predictions_applied_to_environment=False,executed_physics_ticks=0))
    assert len(failures)==6
    raw_path=RESULT/'raw/failure_pairs.json';save(raw_path,failures)
    distribution=Counter(f"{r['outer_blue']}_{'reverse' if r['reverse_menu'] else 'normal'}" for r in failures)
    save(RESULT/'failure_audit.json',dict(failure_count=len(failures),stage=5,ids=[r['id'] for r in failures],
        by_target_menu=dict(distribution),by_seed=dict(Counter(r['seed'] for r in failures)),
        full_choices=dict(Counter(r['full_choice'] for r in failures)),
        aid_choices=dict(Counter(r['aid_choice'] for r in failures)),all_aid_protocol_progress=all(r['aid_score']['protocol_progress'] for r in failures),
        actual_model_physics_ticks=0,predictions_applied_to_environment=False,
        conclusion='6次均已结束作用域再次finish/未推进，不能称6个blue目标记忆错误；公开aid同时增加目标/作用域/进度/义务等信息，非单因素归因。',
        canonical_failure_pairs_path=str(raw_path.relative_to(ROOT)),canonical_failure_pairs_sha256=sha(raw_path),
        calls_sha256=sha(calls_path),postfreeze_archiver_sha256=sha(ROOT/'experiments/structure_diagnostic_v9/archive.py')))
    finished=json.loads((RESULT/'raw/model/finished.json').read_text())
    pid=finished['pid']
    own_process=subprocess.run(['ps','-p',str(pid),'-o','pid=,comm='],capture_output=True,text=True)
    assert own_process.returncode==1 and not own_process.stdout.strip()
    gpu_query=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    gpu_processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
    assert str(pid) not in [s.split(',')[0].strip() for s in gpu_processes.splitlines()]
    audit=json.loads((RESULT/'audit.json').read_text());assert audit['all_passed']
    model_path=ROOT/'models/Qwen2.5-14B-Instruct'
    asset_files=['config.json','generation_config.json','model.safetensors.index.json','tokenizer_config.json','tokenizer.json','vocab.json','merges.txt']
    old_receipt=json.loads((ROOT/'results/model_scale_v4/execution_receipt_v6.json').read_text())
    current_assets={n:sha(model_path/n) for n in asset_files}
    assert current_assets==old_receipt['model_config_tokenizer_sha256']
    tracked=['summary.json','audit.json','failure_audit.json']
    raw_names=['frozen_inputs.json','model/calls.json','model/started.json','model/finished.json','model/gpu_preflight.json',
        'model.log','tests.log','focused_tests.log','audit.log','failure_pairs.json']
    save(RESULT/'execution_receipt.json',dict(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sessions=dict(test_and_freeze=dict(id=1750,exit_code=0),model=dict(id=32772,pid=pid,exit_code=0),audit=dict(id=12308,exit_code=0)),
        actual_calls=80,physics_actions_executed=0,no_new_downloads=True,no_new_gate=True,old_14b_gate_passed=False,
        live_task_handles=[],own_model_pid_absent=True,own_pid_absent_from_gpu_processes=True,gpu_after_query=gpu_query,
        model=finished['model'],started=json.loads((RESULT/'raw/model/started.json').read_text()),
        official_weight_receipt_path=str(DOWNLOAD.relative_to(ROOT)),official_weight_receipt_sha256=sha(DOWNLOAD),
        eight_shard_official_sha_verification_reused=True,model_config_tokenizer_sha256=current_assets,
        freeze_sha256=sha(FREEZE),inputs_sha256=sha(INPUTS),model_spec_sha256=sha(SPEC),
        postfreeze_changes='仅新增只读audit.py/archive.py和归档文档；冻结运行源/输入/评分不变。',
        all_audit_checks_passed=audit['all_passed'],
        validation=dict(focused_command='.venv-llm/bin/python -m unittest tests.test_structure_diagnostic_v9',focused_passed=5,
            full_command='.venv-llm/bin/python -m unittest discover -s tests',full_passed=40,
            permanent_tests=True,no_additional_gpu_calls=True),
        artifacts_sha256={n:sha(RESULT/n) for n in tracked},
        raw_artifacts_sha256={n:sha(RESULT/'raw'/n) for n in raw_names},
        raw_storage_path=str((RESULT/'raw').resolve()),raw_total_bytes=sum(p.stat().st_size for p in (RESULT/'raw').rglob('*') if p.is_file())))
    print('6失败原输入输出对照及回执完成；模型PID/GPU资源已释放。',flush=True)


if __name__=='__main__':main()
