"""r1独立全tick审计及H共同物理交付前缀；复用已验证规范投影。"""
import argparse
import gzip
import hashlib
import json
import math
from experiments.physical.run import ROOT,save,sha
from experiments.structure_foundation_v20.canonical import physics,equal
from experiments.sustained_structure_v21.audit import episode_audit
from experiments.sustained_structure_v21.run_r1 import RESULT,freeze_path,hashes


def prefix_digest(folder,end_tick):
    h=hashlib.sha256();count=0
    with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
        for line in stream:
            state=json.loads(line)
            if state['tick']>end_tick:break
            h.update(json.dumps(physics(state),sort_keys=True,separators=(',',':')).encode());count+=1
    return dict(sha256=h.hexdigest(),ticks=count)


def audit(stage):
    f=json.loads(freeze_path(stage).read_text());assert f['source_sha256']==hashes()
    reports=[];summaries={}
    for case in f['cases']:
        folder=RESULT/'raw'/(stage+'_r1')/case['id'];report=episode_audit(folder);reports.append(report)
        summaries[case['id']]=json.loads((folder/'summary.json').read_text())
        print(case['id'],report['passed'],report['task_success'],[k for k,v in report['checks'].items() if not v],flush=True)
    pairs=[]
    if stage=='H':
        for initial in ('left','right'):
            pair=[case for case in f['cases'] if case['initial_blue']==initial]
            a,b=[summaries[case['id']] for case in pair]
            pa,pb=[s['checkpoints']['handoff_delivery'] for s in (a,b)]
            digests=[prefix_digest(RESULT/'raw'/(stage+'_r1')/case['id'],s['checkpoints']['handoff_delivery']['tick']) for case,s in zip(pair,(a,b))]
            pairs.append(dict(initial_blue=initial,ids=[case['id'] for case in pair],
                same_checkpoint_physics=equal(pa,pb),same_tick=pa['tick']==pb['tick'],full_prefix_physics_exact=digests[0]==digests[1],
                prefix_digests=digests,green_source_preserved=all(math.dist(
                    s['checkpoints']['handoff_delivery']['objects']['green']['position'],
                    s['initial_state']['objects']['green']['position'])<f['config']['non_target_interval_displacement_limit_m'] for s in (a,b))))
    result=dict(stage=stage,total=len(reports),passed=sum(r['passed'] for r in reports),task_success=sum(r['task_success'] for r in reports),
        physically_safe=sum(r['physically_safe'] for r in reports),total_ticks=sum(r['total_ticks'] for r in reports),episodes=reports,pairs=pairs,
        all_controls_evidence_and_safety_pass=all(r['passed'] for r in reports) and all(all(r[k] for k in ('same_checkpoint_physics','same_tick','full_prefix_physics_exact','green_source_preserved')) for r in pairs),
        freeze_sha256=sha(freeze_path(stage)),runtime_source_sha256=hashes(),audit_source_sha256=sha(ROOT/'experiments/sustained_structure_v21/audit_r1.py'),
        shared_audit_source_sha256=sha(ROOT/'experiments/sustained_structure_v21/audit.py'),original_C_failure_not_replaced=True)
    save(RESULT/f'{stage}_audit_r1.json',result);assert result['all_controls_evidence_and_safety_pass']
    print('r1独立审计通过',stage,result['total_ticks'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('C_return','H'));audit(p.parse_args().stage)
