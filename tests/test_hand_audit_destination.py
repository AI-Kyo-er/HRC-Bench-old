import importlib.util
import json
from pathlib import Path
import sys


def test_autonomous_table_release_uses_actual_selected_destination(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('hand_audit',Path(__file__).resolve().parents[1]/'scripts/verify_native_hand.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    ep=tmp_path/'episode';ep.mkdir();(ep/'metrics.json').write_text('{}')
    trace=[]
    for i in range(4):
        contacts=[]
        if i in (1,2):contacts=[{'geom1':'plate_1_collision','geom2':'human_'+side+'_finger_contact'} for side in ('left','right')]
        if i==3:contacts=[{'geom1':'plate_1_collision','geom2':'table_collision'}]
        trace.append({'time_s':i*.05,'physics_time_s':10+i*.05,'objects':{'plate_1':[0,0,.06 if i in (1,2) else 0]},'contacts':contacts})
    def write(name,rows):
        (ep/name).write_text(''.join(json.dumps(r)+'\n' for r in rows))
    write('trace.jsonl',trace)
    write('human_control.jsonl',[{'object_id':'plate_1','actual_velocity':[.1,0,0],'human_object_pose_writes':0}])
    write('human_policy_io.jsonl',[{'parsed_decision':{'intent':'place','object_id':'plate_1','destination':'plate_1_personal'}}])
    monkeypatch.setattr(sys,'argv',['verify_native_hand.py','--input-dir',str(tmp_path)])
    audit.main()
    result=json.loads((tmp_path/'hand_verification.json').read_text())['episodes'][0]
    assert result['destination']=='plate_1_personal'
    assert result['first_released_support_contact_s']==trace[-1]['time_s']
