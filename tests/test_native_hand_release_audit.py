import json

from scripts.verify_native_hand import verify


def test_table_support_before_grasp_is_not_a_release_witness(tmp_path):
    obj='plate_1'
    contacts=[{'geom1':obj+'_g1','geom2':'table_collision'}]
    fingers=[{'geom1':obj+'_g1','geom2':'human_'+side+'_finger_contact'} for side in ['left','right']]
    trace=[{'time_s':i*.05,'physics_time_s':i*.05,'objects':{obj:[0.,0.,z]},'contacts':c}
           for i,(z,c) in enumerate([(.91,contacts),(.97,fingers),(.91,contacts)])]
    (tmp_path/'trace.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in trace))
    (tmp_path/'human_control.jsonl').write_text(json.dumps({'actual_velocity':[0.,0.,0.],'human_object_pose_writes':0})+'\n')
    (tmp_path/'metrics.json').write_text(json.dumps({'object_id':obj,'destination':'plate_1_personal'}))
    result=verify(tmp_path)
    assert result['first_bilateral_contact_lift_s']==.05
    assert result['first_released_support_contact_s']==.1
