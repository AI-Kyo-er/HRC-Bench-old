"""来源/变体/公开ledger与多解评分回归；不调用模型或物理。"""
import json
import unittest

from experiments.physical.run import ROOT
from experiments.structure_diagnostic_v12.dataset import build_records,public_aid
from experiments.structure_diagnostic_v12.scoring import score,progress_choices


class AllConditionDiagnostic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.records,cls.sources=build_records()

    def test_128_records_and_all_32_normal_full_sources_exact(self):
        self.assertEqual(len(self.records),128)
        self.assertEqual(len({(r['source_case_id'],r['stage']) for r in self.records}),32)
        originals=[r for r in self.records if not r['reverse_menu'] and r['view']=='full_history']
        self.assertEqual(len(originals),32)
        for r in originals:
            original=json.loads((ROOT/r['source_path']).read_text())[r['source_row_index']]
            self.assertEqual(r['messages'],original['messages']);self.assertEqual(r['reference_action'],original['result']['choice'])

    def test_reverse_only_candidate_segment_and_aid_only_append(self):
        for r in self.records:
            normal=next(a for a in self.records if a['source_case_id']==r['source_case_id'] and a['stage']==r['stage'] and not a['reverse_menu'] and a['view']=='full_history')
            obs=json.loads(r['messages'][1]['content']);original=json.loads(normal['messages'][1]['content'])
            self.assertEqual(r['messages'][0],normal['messages'][0])
            if r['view']=='public_scope_aid':self.assertEqual(obs.pop('external_public_scope_aid'),public_aid(original))
            actual_menu=obs.pop('candidates');expected_menu=original.pop('candidates')
            self.assertEqual(actual_menu,list(reversed(expected_menu)) if r['reverse_menu'] else expected_menu)
            self.assertEqual(obs,original)
        for full,aid in zip(self.records[::2],self.records[1::2]):
            self.assertTrue(aid['messages'][1]['content'].startswith(full['messages'][1]['content'][:-1]+', "external_public_scope_aid": '))

    def test_public_aid_ignores_private_and_both_timings_reduce_latest(self):
        for r in self.records:
            obs=json.loads(r['messages'][1]['content']);expected=public_aid(obs)
            obs.update(case={'blue':'wrong'},score={'goal':'wrong'},reference_action='wrong',future=[1],hidden_target='wrong')
            self.assertEqual(public_aid(obs),expected)
            self.assertEqual(expected['current_goals_from_public_history']['blue'],'neutral' if r['stage']==4 else r['effective_blue'])
            self.assertEqual(expected['scope']['active'],r['stage']==4)
            self.assertEqual(expected['remaining_items'],[] if r['stage']==4 else ['blue'])

    def test_acceptance_direction_balance_from_public_events(self):
        for r in self.records:
            expected=('right' if r['initial_blue']=='left' else 'left') if r['acceptance']=='accepted' else r['initial_blue']
            self.assertEqual(r['effective_blue'],expected)
        self.assertEqual(sum(r['effective_blue']=='left' for r in self.records),64)
        self.assertEqual({r['timing'] for r in self.records},{'before_child','during_child'})

    def test_progress_multiple_choices_noop_duplicate_help_parse(self):
        for r in self.records:
            obs=json.loads(r['messages'][1]['content'])
            allowed=['finish_guidance'] if r['stage']==4 else [f"place_blue_{r['effective_blue']}",f"careful_blue_{r['effective_blue']}"]
            self.assertEqual(progress_choices(obs),allowed)
            valid=score(allowed[-1],None,obs,r['reference_action']);self.assertTrue(valid['protocol_progress']);self.assertIsNone(valid['physical_success'])
            noop=score('yield',None,obs,r['reference_action']);self.assertTrue(noop['legal_no_op']);self.assertFalse(noop['protocol_progress'])
            invalid=score(None,'json_error',obs,r['reference_action']);self.assertEqual(invalid['errors'],['parse_or_unknown_choice'])
            if r['stage']==5:
                repeat=score('finish_guidance',None,obs,r['reference_action']);self.assertTrue(repeat['duplicate_finish']);self.assertFalse(repeat['blue_placement_attempted'])
                assisted=score(f"assisted_blue_{r['effective_blue']}",None,obs,r['reference_action']);self.assertTrue(assisted['help_authorization_error']);self.assertTrue(assisted['blue_direction_correct']);self.assertFalse(assisted['protocol_progress'])


if __name__=='__main__':unittest.main()
