#!/usr/bin/env python3
"""描述人实际选定对象与当次意图对象的关系；不禁止帮助对方或判断动机。"""
import argparse
from collections import Counter
import json
from pathlib import Path


def audit(ep):
    decisions=[json.loads(s) for s in (ep/'human_policy_io.jsonl').read_text().splitlines() if s.strip()]
    groups=Counter();records=[]
    for row in decisions:
        targets=row['personal_goal_state']['personal_targets'];objects={t['object_id'] for t in targets}
        receivers={t['destination'].split(':',1)[1] for t in targets if t['destination'].startswith('on:')}
        chosen=row['parsed_decision'];obj=chosen['object_id']
        if chosen['intent'] not in {'grasp','place','push'}:group='no_object_manipulation_selected'
        elif obj in objects:group='current_personal_target_object'
        elif obj in receivers:group='current_personal_goal_receiver'
        else:group='other_visible_object'
        groups[group]+=1
        records.append({'time_s':row['time_s'],'intent':chosen['intent'],'object_id':obj,
            'scope':group,'current_personal_targets':targets,'model_reason':chosen.get('reason','')})
    return {'episode':str(ep),'status':'audited','decision_counts':dict(groups),'records':records,
        'interpretation':'只描述对象是否属于当次NN声明的目标／接收物。操作其他物品可以是帮助、工具或准备动作，不自动视为错误；没有驱动执行器或评分反馈。'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    root=parser.parse_args().input_dir;episodes=[audit(p.parent) for p in root.rglob('human_policy_io.jsonl')];assert episodes
    (root/'human_goal_action_scope.json').write_text(json.dumps({'status':'audited','episodes':episodes},ensure_ascii=False,indent=2))
    print(json.dumps([{'episode':e['episode'],'decision_counts':e['decision_counts']} for e in episodes],ensure_ascii=False))
