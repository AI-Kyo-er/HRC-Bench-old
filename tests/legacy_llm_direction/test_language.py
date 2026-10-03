import unittest
from experiments.language.environment import Episode, build_case, reference_state, parse_action, DOMAINS, STRUCTURES

class LanguageMechanisms(unittest.TestCase):
    def test_pending_revoked_local_state(self):
        for structure in STRUCTURES:
            e=Episode(build_case('packing',structure,0,'test'))
            e.start_step(0)
            self.assertEqual(reference_state(e.events)['agreements']['红杯']['destination'],'左箱')
            e.act(e.allowed_actions()[0])
            e.start_step(1)
            state=reference_state(e.events)
            self.assertEqual(state['agreements']['蓝碗']['destination'],
                             '左箱' if structure in ('nested','nested_reentry') else '右箱')
            self.assertEqual(state['agreements']['小盘']['destination'],'左箱')
            self.assertEqual(state['completed'],{'红杯':'左箱'})

    def test_reference_solves_all(self):
        for domain in DOMAINS:
            for structure in STRUCTURES:
                for variant in (0,1):
                    e=Episode(build_case(domain,structure,variant,'test'))
                    for step in range(3):
                        e.start_step(step)
                        # 强基线选择所有可行动作中直接完成的动作。
                        completed,terminal=e.act(e.allowed_actions()[0])
                        self.assertTrue(completed and terminal)
                    self.assertEqual(len(reference_state(e.events)['completed']),3)

    def test_action_triggered_partner(self):
        for accepts in (True,False):
            e=Episode(build_case('packing','retain',0,'test',accepts))
            e.start_step(1)
            self.assertFalse(any(x['kind']=='response' for x in e.events))
            e.act({'action':'request','item':'蓝碗'})
            self.assertEqual(e.events[-1]['kind'],'response')
            self.assertEqual(e.granted,accepts)
            self.assertEqual(any(x.get('method')=='assisted' for x in e.allowed_actions()),accepts)

    def test_observation_counterfactual_and_adapter_boundary(self):
        a,b=[Episode(build_case('packing','retain',v,'test')) for v in (0,1)]
        a.start_step(0);b.start_step(0)
        self.assertEqual(a.observation(),b.observation())
        self.assertNotEqual(a.allowed_actions(),b.allowed_actions())
        for view in ('full_history','oracle_summary'):
            text=str(a.messages(view))
            for private in ('partner_accepts','reference_allowed_actions','case_id','retain'):
                self.assertNotIn(private,text)

    def test_strict_parse(self):
        self.assertIsNone(parse_action('{"action":"yield","item":"杯"}')[1])
        self.assertIsNotNone(parse_action('```json\n{}\n```')[1])
        self.assertIsNotNone(parse_action('{"action":"yield","item":"杯","extra":1}')[1])

if __name__ == '__main__':
    unittest.main()
