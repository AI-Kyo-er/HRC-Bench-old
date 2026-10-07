#!/usr/bin/env python3
"""事后查找同一缓存place在完成后产生缺失握持错误的直接时间证据。"""
import argparse
import json
from pathlib import Path


def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def audit(ep):
    trace=rows(ep/'trace.jsonl');decisions=rows(ep/'human_policy_io.jsonl');witnesses=[]
    for a,b in zip(trace,trace[1:]):
        old=a['human_execution'];new=b['human_execution']
        if not (old['motor_phase']=='idle' and new['motor_phase']=='failed'
                and new.get('motor_failure')=='requested_object_not_in_measured_hand'):continue
        before=[(i,d) for i,d in enumerate(decisions) if d['time_s']<a['time_s']-1e-9]
        at_boundary=[d for d in decisions if abs(d['time_s']-a['time_s'])<1e-9]
        if not before or at_boundary:continue
        index,d=before[-1]
        if d['parsed_decision']['intent']!='place':continue
        if old['accepted_intent']!='place' or new['accepted_intent']!='place':continue
        witnesses.append({'neural_decision_id':index,'neural_decision_time_s':d['time_s'],
            'before_time_s':a['time_s'],'after_time_s':b['time_s'],
            'object_id':d['parsed_decision']['object_id'],
            'before_phase':old['motor_phase'],'after_phase':new['motor_phase'],
            'before_measured_in_hand':old.get('object_measured_in_hand'),
            'motor_failure':new['motor_failure'],'new_neural_decision_at_transition':False})
    return {'episode':str(ep),'cached_place_restart_witness_count':len(witnesses),'witnesses':witnesses,
        'interpretation':'保存直接观察到的缓存请求重启见证；没有见证不证明不存在其他请求生命周期问题，不评分或改写NN输出。'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    root=parser.parse_args().input_dir
    episodes=[audit(p.parent) for p in sorted(root.rglob('human_policy_io.jsonl'))]
    result={'status':'audited','episodes':episodes}
    (root/'cached_request_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False))
