#!/usr/bin/env python3
"""在已结束的真实记录上检查公共观测契约；不是重模拟或策略成绩。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from build_joint_progress_report import RUNS
from hrc_pilot.public_scene_measurements import public_scene_measurements


def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def qualify(results,output):
    output.mkdir(parents=True,exist_ok=True);checks=[];pending=[];examples=[]
    wanted={('coherent_snack_service_detour_symbolic_20261008',3),
            ('coherent_drink_storage_change_use_symbolic_20261008',10),
            ('coherent_drawer_access_leave_return_symbolic_20261008',9)}
    for name,label,kind in RUNS:
        root=results/name;ep=root/'episode'
        if not (root/'summary.json').exists():pending.append(name);continue
        if json.loads((root/'interaction_verification.json').read_text())['status']!='verified':
            pending.append(name);continue
        trace=rows(ep/'trace.jsonl');human=rows(ep/'human_policy_io.jsonl')
        record_by_time={round(r['time_s'],6):r for r in trace}
        checked=0;objects=0;relations=0
        for decision in human:
            record=record_by_time[round(decision['time_s'],6)]
            source=decision.get('observation_source_scene',decision['private_input']['scene'])
            movable=[n for n in record['objects'] if n+'_personal' in source['regions_xyz']]
            measurement=public_scene_measurements(record,movable)
            assert measurement['contact_measurement_available']
            for obj,value in measurement['objects'].items():
                np.testing.assert_allclose(value['xyz_m'],source['objects_xyz'][obj],atol=1e-12,rtol=0)
                assert value['human_carried']==(obj in set(record['human_execution'].get('carried_objects',[])) or
                                                obj==record['human_execution']['held_object'])
            assert not {'score','task_success','private_context','next_action'}.intersection(measurement)
            checked+=1;objects+=len(measurement['objects']);relations+=len(measurement['relative_object_measurements'])
            if (name,decision['decision_id']) in wanted:
                examples.append({'run':name,'decision_id':decision['decision_id'],'time_s':decision['time_s'],
                    'observed_choice':decision['choice'],'reconstructed_public_measurements':measurement,
                    'original_human_scene_keys':list(decision['private_input']['scene']),
                    'interpretation':'实际记录的输入重建，不证明新接口改变了NN决策。'})
        hashes={file:sha256((ep/file).read_bytes()).hexdigest() for file in ['trace.jsonl','human_policy_io.jsonl']}
        checks.append({'run':name,'kind':kind,'decisions_checked':checked,'object_measurements':objects,
            'relative_measurements':relations,'source_sha256':hashes})
    report={'status':'saved_public_measurements_qualified','role':'saved_record_input_contract_check_not_policy_benchmark',
        'runs_checked':len(checks),'decisions_checked':sum(c['decisions_checked'] for c in checks),
        'object_measurements_checked':sum(c['object_measurements'] for c in checks),
        'relative_measurements_checked':sum(c['relative_measurements'] for c in checks),
        'source_module_sha256':sha256(Path('src/hrc_pilot/public_scene_measurements.py').read_bytes()).hexdigest(),
        'formal_benchmark_score':None,'checks':checks,'not_checked_runs':pending,'examples':examples}
    (output/'measurement_contract_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in {'checks','examples'}},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir',type=Path,default=Path('results/continuous_v2'))
    parser.add_argument('--output-dir',type=Path,default=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/public_observation_contract_20261008'))
    args=parser.parse_args();qualify(args.results_dir,args.output_dir)
