"""关键作用域回归：终止前提、外层恢复、其他物品保留和不可变观察。"""
import unittest

from experiments.structure_v5.protocol import Episode, candidates, cases, reduce_history, reference


class FactsWorld:
    """仅用于协议单元测试；物理可行性由真实Bullet轨迹单独验收。"""
    def __init__(self):
        self.regions = {x: None for x in ('red', 'blue', 'green')}
        self.tick = 0
        self.occupied = False

    def state(self):
        return {'tick': self.tick, 'objects': dict(self.regions), 'partner_position': [int(self.occupied)]}

    def at_goal(self, item, target):
        return self.regions[item] == target

    def direct_blocked(self):
        return self.occupied

    def pick_place(self, item, target, route):
        self.regions[item] = target
        self.tick += 1
        return {'success': True, 'physical_attempt': True, 'reason': 'test-only fact update'}

    def move_partner(self, occupied):
        self.occupied = occupied
        self.tick += 1
        return {'reached': True}


class StructureScope(unittest.TestCase):
    def test_common_menu_and_same_physical_checkpoint_different_obligation(self):
        self.assertEqual(len(candidates()), 21)
        self.assertEqual(candidates(True), list(reversed(candidates())))
        pair = [Episode(next(c for c in cases() if c['id'] == f'A_{v}_40'), FactsWorld())
                for v in ('exclusive', 'shared')]
        self.assertEqual(pair[0].checkpoint, pair[1].checkpoint)
        self.assertEqual(pair[0].observation()['candidates'], pair[1].observation()['candidates'])
        self.assertEqual(reference(pair[0].observation()), 'yield')
        self.assertEqual(reference(pair[1].observation()), 'careful_blue_right')
        for episode in pair:
            self.assertNotIn('goals', episode.observation())
            self.assertNotIn('must_yield', episode.observation())

    def test_finish_precondition_restore_retention_and_repeat_cost(self):
        world = FactsWorld()
        episode = Episode(next(c for c in cases() if c['id'] == 'B_nested_40'), world)
        observation = episode.observation()
        before = world.state()
        result = episode.act('finish_guidance')
        self.assertFalse(result['valid'])
        self.assertEqual(before, world.state())
        self.assertEqual(episode.cost['decisions'], 1)
        self.assertEqual(episode.cost['finishes'], 1)
        self.assertFalse(any(e['kind'] == 'inspection_started' for e in episode.history))
        episode.act('place_blue_left')
        episode.act('yield')
        episode.act('place_green_left')
        before_finish = world.state()
        self.assertTrue(episode.act('finish_guidance')['valid'])
        self.assertEqual(before_finish, world.state())
        state = reduce_history(episode.history)
        self.assertIsNone(state['active'])
        self.assertEqual(state['goals'], {'red': 'left', 'blue': 'right', 'green': 'left'})
        self.assertEqual(world.regions['green'], 'left')
        self.assertFalse(episode.success())
        self.assertFalse(episode.finish_audit['global_success_immediately_after_finish'])
        before_repeat = world.state()
        history_before = reduce_history(episode.history)
        cost_before = dict(episode.cost)
        self.assertFalse(episode.act('finish_guidance')['valid'])
        self.assertEqual(before_repeat, world.state())
        self.assertEqual(history_before, reduce_history(episode.history))
        self.assertEqual(episode.cost['invalid'], cost_before['invalid'] + 1)
        self.assertEqual(episode.cost['decisions'], cost_before['decisions'] + 1)
        self.assertEqual(len(observation['history']), 4)
        self.assertTrue(episode.act('place_blue_right')['success'])


if __name__ == '__main__':
    unittest.main()
