"""dev1几何间隙及反向事件回归，非安全证明。"""
import copy
import unittest
from unittest.mock import patch
from experiments.structure_foundation_v20.world_v1 import CONFIG,FoundationWorld,distance

class WiderFoundationTests(unittest.TestCase):
    def test_only_inspection_y_geometry_changes(self):
        from experiments.structure_foundation_v20.world import CONFIG as old
        new=copy.deepcopy(CONFIG);self.assertEqual(new.pop('inspection_wall_y'),.085);new['version']=old['version'];new['inspection_half_extents'][1]=.06;self.assertEqual(new,old)
        self.assertGreater(.16-.022-CONFIG['inspection_half_extents'][1],.05)
    def test_profile_fixed_and_return_not_second_delivery(self):
        self.assertEqual(distance(0,.6,.04,.5),0);self.assertEqual(distance(16,.6,.04,.5),.6)
        w=FoundationWorld.__new__(FoundationWorld);w.client=0;w.partner=1;w.tick=200;w.delivery_start_tick=30;w.delivery_event={'first_tick':190};w.return_start_tick=None
        with patch('experiments.structure_foundation_v20.world_v1.p.getJointState',return_value=(.002,0)):w.start_return()
        self.assertEqual(w.delivery_event,{'first_tick':190});self.assertEqual(w.delivery_start_tick,30);self.assertEqual(w.return_origin,.002)
    def test_empty_return_current_support_required(self):
        w=FoundationWorld.__new__(FoundationWorld);w.client=0;w.partner=1;w.return_start_tick=20
        w.support_facts=lambda body:dict(supported=False,relative_position=[0,0,.028],relative_speed=0,blue_speed=0)
        with patch('experiments.structure_foundation_v20.world_v1.p.getJointState',return_value=(.6,0)):
            self.assertTrue(w.return_facts()['carrier_returned']);self.assertFalse(w.return_facts()['payload_returned'])
    def test_presence_independent_target(self):
        w=FoundationWorld.__new__(FoundationWorld);w.presence=8;w.client=0;w.tick=200;w.presence_motion=None;w.partner_target=.13
        with patch('experiments.structure_foundation_v20.world_v1.p.getJointState',return_value=(.45,0)):w.start_presence('far')
        self.assertEqual(w.partner_target,.13);self.assertEqual(w.presence_motion['target'],1.05)

if __name__=='__main__':unittest.main()
