#!/usr/bin/env python3
"""按原始NN决定和物理记录独立重建请求身份及缓存递送。"""
import argparse
import json
from pathlib import Path

import numpy as np


def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def verify(ep):
    trace=rows(ep/'trace.jsonl');human=rows(ep/'human_policy_io.jsonl')
    receipts=rows(ep/'human_command_delivery.jsonl');assert len(receipts)==len(trace)-1
    previous=None
    for r,delivery in zip(trace,receipts):
        index=max(i for i,d in enumerate(human) if d['time_s']<=r['time_s']+1e-9)
        decision=human[index]['parsed_decision'];command=delivery['command']
        assert delivery['neural_decision_id']==index
        assert all(command[k]==decision[k] for k in ['intent','object_id','destination','speed_mps'])
        np.testing.assert_allclose(delivery['physics_time_s'],r['physics_time_s'],atol=1e-7)
        phase=r['human_execution']['motor_phase'];assert delivery['phase_before_delivery']==phase
        new=index!=previous;assert delivery['new_request']==new
        assert delivery['forwarded_to_primitive']==(new or phase not in {'idle','holding','failed'})
        previous=index
    return {'episode':str(ep),'status':'verified','neural_requests':len(human),
        'control_steps':len(receipts),'cached_terminal_requests_suppressed':sum(not d['forwarded_to_primitive'] for d in receipts),
        'interpretation':'核对新请求与缓存请求身份，不生成后续动作；通过不代表人策略可靠或HRC成功。'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    root=parser.parse_args().input_dir
    assert json.loads((root/'provenance.json').read_text())['human_command_delivery']=='neural_request'
    result={'status':'verified','episodes':[verify(p.parent) for p in root.rglob('human_policy_io.jsonl')]}
    assert result['episodes']
    (root/'human_command_delivery_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False))
