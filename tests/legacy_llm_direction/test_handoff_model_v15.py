"""离线模型输入/评分回归；不执行物理、不调用模型。"""
import copy
import json
import unittest
from collections import Counter
from experiments.physical.run import ROOT
from experiments.structure_handoff_v15.model_dataset import build_records,ARMS,REMINDER,OLD_RULE
from experiments.structure_handoff_v15.model_scoring import score_record
from experiments.structure_v11.protocol import SYSTEM as OLD_SYSTEM


class HandoffModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.rows,cls.sources=build_records()

    def test_256_sources_and_64_exact_anchors(self):
        self.assertEqual(len(self.rows),256)
        self.assertEqual(Counter((r['model'],r['arm']) for r in self.rows),Counter({(m,a):32 for m in ('qwen2_5_14b','qwen3_vl_8b') for a in ARMS}))
        old={r['id']:r for r in json.loads((ROOT/'results/state_readout_v13/raw/frozen_inputs.json').read_text())}
        for r in self.rows:
            if r['arm']=='old_anchor':self.assertEqual(r['messages'],old[r['source_id']]['messages'])

    def test_reminder_exact_only_system_line_addition(self):
        for r in (x for x in self.rows if x['arm']=='manual_reminder'):
            anchor=next(x for x in self.rows if x['model']==r['model'] and x['arm']=='old_anchor' and x['source_id']==r['source_id'])
            self.assertEqual(r['messages'][1:],anchor['messages'][1:])
            self.assertEqual(r['messages'][0]['content'],OLD_SYSTEM.replace(OLD_RULE,OLD_RULE+REMINDER,1))
            self.assertEqual(r['messages'][0]['content'].replace(REMINDER,'',1),anchor['messages'][0]['content'])

    def test_counterfactual_exact_budget_field_only(self):
        for r in (x for x in self.rows if x['arm']=='handoff_counterfactual8'):
            actual=next(x for x in self.rows if x['model']==r['model'] and x['arm']=='handoff_budget9' and x['source_id']==r['source_id'])
            self.assertEqual(r['messages'][0],actual['messages'][0])
            self.assertEqual(r['messages'][1]['content'],actual['messages'][1]['content'].replace('"remaining_decisions": 9','"remaining_decisions": 8',1))
            a=json.loads(actual['messages'][1]['content']);b=json.loads(r['messages'][1]['content']);b['remaining_decisions']=9
            self.assertEqual(a,b)

    def test_reverse_only_candidate_order_actual_sources_and_public_ledger(self):
        for r in (x for x in self.rows if x['model']=='qwen2_5_14b' and x['arm']=='handoff_budget9' and not x['reverse_menu']):
            reverse=next(x for x in self.rows if x['model']==r['model'] and x['arm']==r['arm'] and x['source_case_id']==r['source_case_id'] and x['reverse_menu'])
            a=json.loads(r['messages'][1]['content']);b=json.loads(reverse['messages'][1]['content'])
            self.assertEqual(a['candidates'],list(reversed(b['candidates'])));b['candidates']=a['candidates'];self.assertEqual(a,b)
            self.assertEqual(r['messages'][0],reverse['messages'][0]);self.assertEqual(len(a['candidates']),22)
            raw=json.loads((ROOT/r['source_path']).read_text())[3]['messages'];self.assertEqual(raw,r['messages'])
            stripped=copy.deepcopy(r)
            for field in ('source_case_id','reference_action','effective_blue','initial_blue','timing','acceptance','seed'):stripped.pop(field,None)
            stripped['reference_action']='arbitrary_no_reference'
            score=score_record(stripped,'{"choice":"yield"}')['score']
            self.assertEqual(set(score['acceptable_progress_choices']),{f'place_blue_{r["effective_blue"]}',f'careful_blue_{r["effective_blue"]}'})

    def test_scoring_multilegal_noop_duplicate_wronghelp_not_physical(self):
        for r in self.rows:
            target=r['effective_blue']
            for mode in ('place','careful'):
                s=score_record(r,json.dumps({'choice':f'{mode}_blue_{target}'}))['score'];self.assertTrue(s['protocol_progress']);self.assertFalse(s['physical_execution']);self.assertIsNone(s['physical_success'])
            self.assertTrue(score_record(r,'{"choice":"finish_guidance"}')['score']['duplicate_finish'])
            self.assertTrue(score_record(r,'{"choice":"yield"}')['score']['legal_no_op'])
            self.assertTrue(score_record(r,json.dumps({'choice':f'assisted_blue_{target}'}))['score']['help_authorization_error'])
            wrong='right' if target=='left' else 'left'
            self.assertIn('wrong_target',score_record(r,json.dumps({'choice':f'place_blue_{wrong}'}))['score']['errors'])


if __name__=='__main__':unittest.main()
