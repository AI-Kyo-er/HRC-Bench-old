"""永久协议/服务替身反例，不冒充真实物理证据。"""
import copy
import types
import unittest
from experiments.sustained_combination_v23.protocol import Episode,public_ledger,candidates,reference,terminal_score
from experiments.sustained_structure_v21.service import InspectionService
from experiments.transport_cycle_v22.cycle import CycleLedger


class FakeWorld:
    def __init__(self):
        self.tick=240;self.cycle=CycleLedger();self.step_callback=None;self.calls=[];self.presence_motion=None
        self.regions={'red':[],'blue':['inspection'],'green':[]}
        self.near=True;self.far=False;self.payload=False
    def start_presence(self,dest):self.calls.append(('presence',dest));return dict(destination=dest,start_tick=self.tick)
    def public_inspection_sample(self):
        return dict(tick=self.tick,presence=dict(near=self.near,far=self.far),presence_moving=False,
                    inspection=dict(satisfied='inspection' in self.regions['blue']),robot_blue_contact=False)
    def at_goal(self,item,target):return target in self.regions[item]
    def state(self):
        objects={i:dict(position=[.59+.06*('red','blue','green').index(i),-.25 if 'left' in self.regions[i] else .25,.032],velocity=[0,0,0]) for i in self.regions}
        return dict(objects=objects,partner_position=[.65,0,.045],inspection_facts=dict(satisfied='inspection' in self.regions['blue']),
            presence=dict(near=self.near,far=self.far),presence_motion=self.presence_motion,cycle=self.cycle.snapshot(),
            current_carrier_facts=dict(near=self.near,far=self.far,payload_stable=self.payload))
    def pick_place(self,item,target,route):
        self.calls.append(('pick',item,target));self.regions[item]=[target]
        return dict(success=True,physical_attempt=True,reason='替身')
    def request_motion(self,direction):
        return self.cycle.request(direction,dict(tick=self.tick,joint=0 if self.near else .6,near=self.near,far=self.far,payload_stable=self.payload))
    def simulate(self,ticks):
        for _ in range(ticks):
            self.tick+=1
            if self.step_callback:self.step_callback(self.public_inspection_sample())


class CombinationTests(unittest.TestCase):
    def test_role_accept_does_not_waive_check_or_change_goals(self):
        w=FakeWorld();e=Episode(w,'right','accepted','stay');e.act('request_check');l=public_ledger(e.history)
        self.assertEqual(l['blue_role'],'partner_return');self.assertTrue(l['inspection_required']);self.assertTrue(l['child_active']);self.assertEqual(l['goals']['blue'],'right')
        self.assertFalse(e.service.completed);self.assertFalse(terminal_score(e,w.state())['task_success'])

    def test_rejection_preserves_robot_and_no_future_reply(self):
        w=FakeWorld();e=Episode(w,'left','rejected','stay')
        self.assertFalse(any(x['kind']=='proposal_reply' for x in e.observation()['history']))
        e.act('request_check');self.assertEqual(public_ledger(e.history)['blue_role'],'robot')
        proposal=next(i for i,v in enumerate(e.history) if v['kind']=='proposal');check=next(i for i,v in enumerate(e.history) if v['kind']=='check_request_reply')
        self.assertGreater(proposal,check)

    def test_wrong_role_and_unfinished_check_do_not_filter_physics(self):
        w=FakeWorld();e=Episode(w,'left','accepted','stay');e.act('request_check')
        e.act('place_blue_right');self.assertIn(('pick','blue','right'),w.calls)
        self.assertFalse(e.service.completed)

    def test_role_proposal_only_once_after_withdraw_reaccept(self):
        w=FakeWorld();e=Episode(w,'left','accepted','withdraw');e.act('request_check');e.service.committed=False
        e.act('request_check');self.assertEqual(sum(v['kind']=='proposal' for v in e.history),1)
        self.assertEqual(e.service.acceptances,2)

    def test_snapshot_no_alias_and_menu_same(self):
        w=FakeWorld();a=Episode(w,'left','accepted','stay');b=Episode(FakeWorld(),'right','rejected','withdraw')
        obs=a.observation();obs['history'].clear();self.assertTrue(a.history)
        self.assertEqual(obs['candidates'],b.observation()['candidates']);self.assertEqual(len(candidates()),12)
        self.assertNotIn('score',obs);self.assertNotIn('current_goals',obs)

    def test_old_return_is_not_current_payload_or_latest_leg(self):
        w=FakeWorld();e=Episode(w,'left','accepted','stay');e.act('request_check');e.service.completed=True;e.service.committed=False
        e._append(dict(kind='partner_check_handoff',qualified_ticks=240));w.near=False;w.far=True;w.payload=True
        w.cycle.legs=[dict(direction='return',payload_event={'first_tick':1}),dict(direction='forward',payload_event={'first_tick':2})]
        self.assertFalse(terminal_score(e,w.state())['facts']['blue_role_completed'])
        w.cycle.legs=[dict(direction='return',payload_event={'first_tick':1})];w.payload=False
        self.assertFalse(terminal_score(e,w.state())['facts']['blue_role_completed'])

    def test_robot_role_still_requires_actual_far(self):
        w=FakeWorld();e=Episode(w,'left','rejected','stay');w.regions['red']=['left'];w.regions['green']=['right'];w.regions['blue']=['left']
        e.service.completed=True;e.termination_reason='declared_done'
        score=terminal_score(e,w.state());self.assertTrue(score['facts']['blue_role_completed']);self.assertFalse(score['facts']['carrier_current_far']);self.assertFalse(score['task_success'])

    def test_declaration_really_terminal_and_immutable(self):
        w=FakeWorld();e=Episode(w,'left','accepted','stay');e.act('declare_done');before=copy.deepcopy((w.tick,e.history,e.cost,e.service.snapshot()))
        with self.assertRaises(RuntimeError):e.act('yield')
        self.assertEqual((w.tick,e.history,e.cost,e.service.snapshot()),before)

    def test_red_first_overlap_from_public_state(self):
        w=FakeWorld();e=Episode(w,'left','accepted','stay');w.near=False;w.far=True;e.act('request_transport')
        self.assertEqual(reference(e.observation()),'careful_red_left')

    def test_withdraw_preserves_progress_and_needs_request(self):
        events=[];s=InspectionService('withdraw',events.append,lambda d:dict(destination=d))
        def f(t,near=True,far=False):return dict(tick=t,presence=dict(near=near,far=far),presence_moving=False,inspection=dict(satisfied=True),robot_blue_contact=False)
        s.request(f(0))
        for t in range(1,61):s.step(f(t))
        self.assertFalse(s.committed);self.assertEqual(s.qualified_ticks,60)
        for t in range(61,64):s.step(f(t,False,True))
        self.assertEqual(s.qualified_ticks,60);s.request(f(64))
        self.assertTrue(s.committed);self.assertEqual(s.qualified_ticks,60)

    def test_check_handoff_preserves_latest_role(self):
        w=FakeWorld();e=Episode(w,'right','accepted','stay');e.act('request_check');e.act('yield');l=public_ledger(e.history)
        self.assertTrue(l['check_completed']);self.assertFalse(l['child_active']);self.assertEqual(l['blue_role'],'partner_return');self.assertEqual(l['goals']['blue'],'right')

    def test_reference_waits_for_current_movement_not_historical_arrival(self):
        w=FakeWorld();e=Episode(w,'left','accepted','stay');w.regions['red']=['left'];w.cycle.active=1
        self.assertEqual(reference(e.observation()),'yield')


if __name__=='__main__':unittest.main()
