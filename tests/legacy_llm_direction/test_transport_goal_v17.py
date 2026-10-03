"""blue只解耦目标语义；事实替身不是实际控制证据。"""
import unittest
from tests.test_responsive_transport_v16 import ResourceFacts
from experiments.transport_goal_v17.protocol import Episode,candidates
from experiments.transport_goal_v17.run import cases


class GoalTests(unittest.TestCase):
    def test_full16_and21_menu(self):
        self.assertEqual(len(cases()),16);self.assertEqual(len(candidates()),21)
    def test_wrong_blue_safe_endpoint_executes_and_not_task_success(self):
        e=Episode(ResourceFacts('ready'),'left');e.act('request_transport');e.act('careful_red_left');e.act('yield')
        r=e.act('place_blue_right');self.assertTrue(r['valid']);self.assertTrue(r['execution']['success']);self.assertFalse(r['success'])
        self.assertNotIn('left',r['feedback']);self.assertIn('right',r['feedback'])
    def test_declaredgoal_does_not_affect_same_commands(self):
        a,b=Episode(ResourceFacts('ready'),'left'),Episode(ResourceFacts('ready'),'right')
        for action in ('request_transport','careful_red_left','yield','careful_blue_right'):
            ra,rb=a.act(action),b.act(action);self.assertEqual(a.world.state(),b.world.state());self.assertEqual(ra['feedback'],rb['feedback'])
    def test_true_preconditions_and_other_filters_retained(self):
        e=Episode(ResourceFacts('ready'),'right')
        for choice in ('place_blue_left','careful_blue_right','place_green_right','place_red_right','assisted_red_left'):
            self.assertFalse(e.act(choice)['valid'])
        self.assertEqual(e.world.pick_calls,0)
    def test_repeat_selected_actual_region_feedback_not_declared(self):
        e=Episode(ResourceFacts('ready'),'left');e.act('request_transport');e.act('careful_red_left');e.act('yield');e.act('place_blue_right')
        r=e.act('place_blue_right');self.assertFalse(r['valid']);self.assertIn('实际',r['feedback']);self.assertNotIn('left',r['feedback']);self.assertNotIn('约定',r['feedback'])


if __name__=='__main__':unittest.main()
