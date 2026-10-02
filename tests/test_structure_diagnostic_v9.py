"""真实来源/仅追加aid/无私有字段/多解评分的永久回归，不调用模型。"""
import copy
import json
import unittest
from experiments.physical.run import ROOT
from experiments.structure_diagnostic_v9.dataset import build_records,public_aid
from experiments.structure_diagnostic_v9.scoring import progress_choices,score


class ScopeDiagnostic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.records,cls.sources=build_records()

    def record(self,stage,view='full_history'):
        return next(r for r in self.records if r['stage']==stage and r['view']==view)

    def test_eighty_records_from_forty_exact_source_messages(self):
        self.assertEqual(len(self.records),80)
        for r in self.records:
            if r['view']=='full_history':
                source=json.loads((ROOT/r['source_path']).read_text())[r['source_row_index']]
                self.assertEqual(r['messages'],source['messages'])
                self.assertEqual(r['reference_action'],source['result']['choice'])
        self.assertEqual(len({(r['source_case_id'],r['source_row_index']) for r in self.records}),40)

    def test_aid_only_append_original_fields_and_system_exact(self):
        for full,aid in zip(self.records[::2],self.records[1::2]):
            self.assertEqual(full['messages'][0],aid['messages'][0])
            f=json.loads(full['messages'][1]['content']);a=json.loads(aid['messages'][1]['content'])
            added=a.pop('external_public_scope_aid')
            self.assertEqual(f,a)
            self.assertEqual(added,public_aid(f))
            self.assertTrue(aid['messages'][1]['content'].startswith(full['messages'][1]['content'][:-1]+', "external_public_scope_aid": '))

    def test_public_aid_ignores_private_metadata_and_reference(self):
        obs=json.loads(self.record(5)['messages'][1]['content'])
        expected=public_aid(obs)
        obs.update(hidden_goal='opposite',case={'outer_blue':'wrong'},reference_action='yield',future=[1,2,3],privileged_done=True)
        self.assertEqual(expected,public_aid(obs))
        self.assertEqual(expected['remaining_items'],['blue'])
        self.assertFalse(expected['scope']['active'])

    def test_multiple_progress_actions_and_noop_not_physical_success(self):
        expected={1:{'stage_blue_neutral','place_green_right','careful_green_right'},2:{'yield'},
                  3:{'place_green_right','careful_green_right','finish_guidance'},4:{'finish_guidance'}}
        for stage,allowed in expected.items():
            r=self.record(stage);obs=json.loads(r['messages'][1]['content'])
            self.assertEqual(set(progress_choices(obs)),allowed)
        r=self.record(3);obs=json.loads(r['messages'][1]['content'])
        scored=score('finish_guidance',None,obs,r['reference_action'])
        self.assertTrue(scored['protocol_progress']);self.assertFalse(scored['reference_action_hit'])
        self.assertIsNone(scored['physical_success']);self.assertFalse(scored['physical_execution'])
        noop=score('request_clear',None,obs,r['reference_action'])
        self.assertTrue(noop['protocol_admissible']);self.assertTrue(noop['legal_no_op']);self.assertFalse(noop['protocol_progress'])

    def test_outer_pair_and_menu_invariants(self):
        full=[r for r in self.records if r['view']=='full_history' and r['stage']==5]
        for seed in (60,61):
            for reverse in (False,True):
                pair=[r for r in full if r['seed']==seed and r['reverse_menu']==reverse]
                obs=[json.loads(r['messages'][1]['content']) for r in pair]
                for o in obs:o.pop('history')
                self.assertEqual(obs[0],obs[1])
                allowed=[set(progress_choices(json.loads(r['messages'][1]['content']))) for r in pair]
                self.assertFalse(allowed[0]&allowed[1])


if __name__=='__main__':unittest.main()
