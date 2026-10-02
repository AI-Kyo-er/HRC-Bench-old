"""同动作多重集合的公开red-first替代控制，不删原失败。"""
import unittest
from experiments.structure_foundation_v20.run_f import cases
from experiments.structure_foundation_v20.run_v1 import cases as original

class RedFirstTests(unittest.TestCase):
    def test_same_work_multiset_for_all_four_conditions(self):
        rows=cases('F');self.assertEqual(len(rows),4)
        for c in rows:
            before=next(x for x in original('BCD') if x['group']=='B' and x['seed']==c['seed'] and x['first']==c['first'] and x['timing']=='during')
            self.assertEqual(sorted(c['commands']),sorted(before['commands']));self.assertNotEqual(c['commands'],before['commands'])
            self.assertEqual(c['commands'][1],'red_left');self.assertEqual(c['commands'].count('wait_delivery'),1)
    def test_original_failed_conditions_not_removed_or_changed(self):
        self.assertEqual(len(original('BCD')),16);self.assertEqual(sum(x['group']=='B' and x['first']=='right' and x['timing']=='during' for x in original('BCD')),2)
        self.assertEqual({(x['seed'],x['first']) for x in cases('F')},{(s,d) for s in (120,121) for d in ('left','right')})

if __name__=='__main__':unittest.main()
