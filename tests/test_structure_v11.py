"""FactsWorld替身只验协议，不代表真实物理更新/错误恢复轨迹。"""
import copy
import unittest

from tests.test_structure_v5 import FactsWorld
from experiments.structure_v11.protocol import Episode,cases,candidates,reduce_history,update_events,reference,effective_blue_returns


class OuterUpdate(unittest.TestCase):
    def episode(self,timing='during_child',reply='accepted',initial='left'):
        case=next(c for c in cases() if c['timing']==timing and c['reply']==reply and c['initial_blue']==initial and c['seed']==60)
        return Episode(case,FactsWorld())

    def checked(self,ep):
        ep.act('stage_blue_neutral');ep.act('yield')

    def test_sixteen_cases_and_public_common_menu(self):
        self.assertEqual(len(cases()),16);self.assertEqual(len(candidates()),22)
        self.assertTrue(all(not c['reverse_menu'] for c in cases()))
        for c in cases():self.assertNotEqual(c['initial_blue'],c['proposed_blue'])

    def test_accept_reject_timing_keeps_neutral_and_bound_reply(self):
        for timing in ('before_child','during_child'):
            for reply in ('accepted','rejected'):
                ep=self.episode(timing,reply);old=ep.observation();self.checked(ep)
                state=reduce_history(ep.history)
                self.assertEqual(state['goals'],{'red':'left','blue':'neutral','green':'right'})
                self.assertEqual(state['outer']['blue'],'right' if reply=='accepted' else 'left')
                self.assertEqual(state['pending'],{})
                self.assertEqual(len(ep.update_audit),1);self.assertEqual(ep.update_audit[0]['before'],ep.update_audit[0]['after'])
                self.assertEqual(old['history'],ep.history[:len(old['history'])])
        with self.assertRaises(ValueError):reduce_history([dict(kind='proposal_reply',proposal_id='absent',decision='accept')])

    def test_during_update_appears_only_after_actual_check_feedback(self):
        ep=self.episode();self.assertFalse(ep.update_injected)
        ep.act('stage_blue_neutral');self.assertFalse(ep.update_injected)
        self.assertNotIn('update_proposed',[e['kind'] for e in ep.observation()['history']])
        ep.act('yield');self.assertTrue(ep.update_injected)
        start=ep.update_audit[0]['history_start_index']
        self.assertEqual(ep.history[start-1]['choice'],'yield')
        self.assertTrue(reduce_history(ep.history[:start])['checked'])

    def test_finish_restores_latest_and_preserves_green_without_moving(self):
        ep=self.episode();self.checked(ep);ep.act('place_green_right')
        before=copy.deepcopy(ep.world.state());r=ep.act('finish_guidance')
        self.assertTrue(r['valid']);self.assertEqual(before,ep.world.state())
        self.assertEqual(reduce_history(ep.history)['goals'],{'red':'left','blue':'right','green':'right'})
        self.assertTrue(ep.finish_audit['green_right_before']);self.assertTrue(ep.finish_audit['green_right_after'])
        self.assertEqual(effective_blue_returns(ep.observation()),['place_blue_right','careful_blue_right'])
        state=reduce_history(ep.history);self.assertFalse(ep.act('finish_guidance')['valid']);self.assertEqual(state,reduce_history(ep.history))

    def test_multiple_accepted_updates_no_snapshot_rollback(self):
        ep=self.episode();self.checked(ep)
        ep.history.extend(update_events('left','accepted','u2'))
        ep.history.extend(update_events('right','accepted','u3'))
        ep.history.extend(update_events('left','rejected','u4'))
        self.assertEqual(reduce_history(ep.history)['goals']['blue'],'neutral')
        self.assertTrue(ep.act('finish_guidance')['valid'])
        self.assertEqual(reduce_history(ep.history)['goals']['blue'],'right')
        self.assertEqual(reference(ep.observation()),'place_blue_right')

    def test_early_finish_remains_legal_and_green_progress_pending(self):
        ep=self.episode();self.checked(ep)
        self.assertNotEqual(ep.world.regions['green'],'right')
        self.assertTrue(ep.act('finish_guidance')['valid'])
        self.assertFalse(ep.success());self.assertIsNone(ep.world.regions['green'])
        self.assertTrue(ep.act('place_blue_right')['valid']);self.assertTrue(ep.act('place_green_right')['success'])


if __name__=='__main__':unittest.main()
