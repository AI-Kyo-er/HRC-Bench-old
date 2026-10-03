"""v3接口边界与恢复机制；真实抓放可行性由controls阶段检验。"""
import unittest

from experiments.physical.protocol import (Episode, candidates, calibration_cases,
                                           parse, reference)


class PhysicalProtocol(unittest.TestCase):
    def setUp(self):
        try:
            from experiments.physical.world import World
        except ImportError:
            self.skipTest('物理测试需使用.venv-llm/bin/python和物理依赖')
        self.world = World(seed=0)
        self.ep = Episode({'condition': 'revision', 'seed': 0, 'partner_accepts': False,
                           'reverse_menu': False, 'step_budget': 12}, self.world)

    def tearDown(self):
        if hasattr(self, 'world'):
            self.world.close()

    def test_menu_and_observation_do_not_leak_scoring_goal(self):
        before = self.ep.observation()
        self.ep.goals['blue'] = 'left'
        self.ep.case['partner_accepts'] = True
        self.assertEqual(before, self.ep.observation())
        self.assertNotIn('completed', str(before))
        self.assertEqual({x['id'] for x in candidates()}, {x['id'] for x in candidates(reverse=True)})
        self.assertEqual(len(candidates()), 20)

    def test_nonessential_help_is_recoverable_and_costed(self):
        start = self.world.state()['objects']
        result = self.ep.act('request_clear')
        self.assertTrue(result['valid'])
        self.assertEqual(self.ep.cost['redundant_requests'], 1)
        self.assertEqual(self.ep.cost['decisions'], 1)
        self.assertEqual(start, self.world.state()['objects'])
        self.assertEqual(reference(self.ep.observation()), 'place_red_left')

    def test_wrong_target_feedback_keeps_other_subtasks(self):
        result = self.ep.act('place_red_right')
        self.assertFalse(result['valid'])
        self.assertEqual(self.ep.cost['physical_attempts'], 0)
        self.assertFalse(self.ep.intervened)
        self.assertEqual(reference(self.ep.observation()), 'place_red_left')

    def test_partner_motion_changes_real_geometry_yield_does_not_finish_items(self):
        occupied = self.world.move_partner(True)
        self.assertTrue(occupied['direct_blocked_after'])
        self.assertLess(occupied['central_waypoint_clearance']['aabb_sphere_clearance'], 0)
        refused = self.ep.act('request_clear')
        self.assertIn('拒绝', refused['feedback'])
        self.assertTrue(self.world.direct_blocked())
        self.assertEqual(reference(self.ep.observation()), 'careful_red_left')
        self.ep.must_yield = True
        result = self.ep.act('yield')
        self.assertFalse(self.world.direct_blocked())
        self.assertEqual(result['completed'], {})
        self.assertEqual(self.ep.cost['physical_attempts'], 0)

    def test_parser_and_calibration_target_order_controls(self):
        menu = candidates()
        self.assertEqual(parse('{"choice":"yield"}', menu), ('yield', None))
        for bad in ('{}', '[]', '{"choice": []}', '{"choice":"yield","extra":1}',
                    '```json\n{"choice":"yield"}\n```', '{"choice":"teleport"}'):
            self.assertIsNotNone(parse(bad, menu)[1])
        cases = calibration_cases()
        self.assertEqual(len(cases), 16)
        for a, b in zip(cases[::2], cases[1::2]):
            self.assertEqual(a['facts'], b['facts'])
            self.assertEqual(a['allowed'], b['allowed'])
            self.assertEqual(a['menu'], b['menu'][::-1])


if __name__ == '__main__':
    unittest.main()
