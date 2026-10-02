import copy
import unittest

from experiments.physical_v3_2.progress import (dev_cases, public_progress, messages,
                                                snapshot_observation)


class ProgressAndLogging(unittest.TestCase):
    def test_observation_log_is_immutable_after_next_action(self):
        case = dev_cases()[0]
        live = case['observation']
        history = live['history']
        stored = snapshot_observation(live)
        sent = messages(live, 'full_history')
        history.append('机器人下一步行动与未来反馈。')
        live['physical_placements']['blue'].append('left')
        self.assertNotIn('未来反馈', str(stored))
        self.assertNotIn('未来反馈', str(sent))
        self.assertEqual(stored['physical_placements']['blue'], [])

    def test_public_aid_keeps_menu_and_handles_local_revision(self):
        for case in dev_cases():
            obs = case['observation']
            aid = public_progress(obs)
            self.assertEqual(set(aid['remaining_items']), {'red', 'blue', 'green'} - {case['completed_item']})
            self.assertEqual(len(obs['candidates']), 20)
            if case['completed_item'] == 'blue':
                changed = copy.deepcopy(obs)
                prior = aid['current_goals_from_public_history']['blue']
                target = 'right' if prior == 'left' else 'left'
                changed['history'].append(f'已接受局部修正：blue最终放到{target}。其他约定保留。')
                revised = public_progress(changed)
                self.assertIn('blue', revised['remaining_items'])
                self.assertEqual(changed['candidates'], obs['candidates'])
                self.assertEqual(revised['current_goals_from_public_history']['red'],
                                 aid['current_goals_from_public_history']['red'])


if __name__ == '__main__':
    unittest.main()
