import numpy as np

from hrc_pilot.libero_native import perceived_object_contacts
from hrc_pilot.native_video_frame import compose_runtime_views


def test_simultaneous_runtime_cameras_keep_policy_orientation_and_wide_pixels():
    wide=np.full((480,640,3),33,np.uint8)
    exterior=np.zeros((256,256,3),np.uint8);exterior[0,0]=[12,34,56]
    wrist=np.full((256,256,3),99,np.uint8)
    output=compose_runtime_views(wide,{'agentview_image':exterior,'robot0_eye_in_hand_image':wrist},'wide_and_policy')
    assert output.shape==(512,896,3)
    np.testing.assert_array_equal(output[100,100],wide[84,100])
    np.testing.assert_array_equal(output[255,895],exterior[0,0])
    np.testing.assert_array_equal(output[450,850],wrist[0,0])


def test_contact_perception_exposes_entities_without_evaluator_completion():
    measured=perceived_object_contacts({'objects':{'food':[], 'bowl':[]},'contacts':[
        {'geom1':'food_g1','geom2':'bowl_g2'}, {'geom1':'gripper0_finger','geom2':'food_g1'},
        {'geom1':'bowl_g3','geom2':'table_collision'}]})
    assert measured['food']=={'contact_entities':['bowl'],'robot_hand_contact':True,'human_hand_contact':False}
    assert measured['bowl']['contact_entities']==['food','table']
