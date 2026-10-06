#!/usr/bin/env python3
"""描述双方实际接触抬起了哪些物体，不以语言声明认定操作者或因果。"""
import argparse
import json
from pathlib import Path


def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args();episodes=[]
    for path in sorted(args.input_dir.rglob('trace.jsonl')):
        trace=rows(path);metrics=json.loads((path.parent/'metrics.json').read_text());objects=[]
        for obj,initial in trace[0]['objects'].items():
            first={'robot':None,'human':None};peak=max(r['objects'][obj][2]-initial[2] for r in trace)
            for r in trace:
                if r['objects'][obj][2]-initial[2]<=.04:continue
                touch={'robot':[False,False],'human':[False,False]}
                for c in r['contacts']:
                    a,b=c['geom1'] or '',c['geom2'] or ''
                    if b.startswith(obj+'_'):a,b=b,a
                    if not a.startswith(obj+'_'):continue
                    touch['robot'][0]|=b.startswith('gripper0_finger1');touch['robot'][1]|=b.startswith('gripper0_finger2')
                    touch['human'][0]|=b=='human_left_finger_contact';touch['human'][1]|=b=='human_right_finger_contact'
                for role in first:
                    if all(touch[role]) and first[role] is None:first[role]=r['time_s']
            if peak>.005 or any(v is not None for v in first.values()):objects.append({'object_id':obj,'maximum_lift_m':peak,
                         'first_robot_bilateral_contact_lift_s':first['robot'],'first_human_bilateral_contact_lift_s':first['human']})
        episodes.append({'episode':str(path.parent),'robot_public_goal':metrics.get('robot_goal_spec'), 'objects':objects})
    assert episodes
    result={'status':'audited','episodes':episodes,'interpretation':'实际双指接触与抬高同时出现的见证，区分操作者和物品；不证明严格因果归属、理解或协商成功。'}
    (args.input_dir/'object_role_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
