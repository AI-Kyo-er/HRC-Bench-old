"""CPU冻结后的独立派生审计反例；源独立归档，不改变模型执行源。"""
import copy
import unittest
from tests import test_dual_goal_model_v26 as helpers
from experiments.dual_goal_model_v26.inputs import messages,parse_output,public_aid
from experiments.dual_goal_model_v26.audit import confirmation_trace,independent_aid,neural_checks


class Tokenizer:
    response='</think>{"choice":"unknown"}'
    def apply_chat_template(self,*a,**k):return [42]
    def decode(self,ids,skip_special_tokens=True):return '{"choice":"unknown"}' if ids==[9] else self.response


class AuditTests(unittest.TestCase):
    def make(self,**kwargs):return helpers.DualModelTests().make(**kwargs)

    def test_no_future_update_required_at_early_declare(self):
        s={'case':{'timing':'after_handoff'}}
        self.assertTrue(confirmation_trace(s,[],[],[]));self.assertFalse(confirmation_trace(s,[{}],[],[]))
        self.assertFalse(confirmation_trace(s,[],[],[{'kind':'partner_check_handoff'}]))

    def test_bound_actual_completed_tick_and_observation(self):
        s={'case':{'timing':'after_handoff'},'common_start_tick':240}
        p={'actual_tick':480,'observed_tick':540,'event_sequence':5,'proposal_id':'x'};r=dict(p,event_sequence=6)
        events=[{'kind':'partner_check_handoff','actual_tick':480}]
        self.assertTrue(confirmation_trace(s,[p],[r],events));r['actual_tick']=540;self.assertFalse(confirmation_trace(s,[p],[r],events))

    def test_independent_aid_accept_reject_and_no_private(self):
        for reply in ('accepted','rejected'):
            w,e=self.make(reply=reply,timing='before_check');o=e.observation();a=independent_aid(o)
            self.assertEqual(a,public_aid(o));o.update(case={'target':'right'},score={'ok':True},future='accept')
            self.assertEqual(a,independent_aid(o))

    def test_neural_parse_failure_cost_and_seed_rebuilt(self):
        w,e=self.make();o=e.observation();m=messages(o,'full_history');before=w.tick;result=e.act(None);t=Tokenizer()
        prediction=dict(messages=m,seed=1,input_ids=[42],generated_ids=[151668,9],response=t.response,response_with_special_tokens=t.response,
            input_tokens=1,output_tokens=2,think_end_marker_count=1,capacity_only=False,**parse_output(t.response))
        row=dict(sequence=0,phase='model',choice=None,prediction=prediction,observation=o,messages=m,before_tick=before,after_tick=w.tick,result=result)
        s=dict(record_id='audit_unit',record={'seed_base':1,'initial_messages':m},view='full_history',cost=e.cost,model_calls=1,parse_failures=1,termination_reason='budget_exhausted')
        self.assertTrue(all(neural_checks(s,[row],t)['checks'].values()))
        row['prediction']['seed']=2;self.assertFalse(neural_checks(s,[row],t)['checks']['all_predictions'])
        row['prediction']['seed']=1;s['cost']=copy.deepcopy(s['cost']);s['cost']['decisions']=2
        self.assertFalse(neural_checks(s,[row],t)['checks']['cost_exact'])


if __name__=='__main__':unittest.main()
