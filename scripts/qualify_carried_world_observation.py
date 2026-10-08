"""用完整运行的实际决策帧核对下一版载荷测量，绝不改原始输入。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from hrc_pilot.carried_world_observation import observable_carried_world
from hrc_pilot.joint_world import observable_world


def qualify(root):
    if not (root/'summary.json').exists():raise ValueError('要求完整终态，不能使用增长中的轨迹')
    files=[root/'episode'/name for name in ['trace.jsonl','human_policy_io.jsonl']]
    raw={p:p.read_bytes() for p in files}
    trace=[json.loads(x) for x in raw[files[0]].decode().splitlines() if x.strip()]
    decisions=[json.loads(x) for x in raw[files[1]].decode().splitlines() if x.strip()]
    observations=[]
    for decision in decisions:
        scene=decision['observation_source_scene'];record=trace[round(decision['time_s']*20)]
        drawer=scene['measured_world']['drawer'];regions=scene['regions_xyz']
        previous=observable_world(record,regions,drawer,measurement_version=4)
        if previous!=scene['measured_world']:raise ValueError('存量v4测量无法原样重建')
        current=observable_carried_world(record,regions,drawer)
        changes=[key for key in previous if previous[key]!=current[key]]
        if set(changes)-{'measurement_version','released_object_support_contacts','current_measured_fact_sentences'}:
            raise ValueError('修复改变了载荷离手事实以外的字段')
        carried=[name for name,state in current['public_scene_measurements']['objects'].items() if state['human_carried']]
        for name in carried:
            if current['released_object_support_contacts'][name]:raise ValueError('携带物仍有离手支撑声明')
            if any(text.startswith(name+' is released') for text in current['current_measured_fact_sentences']):
                raise ValueError('携带物仍有离手文字声明')
        observations.append({'time_s':decision['time_s'],'decision_id':decision['decision_id'],
            'human_carried_objects':carried,'changed_fields':changes,
            'corrected_objects':[name for name in carried if previous['released_object_support_contacts'][name]],
            'previous_facts':previous['current_measured_fact_sentences'],
            'proposed_facts':current['current_measured_fact_sentences']})
    for path,content in raw.items():
        if path.read_bytes()!=content:raise ValueError('源记录被改变')
    modules=[Path('src/hrc_pilot/carried_world_observation.py'),Path('src/hrc_pilot/joint_world.py')]
    return {'status':'saved_decision_frames_verified','run':root.name,
        'source_sha256':{str(p):sha256(content).hexdigest() for p,content in raw.items()},
        'implementation_sha256':{str(p):sha256(p.read_bytes()).hexdigest() for p in modules},
        'decision_count':len(decisions),'affected_decision_count':sum(bool(x['corrected_objects']) for x in observations),
        'observations':observations,'runtime_integrated':False,'formal_benchmark_score':None,
        'scope':'仅在保存物理帧上修正携带载荷的离手事实；没有新NN或Sim运行，不证明策略改善、真人拟真或协作有效。'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=qualify(args.input_dir)
    with args.output.open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps({key:result[key] for key in ['status','decision_count','affected_decision_count','runtime_integrated']},ensure_ascii=False))
