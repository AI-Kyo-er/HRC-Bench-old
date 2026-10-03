"""基础公开字段控制自洽性；不调用模型、不执行物理。"""
import copy
import json
import unittest
from collections import Counter

from experiments.state_calibration_v14.dataset import controls,public_truth,STATE_SYSTEM,build_records
from experiments.physical.run import ROOT
from experiments.state_readout_v13.dataset import state_system
from experiments.structure_v11.protocol import SYSTEM,candidates


class CalibrationInputs(unittest.TestCase):
    def test_24_controls_balanced_by_valid_group(self):
        rows=controls();self.assertEqual(len(rows),24)
        self.assertEqual(Counter(r['group'] for r in rows),dict(direct=8,scope=8,update=8))
        for group in ('direct','scope','update'):
            selected=[r for r in rows if r['group']==group]
            self.assertEqual(Counter(r['public_state_truth']['outer_blue_destination'] for r in selected),dict(left=4,right=4))
            self.assertEqual(Counter(r['public_state_truth']['guidance_active'] for r in selected),{False:8} if group=='update' else {True:4,False:4})

    def test_system_menu_and_no_private_answers(self):
        self.assertEqual(STATE_SYSTEM,state_system(SYSTEM))
        for r in controls():
            obs=json.loads(r['messages'][1]['content'])
            self.assertEqual(r['messages'][0]['content'],STATE_SYSTEM)
            self.assertEqual(obs['candidates'],candidates(False))
            for key in ('public_state_truth','guidance_active','current_blue_destination','case','group'):
                self.assertNotIn(key,obs)
            self.assertTrue(r['synthetic_text']);self.assertEqual(r['physics_actions_executed'],0)

    def test_truth_reads_public_input_not_record_labels(self):
        for r in controls():
            obs=json.loads(r['messages'][1]['content']);truth=public_truth(obs)
            obs.update(private_target='wrong',reference_action='wrong',future=[dict(kind='child_finished')])
            self.assertEqual(public_truth(obs),truth)
            self.assertEqual(truth,r['public_state_truth'])

    def test_direct_is_only_current_natural_language_not_child_events(self):
        for r in controls():
            if r['group']!='direct':continue
            obs=json.loads(r['messages'][1]['content'])
            self.assertEqual([e['kind'] for e in obs['history']],['background_source','public_state_statement'])
            self.assertEqual(set(obs['history'][1]),{'kind','content'})

    def test_scope_current_target_and_physical_region_are_distinct(self):
        for r in controls():
            if r['group']!='scope':continue
            o=json.loads(r['messages'][1]['content']);truth=public_truth(o)
            self.assertEqual(truth['current_blue_destination'],'neutral' if truth['guidance_active'] else truth['outer_blue_destination'])
            if not truth['guidance_active']:
                kinds=[e['kind'] for e in o['history']]
                self.assertLess(kinds.index('local_check_passed'),kinds.index('child_finished'))
                self.assertIn('outer_resumed',kinds)
                self.assertIn(o['physical_placements']['blue'][0],('neutral',truth['outer_blue_destination']))

    def test_update_acceptance_changes_outer_without_starting_scope(self):
        for r in controls():
            if r['group']!='update':continue
            o=json.loads(r['messages'][1]['content']);h=o['history'];truth=public_truth(o)
            original=next(e['goals']['blue'] for e in h if e['kind']=='accepted_outer')
            proposal=next(e['destination'] for e in h if e['kind']=='update_proposed')
            reply=next(e['decision'] for e in h if e['kind']=='proposal_reply')
            self.assertFalse(truth['guidance_active'])
            self.assertEqual(truth['outer_blue_destination'],proposal if reply=='accept' else original)
            proposal_event=next(e for e in h if e['kind']=='update_proposed')
            self.assertNotIn('检查结束后',proposal_event['content'])

    def test_216_records_include_exact_all_v13_and_v4_messages(self):
        rows=build_records();self.assertEqual(len(rows),216)
        self.assertEqual(Counter(r['model'] for r in rows),{'qwen2_5_14b':24,'qwen3_vl_8b':192})
        self.assertEqual(Counter(r['suite'] for r in rows),{'control':48,'v13':128,'v4':40})
        sources={'v13':json.loads((ROOT/'results/state_readout_v13/raw/frozen_inputs.json').read_text()),
                 'v4':json.loads((ROOT/'experiments/model_scale_v4/cases/freeze.json').read_text())['records']}
        for suite,originals in sources.items():
            for r in (r for r in rows if r['suite']==suite):
                old=next(o for o in originals if o['id']==r['source_id'])
                self.assertEqual(r['messages'],old['messages'])

    def test_score_state_key_order_only_is_compliance(self):
        from experiments.state_calibration_v14.scoring import score_record
        r=next(r for r in build_records() if r['suite']=='control')
        text=json.dumps(dict(reversed(list(r['public_state_truth'].items()))))
        result=score_record(r,text)
        self.assertTrue(result['score']['joint_state_correct']);self.assertFalse(result['key_order_compliant'])
        self.assertFalse(score_record(r,text.replace('false','"false"'))['score']['schema_valid'])

    def test_action_scoring_retains_protocol_and_original_allowed_set(self):
        from experiments.state_calibration_v14.scoring import score_record
        rows=build_records()
        d4=next(r for r in rows if r['suite']=='v13' and r['stage']==4 and r['query']=='action_replay')
        self.assertTrue(score_record(d4,'{"choice":"finish_guidance"}')['score']['protocol_progress'])
        self.assertFalse(score_record(d4,'{"choice":"yield"}')['score']['protocol_progress'])
        v4=next(r for r in rows if r['suite']=='v4')
        self.assertTrue(score_record(v4,json.dumps(dict(choice=v4['allowed'][0])))['score']['acceptable'])
        self.assertFalse(score_record(d4,'{"choice":"finish_guidance"}')['score']['physical_execution'])

    def test_no_state_answer_is_injected_into_action_messages(self):
        rows=build_records()
        for r in rows:
            if r['suite']!='v13' or r['query']!='action_replay':continue
            self.assertNotIn('public_state_truth',r['messages'][1]['content'])
            partner=next(s for s in rows if s['suite']=='v13' and s['query']=='state_readout' and s['source_v12_id']==r['source_v12_id'])
            self.assertEqual(partner['messages'][1],r['messages'][1])


if __name__=='__main__':unittest.main()
