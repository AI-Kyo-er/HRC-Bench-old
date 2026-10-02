"""真实来源、十视图公开字段、D4/D5协议回归；无模型或物理调用。"""
import copy
import json
import unittest

from experiments.structure_ablation_v10.dataset import build_records,subset_aid,V9_INPUTS,ARMS,FIELDS
from experiments.structure_ablation_v10.scoring import score
from experiments.structure_diagnostic_v9.dataset import public_aid


class FieldAblation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.records,cls.sources=build_records();cls.v9=json.loads(V9_INPUTS.read_text())

    def test_160_from_all_16_real_checkpoints(self):
        self.assertEqual(len(self.records),160)
        self.assertEqual(len({r['source_v9_id'] for r in self.records}),16)
        self.assertEqual({r['stage'] for r in self.records},{4,5})
        for arm in ARMS:self.assertEqual(sum(r['arm']==arm for r in self.records),16)

    def test_raw_and_full_aid_anchors_exact(self):
        for r in self.records:
            if r['arm'] not in ('raw_full','v9_full_aid'):continue
            view='full_history' if r['arm']=='raw_full' else 'public_scope_aid'
            source=next(v for v in self.v9 if v['source_case_id']==r['source_case_id'] and v['stage']==r['stage'] and v['view']==view)
            self.assertEqual(r['messages'],source['messages'])

    def test_ten_view_differences_only_specified_append(self):
        for r in self.records:
            raw=next(v for v in self.records if v['source_v9_id']==r['source_v9_id'] and v['arm']=='raw_full')
            self.assertEqual(r['messages'][0],raw['messages'][0])
            obs=json.loads(raw['messages'][1]['content']);actual=json.loads(r['messages'][1]['content'])
            if r['arm']=='raw_full':self.assertEqual(obs,actual);continue
            aid=actual.pop('external_public_scope_aid');self.assertEqual(obs,actual)
            if r['arm']=='v9_full_aid':self.assertEqual(aid,public_aid(obs))
            else:
                self.assertEqual(aid,subset_aid(obs,r['arm']))
                keys={'source'}|{key for f in r['arm'] if f in FIELDS for key in FIELDS[f]}
                self.assertEqual(set(aid),keys)
                self.assertEqual(aid['source'],public_aid(obs)['source'])
            self.assertTrue(r['messages'][1]['content'].startswith(raw['messages'][1]['content'][:-1]))

    def test_public_factors_ignore_private_fields(self):
        obs=json.loads(self.records[0]['messages'][1]['content'])
        altered=copy.deepcopy(obs);altered.update(case={'blue':'wrong'},reference_action='wrong',future=[1],privileged_done=True)
        for arm in ARMS[1:9]:self.assertEqual(subset_aid(obs,arm),subset_aid(altered,arm))

    def test_d4_positive_d5_multiple_blue_choices_noop_direction(self):
        for r in self.records:
            obs=json.loads(r['messages'][1]['content'])
            if r['stage']==4:
                result=score('finish_guidance',None,obs,r['reference_action']);self.assertTrue(result['protocol_progress'])
                self.assertEqual(result['acceptable_progress_choices'],['finish_guidance'])
            else:
                target=r['outer_blue'];result=score(f'careful_blue_{target}',None,obs,r['reference_action'])
                self.assertEqual(set(result['acceptable_progress_choices']),{f'place_blue_{target}',f'careful_blue_{target}'})
                self.assertTrue(result['blue_placement_attempted']);self.assertTrue(result['blue_direction_correct'])
                repeat=score('finish_guidance',None,obs,r['reference_action']);self.assertTrue(repeat['duplicate_finish'])
                opposite='right' if target=='left' else 'left'
                wrong=score(f'place_blue_{opposite}',None,obs,r['reference_action']);self.assertTrue(wrong['blue_placement_attempted']);self.assertFalse(wrong['blue_direction_correct'])
            self.assertIsNone(result['physical_success']);self.assertFalse(result['physical_execution'])
            noop=score('yield',None,obs,r['reference_action']);self.assertTrue(noop['legal_no_op']);self.assertFalse(noop['protocol_progress'])

    def test_summary_interpretation_uses_frozen_runtime_metadata(self):
        from experiments.structure_ablation_v10.audit import summary_matches
        derived={'total':160,'interpretation':'分析简述'};frozen={'interpretation':'冻结运行说明'}
        saved={'total':160,'interpretation':'冻结运行说明','model':{}}
        self.assertTrue(summary_matches(saved,derived,frozen))
        self.assertFalse(summary_matches(dict(saved,total=159),derived,frozen))
        self.assertFalse(summary_matches(dict(saved,interpretation='错误版本'),derived,frozen))


if __name__=='__main__':unittest.main()
