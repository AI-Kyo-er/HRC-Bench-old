"""输入/任务拆分、公开真值、严格JSON和独立query配对，不运行模型/物理。"""
import json
import unittest

from experiments.state_readout_v13.dataset import build_records,public_truth,REPLACEMENTS,V12_INPUTS
from experiments.state_readout_v13.scoring import parse_state,score_state
from experiments.state_readout_v13.analysis import summarize
from experiments.structure_diagnostic_v12.scoring import score as action_score


class StateReadout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.records,cls.sources=build_records();cls.original=json.loads(V12_INPUTS.read_text())

    def test_128_inputs_with_64_exact_action_and_same_user_state(self):
        self.assertEqual(len(self.records),128)
        for action,state in zip(self.records[::2],self.records[1::2]):
            old=next(o for o in self.original if o['id']==action['source_v12_id'])
            self.assertEqual(action['messages'],old['messages'])
            self.assertEqual(action['messages'][1],state['messages'][1])
        self.assertEqual(len({r['source_v12_id'] for r in self.records}),64)

    def test_system_only_three_predetermined_task_replacements(self):
        for action,state in zip(self.records[::2],self.records[1::2]):
            text=state['messages'][0]['content']
            self.assertNotIn('choice',text)
            for old,new in reversed(REPLACEMENTS):
                self.assertEqual(text.count(new),1);text=text.replace(new,old,1)
            self.assertEqual(text,action['messages'][0]['content'])

    def test_truth_public_only_and_stage_scope(self):
        for r in self.records:
            obs=json.loads(r['messages'][1]['content']);truth=public_truth(obs)
            obs.update(case={'blue':'wrong'},future=[1],old_model_answer='wrong',reference_action='wrong')
            self.assertEqual(public_truth(obs),truth)
            self.assertEqual(truth['guidance_active'],r['stage']==4)
            self.assertEqual(truth['current_blue_destination'],'neutral' if r['stage']==4 else truth['outer_blue_destination'])

    def test_strict_parser_no_coercion_repair_or_extra_fields(self):
        truth={'outer_blue_destination':'left','guidance_active':True,'current_blue_destination':'neutral'}
        encoded=json.dumps(truth)
        self.assertEqual(parse_state(' \n'+encoded+'\t'),(truth,None))
        for bad in ('```json\n'+encoded+'\n```',encoded+'分析',encoded.replace('true','"true"'),
                    encoded.replace('true','1'),encoded.replace('neutral','wrong'),encoded[:-1]+',"extra":0}',
                    encoded[:-1]+',"guidance_active":false}',encoded.replace('true','NaN'),
                    json.dumps(dict(reversed(list(truth.items()))))):
            value,error=parse_state(bad);self.assertIsNone(value);self.assertIsNotNone(error)
            self.assertFalse(score_state(value,error,truth)['joint_state_correct'])

    def test_paired_summary_distinguishes_report_correct_action_wrong(self):
        action,state=self.records[:2];obs=json.loads(action['messages'][1]['content'])
        rows=[dict(record=action,choice='yield',state_value=None,parse_error=None,truncated=False,
            score=action_score('yield',None,obs,action['reference_action'])),
            dict(record=state,choice=None,state_value=state['public_state_truth'],parse_error=None,truncated=False,
                 score=score_state(state['public_state_truth'],None,state['public_state_truth']))]
        result=summarize(rows)
        self.assertEqual(result['pair_outcomes'],{'state_correct_action_incorrect':1})
        self.assertEqual(result['state']['field_correct'],{'outer_blue_destination':1,'guidance_active':1,'current_blue_destination':1})

    def test_postfreeze_semantic_key_order_is_only_compliance(self):
        from experiments.state_readout_v13.semantic import parse_semantic
        truth={'outer_blue_destination':'right','guidance_active':False,'current_blue_destination':'right'}
        encoded=json.dumps(dict(reversed(list(truth.items()))))
        value,error,ordered=parse_semantic(encoded)
        self.assertEqual(value,truth);self.assertIsNone(error);self.assertFalse(ordered)
        self.assertTrue(score_state(value,error,truth)['joint_state_correct'])
        missing=json.dumps({k:v for k,v in truth.items() if k!='guidance_active'})
        for bad in (encoded.replace('false','"false"'),encoded[:-1]+',"extra":0}',encoded[:-1]+',"guidance_active":true}',missing):
            self.assertIsNotNone(parse_semantic(bad)[1])


if __name__=='__main__':unittest.main()
