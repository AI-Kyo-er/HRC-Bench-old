"""FactsWorld只验伙伴交还协议；不是物理错误恢复证据。"""
import copy
import unittest
from tests.test_structure_v5 import FactsWorld
from experiments.structure_handoff_v15.protocol import Episode,cases,candidates,reduce_history,effective_blue_returns
from experiments.structure_v11.protocol import candidates as old_candidates


class HandoffProtocol(unittest.TestCase):
    def episode(self,timing='during_child',reply='accepted',initial='left'):
        c=next(c for c in cases() if c['seed']==60 and c['timing']==timing and c['reply']==reply and c['initial_blue']==initial)
        return Episode(c,FactsWorld())

    def checked(self,ep):ep.act('stage_blue_neutral');ep.act('yield')

    def test_same_16_conditions_and_22_menu(self):
        self.assertEqual(len(cases()),16);self.assertEqual(candidates(),old_candidates());self.assertEqual(len(candidates()),22)

    def test_handoff_before_green_is_legal_zero_cost_and_preserves_pending(self):
        ep=self.episode();self.checked(ep);state=copy.deepcopy(ep.world.state());cost=copy.deepcopy(ep.cost)
        self.assertTrue(ep.partner_handoff()['valid']);self.assertEqual(ep.world.state(),state);self.assertEqual(ep.cost,cost)
        self.assertFalse(reduce_history(ep.history)['active']);self.assertIsNone(ep.world.regions['green']);self.assertFalse(ep.success())
        self.assertTrue(ep.act('place_blue_right')['valid']);self.assertTrue(ep.act('place_green_right')['success'])

    def test_handoff_preserves_done_green_and_restores_latest_acceptance(self):
        for timing in ('before_child','during_child'):
            for reply in ('accepted','rejected'):
                ep=self.episode(timing,reply);self.checked(ep);ep.act('place_green_right');before=copy.deepcopy(ep.world.state())
                self.assertTrue(ep.partner_handoff()['valid']);self.assertEqual(before,ep.world.state())
                goal='right' if reply=='accepted' else 'left'
                self.assertEqual(reduce_history(ep.history)['goals']['blue'],goal)
                self.assertEqual(effective_blue_returns(ep.observation()),[f'place_blue_{goal}',f'careful_blue_{goal}'])
                self.assertTrue(ep.world.at_goal('green','right'));self.assertFalse(ep.success())

    def test_unchecked_unreleased_and_repeated_handoff_never_ends_early(self):
        ep=self.episode();self.assertFalse(ep.partner_handoff()['valid']);self.assertTrue(reduce_history(ep.history)['active'])
        ep.act('stage_blue_neutral');self.assertFalse(ep.partner_handoff()['valid']);self.assertTrue(reduce_history(ep.history)['active'])
        ep.act('yield');ep.world.occupied=True
        self.assertFalse(ep.partner_handoff()['valid']);self.assertTrue(reduce_history(ep.history)['active'])
        ep.world.occupied=False;self.assertTrue(ep.partner_handoff()['valid']);before=copy.deepcopy(ep.world.state());state=reduce_history(ep.history)
        self.assertFalse(ep.partner_handoff()['valid']);self.assertEqual(before,ep.world.state());self.assertEqual(state,reduce_history(ep.history))

    def test_duplicate_robot_finish_rejected_but_early_manual_finish_retained(self):
        ep=self.episode();self.checked(ep);self.assertTrue(ep.act('finish_guidance')['valid'])
        self.assertFalse(ep.partner_handoff()['valid'])
        ep=self.episode();self.checked(ep);ep.partner_handoff();before=copy.deepcopy(ep.world.state())
        self.assertFalse(ep.act('finish_guidance')['valid']);self.assertEqual(before,ep.world.state())

    def test_event_no_target_and_immutable_public_input(self):
        ep=self.episode();self.checked(ep);ep.act('place_green_right');obs=ep.observation();ep.partner_handoff()
        event=ep.history[-1];self.assertEqual(set(event),{'kind','content'})
        for word in ('left','right','destination','goals'):self.assertNotIn(word,str(event))
        self.assertEqual(ep.history[:len(obs['history'])],obs['history'])
        self.assertEqual(ep.observation()['remaining_decisions'],9)

    def test_during_update_precedes_handoff_and_child_remains_neutral(self):
        ep=self.episode();ep.act('stage_blue_neutral');self.assertFalse(ep.update_injected)
        ep.act('yield');self.assertTrue(ep.update_injected);self.assertEqual(reduce_history(ep.history)['goals']['blue'],'neutral')
        ep.partner_handoff();kinds=[e['kind'] for e in ep.history]
        self.assertLess(kinds.index('proposal_reply'),kinds.index('partner_handoff'))

    def test_public_ledger_rejects_invalid_handoff_event(self):
        ep=self.episode()
        with self.assertRaises(ValueError):reduce_history(ep.history+[dict(kind='partner_handoff',content='尚未检查')])

    def test_actual_nested_contact_container_normalization_keeps_differences(self):
        import json
        from experiments.physical.run import ROOT
        from experiments.structure_handoff_v15.reference_audit import physical_equal,normalize_containers
        original=json.loads((ROOT/'results/structure_v11/raw/reference/B_update_before_child_accepted_left_60/summary.json').read_text())['finish_audit']['after']
        reconstructed=copy.deepcopy(original)
        self.assertTrue(reconstructed['contacts'])
        for c in reconstructed['contacts']:
            c['position_a']=tuple(c['position_a']);c['position_b']=tuple(c['position_b'])
        self.assertNotEqual(reconstructed,original);self.assertTrue(physical_equal(reconstructed,original))
        self.assertEqual(normalize_containers(reconstructed),original)
        reconstructed['contacts'][0]['contact_distance']+=1e-9
        self.assertFalse(physical_equal(reconstructed,original))


if __name__=='__main__':unittest.main()
