"""全部正式运行/派生审计真实退出后的独立回执，不改旧freeze或输入。"""
import importlib.metadata
import json
import subprocess
from datetime import datetime,timezone
from pathlib import Path
from experiments.physical.run import ROOT,save,sha,asset_hashes
from experiments.dual_goal_model_v26.run import RESULT,FREEZE,hashes


def finalize():
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes()
    summary=json.loads((RESULT/'final_summary.json').read_text())
    audit=json.loads((RESULT/'model_audit.json').read_text())
    runtime=json.loads((RESULT/'model_summary.json').read_text())
    lifecycle=json.loads((RESULT/'raw/final_lifecycle.json').read_text())
    assert summary['total']==audit['total']==runtime['total']==80
    assert all(v['exit_code']==0 for v in lifecycle['formal'].values())
    probes={str(v['pid']):subprocess.run(['ps','-p',str(v['pid']),'-o','pid=,stat=,etime=,args='],capture_output=True,text=True).stdout
            for v in lifecycle['formal'].values() if 'pid' in v}
    assert not any(probes.values())
    copied=RESULT/'raw/final_derivation_sources';copied.mkdir(parents=True,exist_ok=True)
    names=('audit.py','stage_audit.py','report.py','finalize.py')
    derivations={}
    for name in names:
        p=ROOT/'experiments/dual_goal_model_v26'/name
        (copied/name).write_bytes(p.read_bytes());derivations[name]=sha(p)
    assert audit['audit_source_sha256']==sha(RESULT/'raw/audit_sources/audit.py')==derivations['audit.py']
    assert summary['report_source_sha256']==derivations['report.py']
    assert all(sha(RESULT/'raw/run_sources'/p)==h for p,h in hashes().items())
    assert f['assets_sha256']==asset_hashes()
    assert f['packages']=={p:importlib.metadata.version(p) for p in f['packages']}
    prediction=[]
    for record in f['episodes']:
        rows=json.loads((RESULT/'raw/episodes'/record['id']/'decisions.json').read_text())
        prediction.extend(r['prediction'] for r in rows if r['phase']=='model')
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free,memory.used','--format=csv,noheader,nounits'],text=True)
    raw=(RESULT/'raw').resolve()
    r=dict(utc=datetime.now(timezone.utc).isoformat(),freeze_sha256=sha(FREEZE),source_sha256=hashes(),frozen_sources_unchanged=True,
           assets_sha256=asset_hashes(),packages=f['packages'],model_spec=f['model_spec'],model_metadata=runtime['metadata'],
           model_verification_receipt_sha256=f['model_verification_receipt_sha256'],runtime_copies_all_exact=True,
           independent_derivation_sha256=derivations,local_audit_sources=json.loads((RESULT/'local_audit.json').read_text())['independent_sources_sha256'],
           audit_source_copy_exact=True,lifecycle=lifecycle,pid_probes=probes,nvidia_after=gpu,
           capacity_probe_receipt_sha256=sha(RESULT/'capacity_probe_receipt.json'),preparation_receipt_sha256=sha(RESULT/'preparation_receipt.json'),
           artifact_sha256={p.name:sha(p) for p in RESULT.glob('*.json') if p.name!='execution_receipt.json'},
           log_sha256={p.name:sha(p) for p in raw.glob('*.log')},raw_real_path=str(raw),raw_bytes=sum(p.stat().st_size for p in raw.rglob('*') if p.is_file()),
           calls=len(prediction),max_actual_input_tokens=max(p['input_tokens'] for p in prediction),max_actual_output_tokens=max(p['output_tokens'] for p in prediction),
           inputs_truncated=False,automatic_retries=0,condition_changes_after_outputs=False,
           outcomes=dict(task_success=summary['overall']['task_success'],safe_task_success=summary['overall']['safe_task_success'],
                         trace_integrity=summary['overall']['trace_integrity'],physical_contract_ok=summary['overall']['physical_contract_ok'],
                         strict_audit_passed=audit['passed']),
           tests=lifecycle['tests'],failures_preserved='首次单例派生入口缺PYTHONPATH exit1保留；仅修进程入口后exit0。测试替身首错保留；不重复物理/模型。',
           timing='推理时仿真暂停；模型墙钟独立。失败到终止时长不是完成效率，成功成本与共同成功配对子集分别报告；局部真实prefix成本不消失。',
           scope='80预设自主闭环全条件。表达/显式账本/确认时机均有信息和新近程度差，单模板单物理seed，非纯结构因果、泛化或完整六结构。')
    save(RESULT/'execution_receipt.json',r)
    print('最终回执完成',r['outcomes'],r['calls'],r['raw_bytes'],flush=True)


if __name__=='__main__':finalize()
