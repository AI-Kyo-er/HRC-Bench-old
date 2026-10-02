"""恢复来源覆盖的指定控制回归，不执行物理。"""
import unittest
from experiments.structure_foundation_v20.run_e import cases,SOURCES

class RecoveryFoundationTests(unittest.TestCase):
    def test_four_recovery_directions_and_same_world_sources(self):
        rows=cases('E');self.assertEqual(len(rows),4);self.assertEqual({(r['seed'],r['first']) for r in rows},{(s,t) for s in (120,121) for t in ('left','right')})
        self.assertIn('experiments/structure_foundation_v20/world_v1.py',SOURCES);self.assertNotIn('experiments/structure_foundation_v20/world_v2.py',SOURCES)
    def test_fixed_first_inspect_opposite_preserves_original_20(self):
        for r in cases('E'):
            self.assertEqual(r['commands'],['request','red_left','wait_delivery',f'blue_{r["first"]}','blue_inspection',f'blue_{r["goal"]}']);self.assertNotEqual(r['first'],r['goal'])
        from experiments.structure_foundation_v20.run_v1 import cases as old
        self.assertEqual(len(old('A')),4);self.assertEqual(len(old('BCD')),16)
    def test_intermediate_evidence_required_even_when_final_correct(self):
        import copy
        from types import SimpleNamespace
        from experiments.structure_foundation_v20.run_e import facts
        c=cases('E')[0];state=dict(objects={'green':dict(position=[.42,.16,.023])})
        w=SimpleNamespace(state=lambda:state,initial_state=copy.deepcopy(state),at_goal=lambda item,goal:True)
        state['delivery_event']={'first_tick':10}
        rows=[dict(result={'success':True},after_state={}) for _ in c['commands']]
        rows[3]['after_state']={'objects':{'blue':dict(position=[.65,-.25,.032],velocity=[0,0,0])}}
        rows[4]['after_state']={'inspection_facts':{'satisfied':True}}
        self.assertTrue(all(facts(w,c,rows).values()))
        rows[3]['after_state']['objects']['blue']['position'][1]=.25
        self.assertFalse(facts(w,c,rows)['first_real_region'])
        rows[3]['after_state']['objects']['blue']['position'][1]=-.25;rows[4]['after_state']['inspection_facts']['satisfied']=False
        self.assertFalse(facts(w,c,rows)['inspection_actual'])

if __name__=='__main__':unittest.main()
