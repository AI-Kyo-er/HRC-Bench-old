"""永久机制验收测试，非临时 smoke 文件。"""
import unittest
from experiments.symbolic.run import generate, rollout, verify_mechanisms


class MechanismTests(unittest.TestCase):
    def test_acceptance_gates(self):
        self.assertTrue(all(v for k, v in verify_mechanisms().items() if k != 'tested_seeds'))

    def test_memoryless_paired_bound(self):
        for seed in range(30):
            results = [rollout(generate(seed, v, 'dependent', 'human'), 'memoryless_tie', 'human')[0]
                       for v in (0, 1)]
            self.assertEqual(sum(r['completed'] for r in results), 12)

    def test_rejected_request_needs_alternative(self):
        job = generate(0, 0, 'closed_loop', 'human', 1)
        job[0]['truth']['accepts'] = False
        robust, _ = rollout(job, 'full_state', 'human')
        replay, _ = rollout(job, 'fixed_response', 'human')
        self.assertEqual(robust['completed'], 1)
        self.assertEqual(robust['action_cost'], 5)
        self.assertEqual(replay['unsafe_attempts'], 1)
        self.assertEqual(replay['completed'], 0)


if __name__ == '__main__':
    unittest.main()
