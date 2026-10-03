"""公开事务/服务/预算反例，仅替身协议，不代替48物理。"""
import copy
import unittest
from tests.test_sustained_combination_v23 import FakeWorld as ParentFakeWorld
from experiments.dual_goal_v25.protocol import Episode,public_ledger,terminal_score,candidates
from experiments.dual_goal_v25.run import cases,requirement
from experiments.dual_goal_v25.audit import audit_ledger


class FakeWorld(ParentFakeWorld):
    def carrier_facts(self):return self.state()['current_carrier_facts']


class DualGoalTests(unittest.TestCase):
    def make(self,initial='left',mode='relation',rule='same',reply='accepted',timing='after_handoff'):
        w=FakeWorld();green=dict(mode=mode,relation=rule) if mode=='relation' else dict(mode=mode,destination=rule)
        return w,Episode(w,initial,green,reply,timing)

    def test_unanswered_proposal_not_effective(self):
        w,e=self.make();e._append(dict(kind='proposal',proposal_id='x',binding='outer_blue',destination='right'))
        l=public_ledger(e.history);self.assertEqual(l['goals']['blue'],'left');self.assertTrue(l['confirmation_pending'])

    def test_rejection_closes_but_preserves(self):
        for initial in ('left','right'):
            w,e=self.make(initial=initial,reply='rejected',timing='before_check');l=public_ledger(e.history)
            self.assertEqual(l['goals']['blue'],initial);self.assertEqual(l['goals']['green'],initial);self.assertFalse(l['confirmation_pending'])

    def test_relation_all_polarities(self):
        for initial in ('left','right'):
            for q in ('same','opposite'):
                w,e=self.make(initial=initial,rule=q,timing='before_check');l=public_ledger(e.history)
                expected='right' if initial=='left' else 'left'
                self.assertEqual(l['goals']['blue'],expected)
                self.assertEqual(l['goals']['green'],expected if q=='same' else initial)

    def test_direct_does_not_link(self):
        w,e=self.make(mode='direct',rule='left',timing='before_check');l=public_ledger(e.history)
        self.assertEqual(l['goals']['blue'],'right');self.assertEqual(l['goals']['green'],'left')

    def test_direct_does_not_expose_pair_relation(self):
        w,e=self.make(mode='direct',rule='right');a=next(x for x in e.history if x['kind']=='accepted_activity')
        self.assertEqual(a['green_requirement'],dict(mode='direct',destination='right'))
        self.assertNotIn('q',e.observation());self.assertNotIn('case',e.observation());self.assertNotIn('score',e.observation())

    def test_before_first_observation_is_closed(self):
        w,e=self.make(timing='before_check');obs=e.observation()
        self.assertFalse(public_ledger(obs['history'])['confirmation_pending'])
        self.assertTrue(all(x['actual_tick']==x['observed_tick']==240 for x in obs['history']))

    def test_handoff_generates_at_tick_not_observation(self):
        w,e=self.make();e.act('request_check');w.simulate(300)
        self.assertTrue(e.service.completed);self.assertTrue(public_ledger(e.history)['confirmation_pending'])
        pending=[x for x in e.pending_events if x['kind'] in ('proposal','proposal_reply')]
        self.assertEqual([x['actual_tick'] for x in pending],[480,480])
        obs=e.observation();p=[x for x in obs['history'] if x['kind'] in ('proposal','proposal_reply')]
        self.assertTrue(all(x['actual_tick']==480 and x['observed_tick']==540 for x in p));self.assertEqual(public_ledger(obs['history'])['goals']['blue'],'right')
        w.simulate(240);e.observation();self.assertEqual(sum(x['kind']=='proposal' for x in e.history),1)

    def test_declare_does_not_generate_future_and_is_immutable(self):
        w,e=self.make();e.act('request_check');tick=w.tick;e.act('declare_done')
        self.assertEqual(w.tick,tick);self.assertTrue(public_ledger(e.history)['confirmation_pending']);self.assertFalse(e.service.completed)
        h=copy.deepcopy(e.history);c=copy.deepcopy(e.cost)
        with self.assertRaises(RuntimeError):e.act('yield')
        self.assertEqual(e.history,h);self.assertEqual(e.cost,c);self.assertEqual(w.tick,tick)
        self.assertFalse(terminal_score(e,w.state())['task_success'])

    def test_wrong_target_and_pending_do_not_filter_physics(self):
        w,e=self.make();e.act('place_blue_right');self.assertIn(('pick','blue','right'),w.calls)
        self.assertTrue(public_ledger(e.history)['confirmation_pending'])

    def test_update_during_skill_not_known_at_start(self):
        w,e=self.make();e.act('request_check');before=public_ledger(e.observation()['history'])
        original=w.pick_place
        def delayed(item,target,route):w.simulate(300);return original(item,target,route)
        w.pick_place=delayed;e.act('careful_green_left');after=public_ledger(e.history)
        self.assertEqual(before['goals']['green'],'left');self.assertEqual(after['goals']['green'],'right')
        self.assertIn('left',w.regions['green']);self.assertEqual(w.tick,540)

    def test_local_prefix_cost_not_reset(self):
        w,e=self.make(reply='rejected',timing='before_check');e.act('request_check');w.simulate(240);e.observation()
        w.far=True;w.near=False;e.cost['decisions']=9;history=copy.deepcopy(e.history);e.begin_local()
        self.assertEqual(e.cost['decisions'],9);self.assertEqual(e.budget_origin,9);self.assertEqual(e.observation()['remaining_decisions'],12)
        self.assertEqual(e.history[:-1],history);e.act(None);self.assertEqual(e.observation()['remaining_decisions'],11)

    def test_initial_observation_no_alias_future(self):
        w,e=self.make();obs=e.observation();obs['history'].clear()
        self.assertTrue(e.history);self.assertFalse(any(x['kind']=='proposal_reply' for x in e.history));self.assertEqual(len(candidates()),12)

    def test_reply_requires_bound_pending_proposal(self):
        w,e=self.make();e._append(dict(kind='proposal_reply',proposal_id='missing',decision='accept'))
        with self.assertRaises(ValueError):public_ledger(e.history)

    def test_independent_history_reducer_same_without_private_case(self):
        for c in cases('reference'):
            w=FakeWorld();e=Episode(w,c['initial_blue'],requirement(c),c['reply'],c['timing'])
            self.assertEqual(audit_ledger(e.history),public_ledger(e.history))
            if c['timing']=='after_handoff':e.act('request_check');w.simulate(240);e.observation()
            self.assertEqual(audit_ledger(e.history),public_ledger(e.history))

    def test_complete_fixed_counts_no_selection(self):
        self.assertEqual([len(cases(s)) for s in ('control','reference','local')],[8,32,8])
        self.assertEqual(sum(c.get('control')=='U4' for c in cases('control')),2)
        self.assertEqual(len({(c['initial_blue'],c['reply'],c['q'],c['expression'],c['timing']) for c in cases('reference')}),32)


if __name__=='__main__':unittest.main()
