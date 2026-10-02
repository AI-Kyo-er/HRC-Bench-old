"""新方向/事件/规范比较永久回归；动力学结果另由真实控制验收。"""
import copy
import unittest
from unittest.mock import patch
from experiments.structure_foundation_v20.world import distance,FoundationWorld,CONFIG,TRANSPORT
from experiments.structure_foundation_v20.run import cases
from experiments.structure_foundation_v20.canonical import physics,equal

class FoundationTests(unittest.TestCase):
    def test_fixed20_sequences_and_body_independence(self):
        self.assertEqual(len(cases('A')),4);self.assertEqual(len(cases('BCD')),16)
        self.assertEqual([sum(c['group']==g for c in cases('BCD')) for g in ('B','C','D')],[8,4,4])
        for c in cases('BCD'):
            if c['group']=='C':self.assertLess(c['commands'].index('presence_far'),c['commands'].index('green_right'));self.assertLess(c['commands'].index('presence_near'),c['commands'].index('red_left'))
    def test_profile_continuous_monotone_stable_and_fixed(self):
        for speed in (.04,.08):
            duration=.6/speed+.5;values=[distance(i/100,.6,speed,.5) for i in range(int(duration*100)+201)]
            self.assertEqual(values[0],0);self.assertEqual(values[-1],.6);self.assertTrue(all(a<=b for a,b in zip(values,values[1:])))
            self.assertAlmostEqual(distance(.5,.6,speed,.5),speed*.25);self.assertAlmostEqual(distance(duration-.5,.6,speed,.5),.6-speed*.25)
    def bare(self):
        w=FoundationWorld.__new__(FoundationWorld);w.client=0;w.partner=1;w.tick=200;w.delivery_event={'first_tick':123};w.delivery_start_tick=10;w.return_start_tick=None;w.return_origin=None;return w
    def test_return_preserves_delivery_history_current_origin(self):
        w=self.bare();old=copy.deepcopy(w.delivery_event)
        with patch('experiments.structure_foundation_v20.world.p.getJointState',return_value=(.003,0)):
            w.start_return();self.assertEqual(w.return_origin,.003);self.assertEqual(w.return_start_tick,200)
            with self.assertRaises(AssertionError):w.start_return()
        self.assertEqual(w.delivery_event,old);self.assertEqual(w.delivery_start_tick,10)
    def test_empty_carrier_not_payload_handoff(self):
        w=self.bare();w.return_start_tick=150
        with patch('experiments.structure_foundation_v20.world.p.getJointState',return_value=(.6,0)):
            for supported,relative,expected in ((False,[0,0,.028],False),(True,[0,.25,.028],False),(True,[0,0,.028],True)):
                w.support_facts=lambda body:dict(supported=supported,relative_position=relative,relative_speed=0,blue_speed=0)
                f=w.return_facts();self.assertTrue(f['carrier_returned']);self.assertEqual(f['payload_returned'],expected)
    def test_presence_no_carrier_reset_and_two_channels(self):
        w=self.bare();w.presence=9;w.presence_motion=None;w.partner_target=.1
        with patch('experiments.structure_foundation_v20.world.p.getJointState',return_value=(.45,0)):
            w.start_presence('far')
            with self.assertRaises(AssertionError):w.start_presence('near')
        self.assertEqual(w.partner_target,.1);self.assertEqual(w.delivery_start_tick,10);self.assertEqual(w.presence_motion['target'],1.05)
    def test_canonical_contacts_container_only_and_real_difference(self):
        from experiments.sustained_model_v19.run import initial_records
        # 真实旧trace字段扩展新body；新contacts仍保留完整距离/位置/精度。
        import json
        from experiments.physical.run import ROOT
        s=json.loads((ROOT/'results/sustained_activity_v18/raw/reference/Reference_left_none_ready_public_ledger_parallel_100/decisions.json').read_text())[0]['before_state']
        s.update(inspection_facts=None,presence=None,presence_motion=None,presence_events=[],return_start_tick=None,return_origin=None,return_event=None,payload_return_event=None,return_facts=None)
        other=copy.deepcopy(s);other['contacts'][0]['position_a']=tuple(other['contacts'][0]['position_a']);self.assertTrue(equal(s,other))
        other['contacts'][0]['contact_distance']+=1e-9;self.assertFalse(equal(s,other))
        wrong=copy.deepcopy(s);wrong['unclassified']='extra'
        with self.assertRaises(AssertionError):physics(wrong)

if __name__=='__main__':unittest.main()
