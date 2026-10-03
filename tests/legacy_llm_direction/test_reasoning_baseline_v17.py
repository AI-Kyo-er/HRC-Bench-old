"""固定人工输入，只检验适配和来源；不调用模型。"""
import unittest
import json
from experiments.reasoning_baseline_v17.adapter import score,final_answer,PARAMETERS,MAX_NEW_TOKENS
from experiments.reasoning_baseline_v17.run import records,SOURCE,digest

class ReasoningTests(unittest.TestCase):
    def test_original80_exact_seed(self):
        original=json.loads(SOURCE.read_text())['records'];rows=records();self.assertEqual(len(rows),80)
        for row in rows:
            self.assertEqual(row['record'],original[row['case_index']]);self.assertEqual(row['messages_sha256'],digest(original[row['case_index']]['messages']))
            self.assertEqual(row['seed'],17000+row['case_index'])
    def test_thinking_never_scores_reasoning(self):
        r=records()[0]['record'];correct=r['allowed'][0];bad='not_in_menu'
        value=score(r,json.dumps({'choice':correct})+'\n</think>\n'+json.dumps({'choice':bad}),'thinking')
        self.assertFalse(value['acceptable']);self.assertIsNotNone(value['parse_error'])
    def test_missing_end_rejected_even_with_correct_json(self):
        r=records()[0]['record'];value=score(r,json.dumps({'choice':r['allowed'][0]}),'thinking')
        self.assertIsNone(value['choice']);self.assertEqual(value['boundary_error'],'missing_think_end')
    def test_exact_end_final_and_strict_original_parser(self):
        r=records()[0]['record'];text=json.dumps({'choice':r['allowed'][0]})
        self.assertTrue(score(r,'推理\n</think>\n'+text,'thinking')['acceptable'])
        self.assertTrue(score(r,text,'nonthinking')['acceptable'])
        self.assertFalse(score(r,'```json\n'+text+'\n```','nonthinking')['acceptable'])
        self.assertEqual(final_answer('</think>xxx</think>final','thinking'),('final',None))
        self.assertTrue(score(r,text+'</think>wrong</think>'+text,'thinking')['acceptable'])
        self.assertIsNotNone(score(r,text+'</think>','thinking')['parse_error'])
    def test_nonthinking_not_require_generated_end(self):
        self.assertEqual(final_answer(' {"choice":"yield"} ','nonthinking'),('{"choice":"yield"}',None))
        self.assertIsNotNone(final_answer('<think>x</think>{"choice":"yield"}','nonthinking')[1])
    def test_parameters_fixed(self):
        self.assertEqual(MAX_NEW_TOKENS,8192);self.assertEqual(PARAMETERS['thinking']['temperature'],.6);self.assertEqual(PARAMETERS['nonthinking']['top_p'],.8)

if __name__=='__main__':unittest.main()
