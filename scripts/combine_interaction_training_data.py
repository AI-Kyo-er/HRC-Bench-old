#!/usr/bin/env python3
"""同stem合并数据，并从原始物理记录补充v2接触与短历史，不改标签。"""
import argparse,json
from pathlib import Path
from dataclasses import replace

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.interactive_human import InteractiveArticulatedHuman


def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inputs',nargs='+',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir
    if out.exists():parser.error('输出需为新目录')
    out.mkdir(parents=True);(out/'episodes').mkdir();verification=[];summary=[];count=0
    for root in args.inputs:
        audit=read(root/'training_data_verification.json');assert audit['status']=='verified' and read(root/'video_verification.json')['status']=='verified'
        verification.extend(audit['episodes']);summary.extend(read(root/'summary.json')['episodes'])
        for ep in (root/'episodes').iterdir():
            (out/'episodes'/ep.name).symlink_to(ep.resolve())
            trace=rows(ep/'trace.jsonl');bytime={r['time_s']:r for r in trace};metric=read(ep/'metrics.json');split=metric['split']
            names=[t['object_id'] for t in metric['targets']]
            formatter=InteractiveArticulatedHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),autonomous_context='shared_meal',preferred_personal_objects=names,model_path=Path('/unused'),persona_id='independent')
            formatter.reset(0);history=[]
            folder=out/'samples'/split;folder.mkdir(parents=True,exist_ok=True)
            for sourcepath in sorted((root/'samples'/split).glob(ep.name+'__step*.source.json')):
                source=read(sourcepath);title,value=source['public_input'].split('\n',1);public=json.loads(value)
                r=bytime[source['time_s']];measured=r['human_execution'];contact=measured.get('hand_contact_report',{})
                public['hand_contact_summary']={'source':'current_collision_geometry_no_goal_or_force_inference',
                    'contact_with_other_agent':bool(contact.get('contact_with_other_agent',False)),
                    'contact_geoms':measured.get('hand_contact_geoms',[])[:12]}
                for key in ['body_xy','body_target_xy','body_remaining_distance_m','fingertip_target_xyz']:
                    if key in measured:public['your_measured_execution'][key]=measured[key]
                public['recent_measured_world_history']=history[-2:]
                history.append({'time_s':source['time_s'],'fingertip_xyz':r['human_hand_position'],
                    'fingertip_remaining_distance_m':measured.get('fingertip_remaining_distance_m'),
                    'phase':measured['motor_phase'],'object_measured_in_hand':measured.get('object_measured_in_hand'),
                    'contact_with_other_agent':bool(contact.get('contact_with_other_agent',False))})
                if 'move_hand' not in public['action_interface']['intents']:public['action_interface']['intents'].append('move_hand')
                public['action_interface'].update(hand_workspace_xyz_min=[-.7,-.4,.98],hand_workspace_xyz_max=[.7,.85,1.45])
                public['observation_projection']='compact_contact_history_v2';source['public_input']=title+'\n'+json.dumps(public,ensure_ascii=False,separators=(',',':'))
                source['system_prompt']=formatter._system_prompt();source['raw_source_file']=str(sourcepath.resolve())
                (folder/sourcepath.name).write_text(json.dumps(source,ensure_ascii=False,indent=2))
                target=sourcepath.with_name(sourcepath.name.replace('.source.json','.target.json'))
                (folder/target.name).symlink_to(target.resolve());count+=1
    (out/'training_data_verification.json').write_text(json.dumps({'status':'verified','episodes':verification,'qualified_episodes':sum(e['supervision_eligible'] for e in verification)},ensure_ascii=False,indent=2))
    (out/'summary.json').write_text(json.dumps({'episodes':summary},ensure_ascii=False,indent=2))
    (out/'provenance.json').write_text(json.dumps({'inputs':[str(p.resolve()) for p in args.inputs],'sample_pairs':count,
        'pair_rule':'same stem .source.json/.target.json; episode before __step','projection':'compact_contact_history_v2',
        'reprojection':'current contacts and previous two actual decision-time measurements from saved raw trace; labels unchanged'},ensure_ascii=False,indent=2))
    print('sample_pairs',count,'qualified_episodes',sum(e['supervision_eligible'] for e in verification))


if __name__=='__main__':main()
