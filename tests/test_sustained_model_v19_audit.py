"""派生审计计数回归：原实际12条逐例全过不能因局部方向变量错误拒绝。"""
import copy
import json
import unittest
from experiments.physical.run import ROOT
from experiments.sustained_model_v19.audit import results_passed

class AuditCountTests(unittest.TestCase):
    def test_original_failed_aggregate_real_individual_checks(self):
        original=json.loads((ROOT/'results/sustained_model_v19/raw/full_history_audit_failed/full_history_audit.json').read_text())
        self.assertFalse(original['all_inputs_and_scores_pass']);self.assertTrue(results_passed(original['episodes'],original['identification'],12))
        self.assertFalse(results_passed(original['episodes'],original['identification'],24))
    def test_missing_or_real_failed_episode_still_rejected(self):
        good=[{'passed':True} for _ in range(12)];ids=copy.deepcopy(good)
        self.assertTrue(results_passed(good,ids,12));self.assertFalse(results_passed(good[:-1],ids,12));self.assertFalse(results_passed(good,ids[:-1],12))
        good[0]['passed']=False;self.assertFalse(results_passed(good,ids,12))

if __name__=='__main__':unittest.main()
