"""公开事件/终止/来源前提的事实替身回归；非真实物理控制。"""
import copy
import unittest
from tests.test_responsive_transport_v16 import ResourceFacts
from experiments.sustained_activity_v18.protocol import Episode,candidates,reference,public_ledger
from experiments.sustained_activity_v18.run import cases,terminal_score

class Facts(ResourceFacts):
    def delivery_facts(self):return {'satisfied':self.delivery_event is not None and not self.regions.get('blue')}
    def state(self):
        state=super().state()
        state['objects']={i:dict(position=[.42, .16, .023] if self.regions[i] is None else [.65,-.25 if self.regions[i]=='left' else .25,.036],velocity=[0,0,0]) for i in self.regions}
        return state

class SustainedTests(unittest.TestCase):
    def episode(self,status='ready',target='left',update='none'):return Episode(Facts(status),target,update)
    def complete(self,e,target='left'):
        for action in ('request_transport','careful_red_left','yield',f'place_blue_{target}','declare_done'):e.act(action)
    def test_fixed56_and_six_menu(self):
        self.assertEqual([len(cases(s)) for s in ('recovery','negative','reference')],[4,4,48]);self.assertEqual(len(candidates()),6)
    def test_no_hidden_red_prefix_or_future_state(self):
        e=self.episode('temporarily_busy');self.assertEqual(e.world.pick_calls,0);self.assertFalse(e.world.at_goal('red','left'))
        o=e.observation();self.assertIsNone(o['partner_availability']['ready_event'])
        for k in ('case','seed','policy','current_goal','done_under_goals','score','success'):self.assertNotIn(k,o)
    def test_public_update_accepted_rejected_and_no_update(self):
        for initial in ('left','right'):
            for update in ('none','accepted','rejected'):
                e=self.episode(target=initial,update=update);t=('right' if initial=='left' else 'left') if update=='accepted' else initial
                self.assertEqual(public_ledger(e.history)['goals']['blue'],t)
    def test_reject_ready_retry_duplicate_no_reset(self):
        e=self.episode('temporarily_busy');e.act('request_transport');self.assertIsNone(e.world.delivery_start_tick);e.act('careful_red_left')
        self.assertTrue(e.world.at_goal('red','left'));e.act('request_transport');start=e.world.delivery_start_tick;before=copy.deepcopy(e.world.state());e.act('request_transport')
        self.assertEqual(start,e.world.delivery_start_tick);self.assertEqual(before,e.world.state());self.assertEqual(e.world.start_calls,1)
    def test_yield_branches_no_auto_transport(self):
        for status in ('ready','temporarily_busy'):
            e=self.episode(status);e.act('yield');self.assertIsNone(e.world.delivery_start_tick);self.assertEqual(e.world.start_calls,0)
        e=self.episode();e.act('request_transport');e.act('yield');self.assertIsNotNone(e.world.delivery_event)
    def test_blue_requires_actual_delivery_and_wrong_goal_executes(self):
        e=self.episode();self.assertFalse(e.act('place_blue_right')['valid']);self.assertEqual(e.world.pick_calls,0)
        e.act('request_transport');e.act('yield');r=e.act('place_blue_right');self.assertTrue(r['execution']['success']);self.assertNotIn('left',r['feedback']);self.assertNotIn('success',r)
    def test_same_region_noop_and_cross_region_recovery(self):
        e=self.episode();e.act('request_transport');e.act('yield');e.act('place_blue_right');before=copy.deepcopy(e.world.state());r=e.act('place_blue_right')
        self.assertTrue(r['no_op']);self.assertEqual(before,e.world.state());e.act('place_blue_left');self.assertTrue(e.world.at_goal('blue','left'))
    def test_early_done_terminates_and_not_corrected(self):
        e=self.episode();r=e.act('declare_done');self.assertTrue(r['valid']);self.assertTrue(e.terminated);self.assertNotIn('success',r);self.assertFalse(terminal_score(e,e.world)['goal_compliant'])
        old=copy.deepcopy((e.history,e.world.state(),e.cost))
        with self.assertRaises(RuntimeError):e.act('request_transport')
        self.assertEqual(old,(e.history,e.world.state(),e.cost))
    def test_wrong_and_correct_done_are_both_allowed(self):
        for actual,expected in (('left',True),('right',False)):
            e=self.episode();self.complete(e,actual);self.assertEqual(e.termination_reason,'declared_done');self.assertEqual(terminal_score(e,e.world)['goal_compliant'],expected)
    def test_immutable_snapshot_and_baseline_only_public(self):
        e=self.episode('temporarily_busy',update='accepted');o=e.observation();self.assertEqual(reference(o,'public_ledger_parallel'),'yield');self.assertEqual(reference(o,'conservative_serial'),'careful_red_left')
        e.act('careful_red_left');self.assertEqual(e.history[:len(o['history'])],o['history']);self.assertFalse('left' in o['physical_placements']['red'])
    def test_budget_ends_without_automatic_success(self):
        e=self.episode();e.step_budget=2;e.act('yield');e.act('yield');self.assertEqual(e.termination_reason,'budget_exhausted')
        with self.assertRaises(AssertionError):terminal_score(self.episode(),Facts('ready'))

if __name__=='__main__':unittest.main()
