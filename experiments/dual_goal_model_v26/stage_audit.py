"""完整局部阶段的独立派生审计；等待落盘，不读取半写轨迹或重复单例。"""
import argparse
import json
import time
from pathlib import Path
from experiments.physical.run import ROOT, save, sha
from experiments.dual_goal_model_v26.run import RESULT, FREEZE, hashes
from experiments.dual_goal_model_v26.audit import episode_audit


def stage_audit(wait=False):
    f=json.loads(FREEZE.read_text())
    assert f['source_sha256']==hashes()
    records=[r for r in f['episodes'] if r['stage']=='local']
    assert len(records)==16
    # summary 是该局全部 trace/decisions 关闭后才写出的终态标志。
    while True:
        complete=[r for r in records if (RESULT/'raw/episodes'/r['id']/'summary.json').exists()]
        print('局部审计等待完整阶段',len(complete),16,flush=True)
        if len(complete)==16:break
        if not wait:raise RuntimeError('局部16尚未全部终态，未执行审计。')
        time.sleep(30)
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(f['model_spec']['path'],local_files_only=True)
    copied=RESULT/'raw/local_audit_sources';copied.mkdir(parents=True,exist_ok=True)
    sources={}
    for name in ('audit.py','stage_audit.py'):
        p=ROOT/'experiments/dual_goal_model_v26'/name
        (copied/name).write_bytes(p.read_bytes());sources[name]=sha(p)
    reports=[]
    for record in records:
        r=episode_audit(RESULT/'raw/episodes'/record['id'],tokenizer);reports.append(r)
        print(r['id'],r['passed'],r['task_success'],r['physically_safe'],[k for k,v in r['checks'].items() if not v],flush=True)
    assert sources=={name:sha(ROOT/'experiments/dual_goal_model_v26'/name) for name in sources}
    out=dict(total=16,passed=sum(r['passed'] for r in reports),task_success=sum(r['task_success'] for r in reports),
             physically_safe=sum(r['physically_safe'] for r in reports),total_ticks=sum(r['total_ticks'] for r in reports),
             episodes=reports,freeze_sha256=sha(FREEZE),independent_sources_sha256=sources,
             scope='仅完整local16独立审计，原运行继续full64；原运行/评分未改，任务失败与轨迹重建/安全分列。')
    save(RESULT/'local_audit.json',out)
    print('局部独立审计终态',out['passed'],out['task_success'],out['physically_safe'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true')
    stage_audit(p.parse_args().wait)
