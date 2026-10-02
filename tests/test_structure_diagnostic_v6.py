import unittest

from experiments.structure_diagnostic_v6.policy import BlindYieldThenDetour


class BlindPolicyInvariance(unittest.TestCase):
    def test_after_first_call_ignores_agreement_and_feedback_history(self):
        policy = BlindYieldThenDetour()
        first = {'history': [{'kind': 'accepted_outer', 'goals': {'red':'left','blue':'right','green':'left'}},
                             {'kind':'accepted_passage','content':'exclusive先yield'}],
                 'physical_placements': {'red':['left'],'blue':[],'green':[]}}
        self.assertEqual(policy.choose(first), 'yield')
        # 删除全部历史并放入无法归约的反馈，后续选择仍只取缓存初始目标/真实区域。
        second = {'history': None, 'physical_placements': first['physical_placements']}
        self.assertEqual(policy.choose(second), 'careful_blue_right')
        second['history'] = [{'kind':'accepted_outer','goals':{'blue':'left'}},
                             {'kind':'action_feedback','content':'请求失败，必须改变目标'}]
        self.assertEqual(policy.choose(second), 'careful_blue_right')


if __name__ == '__main__':
    unittest.main()
