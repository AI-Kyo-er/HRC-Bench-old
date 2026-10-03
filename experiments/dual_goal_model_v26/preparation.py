"""探针真实退出后独立归档准备证据；不改原freeze/输入/执行源。"""
import json
import subprocess
from datetime import datetime,timezone
from pathlib import Path
from experiments.physical.run import ROOT,sha,save
from experiments.dual_goal_model_v26.run import RESULT,FREEZE,hashes


def preparation():
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes()
    source=RESULT/'raw/postfreeze_audit_sources';source.mkdir(parents=True,exist_ok=True)
    extra=['experiments/dual_goal_model_v26/audit.py','tests/test_dual_goal_model_audit_v26.py','experiments/dual_goal_model_v26/preparation.py']
    for p in extra:out=source/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((ROOT/p).read_bytes())
    lifecycle=json.loads((RESULT/'raw/preparation_lifecycle.json').read_text());assert lifecycle['probe']['exit_code']==0
    pid=lifecycle['probe']['pid'];probe=subprocess.run(['ps','-p',str(pid),'-o','pid=,stat=,etime=,args='],capture_output=True,text=True).stdout;assert not probe
    capacity=json.loads((RESULT/'capacity_probe_receipt.json').read_text());assert capacity['passed'] and capacity['freeze_sha256']==sha(FREEZE)
    r=dict(utc=datetime.now(timezone.utc).isoformat(),freeze_sha256=sha(FREEZE),frozen_sources_unchanged=True,source_sha256=hashes(),postfreeze_audit_source_sha256={p:sha(ROOT/p) for p in extra},
        lifecycle=lifecycle,probe_pid_probe=probe,capacity_receipt_sha256=sha(RESULT/'capacity_probe_receipt.json'),probe_source_copy_all_exact=all(sha(RESULT/'raw/probe/source'/p)==v for p,v in hashes().items()),
        completed_log_sha256={p.name:sha(p) for p in (RESULT/'raw').glob('*.log')},episodes_frozen=80,local=16,full=64,task_generations_started=False,
        tests=dict(initial_focused=11,frozen_focused=13,before_audit_full=228,postfreeze_audit_focused=4,final_full=232,final_full_exit=0,
            audit_first_error='替身缺record_id；17包含误收集旧13，新增4。保留首失败源/日志，修替身和import，不弱化业务。'),
        raw_real_path=str((RESULT/'raw').resolve()),scope='仅CPU准备与非任务最大预算容量预检通过，非正式任务成绩；独立audit/test源码晚于freeze单独SHA。')
    assert r['probe_source_copy_all_exact'];save(RESULT/'preparation_receipt.json',r);print('准备证据归档完成',r['freeze_sha256'])


if __name__=='__main__':preparation()
