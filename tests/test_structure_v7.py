"""协议/评分回归；FactsWorld仅单元测试替身，不是物理证据。"""
import copy
import unittest
from tests.test_structure_v5 import FactsWorld
from experiments.structure_v7.protocol import Episode, cases, candidates, reduce_history, reference, effective_blue_returns
from experiments.structure_v7.audit import first_return_audit


class NeutralScope(unittest.TestCase):
    def setup_episode(self, target='left'):
        case = next(c for c in cases() if c['outer_blue'] == target and c['seed'] == 60 and not c['reverse_menu'])
        return Episode(case, FactsWorld())

    def finish(self, episode):
        for choice in ('stage_blue_neutral', 'yield', 'place_green_right', 'finish_guidance'):
            self.assertTrue(episode.act(choice)['valid'])

    def test_crossed_cases_and_full_menu(self):
        self.assertEqual(len(cases()), 8)
        self.assertEqual(len(candidates()), 22)
        self.assertEqual(candidates(True), list(reversed(candidates())))
        for seed in (60, 61):
            for reverse in (True, False):
                self.assertEqual({c['outer_blue'] for c in cases() if c['seed'] == seed and c['reverse_menu'] == reverse}, {'left', 'right'})

    def test_finish_lifecycle_and_immutable_history(self):
        ep = self.setup_episode()
        old = ep.observation()
        before = copy.deepcopy(ep.world.state())
        self.assertFalse(ep.act('finish_guidance')['valid'])
        self.assertEqual(ep.world.state(), before)
        self.assertEqual(ep.cost['invalid'], 1)
        self.finish(ep)
        self.assertEqual(old['history'], old['history'][:4])
        self.assertEqual(len(old['history']), 4)
        self.assertEqual(ep.finish_audit['before'], ep.finish_audit['after'])
        self.assertTrue(ep.finish_audit['green_right_after'])
        self.assertFalse(ep.success())
        before = copy.deepcopy(ep.world.state())
        reduction = reduce_history(ep.history)
        self.assertFalse(ep.act('finish_guidance')['valid'])
        self.assertEqual(before, ep.world.state())
        self.assertEqual(reduction, reduce_history(ep.history))

    def test_same_finish_input_without_history_and_disjoint_targets(self):
        pair = [self.setup_episode(t) for t in ('left', 'right')]
        for ep in pair:
            self.finish(ep)
        obs = [ep.observation() for ep in pair]
        sets = [set(effective_blue_returns(o)) for o in obs]
        self.assertFalse(sets[0] & sets[1])
        for o in obs:
            o.pop('history')
            self.assertEqual(set(o), {'physical', 'physical_placements', 'remaining_decisions', 'candidates'})
        self.assertEqual(obs[0], obs[1])
        for ep in pair:
            before = ep.world.state()
            self.assertTrue(ep.act('yield')['valid'])
            self.assertEqual(before, ep.world.state())

    def test_first_attempt_keeps_wrong_target_and_recovery(self):
        ep = self.setup_episode('right')
        self.finish(ep)
        self.assertTrue(ep.act('yield')['valid'])
        before = copy.deepcopy(ep.world.state())
        self.assertFalse(ep.act('place_blue_left')['valid'])
        self.assertEqual(before, ep.world.state())
        first = copy.deepcopy(ep.first_blue_return_attempt)
        self.assertFalse(first['target_correct'])
        self.assertFalse(first['physical_attempt'])
        self.assertEqual(first['prior_target_corrections'], 0)
        self.assertTrue(first['target_revealing_feedback'])
        self.assertTrue(ep.act('place_blue_right')['success'])
        self.assertEqual(first, ep.first_blue_return_attempt)
        self.assertEqual(ep.pre_first_blue_actions, [{'choice': 'yield', 'target_revealing_feedback': False}])
        # 同tick的child拒绝不属于finish后首次返回；评分按序列而非物理tick。
        trace = [{'result': {'choice': 'place_blue_left', 'valid': False, 'target_revealing_feedback': True}},
                 {'result': {'choice': 'finish_guidance', 'valid': True}},
                 {'result': {'choice': 'yield', 'valid': True, 'target_revealing_feedback': False}},
                 {'observation': ep.observation(), 'result': {'choice': 'place_blue_left', 'valid': False, 'target_revealing_feedback': True}}]
        score = first_return_audit(trace)
        self.assertEqual(score['decision'], 4)
        self.assertFalse(score['target_correct'])
        self.assertEqual(score['prior_blue_target_revealing_feedback_after_finish'], 0)
        self.assertFalse(first_return_audit(trace[:3])['answered'])


    def test_no_attempt_and_child_retention(self):
        ep = self.setup_episode()
        self.assertEqual(reference(ep.observation()), 'stage_blue_neutral')
        self.finish(ep)
        self.assertIsNone(ep.first_blue_return_attempt)
        self.assertEqual(ep.world.regions['green'], 'right')
        self.assertFalse(reduce_history(ep.history)['active'])
        self.assertEqual(reference(ep.observation()), 'place_blue_left')


if __name__ == '__main__':
    unittest.main()
