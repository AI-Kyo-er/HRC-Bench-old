"""永久协议/事件反例：纯公开事实替身，不作为物理安全证据。"""
import copy
import unittest
from experiments.transport_cycle_v22.cycle import CycleLedger
from experiments.transport_cycle_v22.world import CycleWorld
from experiments.transport_cycle_v22.canonical import content_equal


def facts(tick=240,near=False,far=True,payload=True):
    return dict(tick=tick,joint=0.0 if near else 0.6,velocity=0.0,near=near,far=far,payload_stable=payload,profile_finished=True)


class CycleTests(unittest.TestCase):
    def test_loaded_multicycle_retains_history(self):
        c=CycleLedger();self.assertEqual(c.request('forward',facts())['decision'],'accepted')
        c.sample(facts(4000,True,False));old=copy.deepcopy(c.events)
        self.assertEqual(c.request('return',facts(4000,True,False))['leg_id'],2)
        c.sample(facts(7800));c.request('forward',facts(7800));c.sample(facts(11600,True,False))
        self.assertEqual([l['id'] for l in c.legs],[1,2,3]);self.assertEqual(c.events[:2],old)
        self.assertEqual([e['leg_id'] for e in c.events],[1,1,2,2,3,3])

    def test_reject_not_queued_and_duplicate_no_restart(self):
        c=CycleLedger();c.request('forward',facts());leg=copy.deepcopy(c.legs[0])
        self.assertEqual(c.request('forward',facts(1240,False,False))['decision'],'already_running')
        self.assertEqual(c.request('return',facts(1240,False,False))['decision'],'rejected_motion')
        self.assertEqual(c.legs[0],leg);c.sample(facts(4000,True,False));c.sample(facts(4480,True,False))
        self.assertEqual(len(c.legs),1);self.assertIsNone(c.active)

    def test_wrong_endpoint_rejected(self):
        c=CycleLedger();self.assertEqual(c.request('return',facts())['decision'],'rejected_endpoint')
        self.assertEqual(c.request('forward',facts(240,True,False))['decision'],'rejected_endpoint')
        self.assertEqual(c.legs,[])

    def test_empty_does_not_inherit_payload(self):
        c=CycleLedger();c.request('forward',facts());c.sample(facts(4000,True,False))
        c.request('return',facts(4000,True,False,False));c.sample(facts(7800,False,True,False))
        c.request('forward',facts(7800,False,True,False));c.sample(facts(11600,True,False,False))
        c.sample(facts(12000,True,False,True))
        self.assertEqual(len([e for e in c.events if e['kind']=='payload_arrived']),1)
        self.assertIsNone(c.legs[-1]['payload_event']);self.assertTrue(c.legs[0]['payload_event'])

    def test_profile_not_finished_cannot_emit(self):
        c=CycleLedger();c.request('forward',facts());f=facts(300,True,False);f['profile_finished']=False;c.sample(f)
        self.assertEqual(c.events,[]);self.assertEqual(c.active,1)

    def test_payload_must_satisfy_current_facts(self):
        c=CycleLedger();c.request('forward',facts());c.sample(facts(4000,True,False,False))
        self.assertEqual(c.active,1);self.assertIsNone(c.legs[0]['payload_event'])
        c.sample(facts(4001,True,False,True));self.assertEqual(c.legs[0]['payload_event']['first_tick'],4001)

    def test_snapshot_no_alias_and_canonical_nested_contact(self):
        c=CycleLedger();c.request('forward',facts());s=c.snapshot();s['legs'][0]['start_tick']=-1
        self.assertEqual(c.legs[0]['start_tick'],240)
        a={'contacts':[{'position_a':(0.,1.,2.),'contact_distance':-0.001}]}
        b={'contacts':[{'position_a':[0.,1.,2.],'contact_distance':-0.001}]}
        self.assertTrue(content_equal(a,b));b['contacts'][0]['contact_distance']=0.001;self.assertFalse(content_equal(a,b))

    def test_remote_blue_source_refused_without_execution(self):
        class Fake:
            cycle=CycleLedger()
            def carrier_facts(self):return dict(near=False,payload_stable=True)
            def at_goal(self,item,region):return False
        r=CycleWorld.pick_place(Fake(),'blue','left');self.assertFalse(r['physical_attempt'])
        self.assertFalse(r['success'])

    def test_reload_requires_near_actual_carrier(self):
        class Fake:
            cycle=CycleLedger()
            def carrier_facts(self):return dict(near=False,payload_stable=False)
            def at_goal(self,item,region):return region=='inspection'
        r=CycleWorld.pick_place(Fake(),'blue','carrier');self.assertFalse(r['physical_attempt'])
        self.assertFalse(r['success'])

    def test_source_motion_refused_without_goal_or_role(self):
        class Fake:
            cycle=CycleLedger()
            def carrier_facts(self):return dict(near=True,payload_stable=False)
            def at_goal(self,item,region):return True
        f=Fake();f.cycle=CycleLedger();f.cycle.request('return',facts(240,True,False))
        r=CycleWorld.pick_place(f,'blue','carrier');self.assertFalse(r['physical_attempt'])


if __name__=='__main__':unittest.main()
