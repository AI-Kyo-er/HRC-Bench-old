import numpy as np

from hrc_pilot.human_training_teacher import ContactDemonstrationTeacher
from test_native_grounded_human import observation
from dataclasses import replace


def test_teacher_advances_only_after_real_release_support_and_dwell():
    targets=[{'object_id':'plate','destination':'personal'},{'object_id':'bowl','destination':'personal'}]
    teacher=ContactDemonstrationTeacher(targets)
    r={'objects':{'plate':[0,.3,.9],'bowl':[.1,0,.9]},'contacts':[
        {'geom1':'plate_g1','geom2':'table_collision'},
        {'geom1':'plate_g1','geom2':'human_left_finger_contact'}]}
    for _ in range(10):teacher.observe(r,{'personal':(0,.3,.9)})
    assert teacher.decision(observation())['object_id']=='plate'
    r['contacts']=r['contacts'][:1]
    for _ in range(4):teacher.observe(r,{'personal':(0,.3,.9)})
    assert teacher.decision(observation())['object_id']=='bowl'
    held=replace(observation(),human_execution={'object_measured_in_hand':'bowl'})
    assert teacher.decision(held)['intent']=='place'


def test_teacher_handles_release_without_a_new_invalid_place_or_grasp():
    teacher=ContactDemonstrationTeacher([{'object_id':'plate','destination':'personal'}])
    o=replace(observation(),human_execution={'object_measured_in_hand':None,'motor_phase':'grasp_retreat'})
    assert teacher.decision(o)['intent']=='release'
