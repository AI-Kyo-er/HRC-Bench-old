"""公开账本/种子/格式/容量隔离反例；不加载模型或替代物理验证。"""
import copy
import unittest
from collections import Counter
from tests.test_dual_goal_v25 import FakeWorld
from experiments.dual_goal_model_v26.inputs import Episode,records,public_aid,messages,parse_output,clarify,OLD_NOTE,NEW_NOTE,source_record
from experiments.dual_goal_model_v26.backend import generation_options,FLAGS
from experiments.dual_goal_v25.run import requirement
from experiments.physical.run import ROOT


class DualModelTests(unittest.TestCase):
    def make(self,reply='accepted',timing='after_handoff',mode='relation',rule='same'):
        w=FakeWorld();green={'mode':mode,('relation' if mode=='relation' else 'destination'):rule}
        return w,Episode(w,'left',green,reply,timing)

    def test_full80_complete_cross_no_duplicates(self):
        rs=records();self.assertEqual(len(rs),80);self.assertEqual(len({r['id'] for r in rs}),80)
        self.assertEqual([r['stage'] for r in rs],['local']*16+['full']*64)
        self.assertEqual([r['order'] for r in rs],list(range(80)))
        self.assertEqual(len({tuple(sorted(r['case'].items())) for r in rs if r['stage']=='full'}),32)

    def test_rotation_balanced_and_seed_timing_pairs(self):
        rs=records();counts=Counter((r['case']['expression'],r['view'],r['position']) for r in rs if r['stage']=='full')
        self.assertEqual(set(counts.values()),{4})
        for r in rs:
            expected=270000+100*r['group'] if r['stage']=='local' else 260000+100*(r['group']//2)
            self.assertEqual(r['seed_base'],expected)
        for g in range(0,16,2):
            a=next(r for r in rs if r['stage']=='full' and r['group']==g)
            b=next(r for r in rs if r['stage']=='full' and r['group']==g+1)
            self.assertEqual(a['seed_base'],b['seed_base']);self.assertNotEqual(a['case']['timing'],b['case']['timing'])

    def test_direct_pair_goals_equal_relation(self):
        for r in records():
            if r['case']['expression']!='direct':continue
            c=r['case'];other=copy.deepcopy(c);other['expression']='relation'
            w=FakeWorld();e=Episode(w,c['initial_blue'],requirement(c),c['reply'],'before_check')
            w2=FakeWorld();e2=Episode(w2,c['initial_blue'],requirement(other),c['reply'],'before_check')
            self.assertEqual(public_aid(e.observation())['current_goals_from_public_history'],public_aid(e2.observation())['current_goals_from_public_history'])

    def test_aid_does_not_read_private_fields_or_future(self):
        w,e=self.make();o=e.observation();a=public_aid(o);o.update(case={'target':'right'},score={'success':True},future_reply='accept')
        self.assertEqual(a,public_aid(o));self.assertEqual(a['current_goals_from_public_history']['blue'],'left');self.assertTrue(a['confirmation_pending'])
        self.assertNotIn('choice',a)

    def test_accept_relation_vs_reject_and_direct(self):
        for reply,expected in (('accepted','right'),('rejected','left')):
            w,e=self.make(reply=reply,timing='before_check');a=public_aid(e.observation());self.assertEqual(a['current_goals_from_public_history'],{'red':'left','blue':expected,'green':expected})
        w,e=self.make(timing='before_check',mode='direct',rule='left');a=public_aid(e.observation())
        self.assertEqual(a['current_goals_from_public_history']['blue'],'right');self.assertEqual(a['current_goals_from_public_history']['green'],'left');self.assertNotIn('relation',a['green_requirement'])

    def test_only_note_and_aid_diff_no_history_mutation(self):
        w,e=self.make();o=e.observation();h=copy.deepcopy(o['history']);full=messages(o,'full_history');aid=messages(o,'public_ledger_aid')
        f=json_load(full[1]['content']);a=json_load(aid[1]['content']);a.pop('external_public_ledger_aid')
        self.assertEqual(a,f);self.assertEqual(full[0],aid[0]);self.assertEqual(o['history'],h)
        self.assertEqual(o['workspace']['notes'],NEW_NOTE)
        old=copy.deepcopy(o);old['workspace']['notes']=OLD_NOTE;self.assertEqual(clarify(old),o);self.assertEqual(old['workspace']['notes'],OLD_NOTE)

    def test_strict_thinking_and_last_boundary(self):
        self.assertIsNone(parse_output('{"choice":"declare_done"}')['choice'])
        self.assertEqual(parse_output('假答案 {"choice":"declare_done"}</think>{"choice":"yield"}')['choice'],'yield')
        self.assertEqual(parse_output('</think>old</think>{"choice":"request_check"}')['choice'],'request_check')
        self.assertEqual(parse_output('</think>')['parse_error'],'empty_final')
        self.assertIsNone(parse_output('</think>{"choice":"nonexistent"}')['choice'])
        self.assertIsNone(parse_output('</think>{"choice":"yield","analysis":"x"}')['choice'])

    def test_parse_none_cost_one_zero_tick_and_no_fallback(self):
        w,e=self.make();tick=w.tick;h=copy.deepcopy(e.history);r=e.act(None)
        self.assertFalse(r['valid']);self.assertEqual(e.cost['decisions'],1);self.assertEqual(e.cost['invalid'],1);self.assertEqual(w.tick,tick)
        self.assertEqual(e.history[:len(h)],h);self.assertEqual(e.observation()['remaining_decisions'],47)

    def test_local_prefix_does_not_consume_model_budget_seed(self):
        w,e=self.make(reply='rejected',timing='before_check');e.act('request_check');w.simulate(240);e.observation();w.far=True;w.near=False;e.cost['decisions']=9
        e.begin_local();self.assertEqual(e.observation()['remaining_decisions'],12);self.assertEqual(e.budget_origin,9)
        e.act(None);self.assertEqual(e.observation()['remaining_decisions'],11);self.assertEqual(e.cost['decisions'],10)
        self.assertEqual(records()[0]['seed_base'],270000)

    def test_capacity_min_new_not_in_task_options(self):
        ordinary=generation_options(151645);probe=generation_options(151645,True)
        self.assertNotIn('min_new_tokens',ordinary);self.assertEqual(probe.pop('min_new_tokens'),8192);self.assertEqual(probe,ordinary)
        self.assertEqual(ordinary['logits_to_keep'],1)
        for k in ('return_dict_in_generate','output_scores','output_logits','output_attentions','output_hidden_states'):self.assertFalse(ordinary[k])

    def test_direct_future_reply_not_encoded_in_observation(self):
        w,a=self.make(reply='accepted',mode='direct',rule='left')
        w2,b=self.make(reply='rejected',mode='direct',rule='left')
        self.assertEqual(a.observation(),b.observation())
        for e in (a,b):
            initial=next(x for x in e.observation()['history'] if x['kind']=='accepted_activity')
            self.assertEqual(initial['green_requirement'],{'mode':'direct','destination':'left'})
            self.assertFalse(any(x['kind'] in ('proposal','proposal_reply') for x in e.observation()['history']))

    def test_actual_handoff_tick_kept_after_note_adapter(self):
        w,e=self.make();e.act('request_check');w.simulate(300)
        self.assertEqual([x['actual_tick'] for x in e.pending_events if x['kind']=='proposal'],[480])
        o=e.observation();proposal=next(x for x in o['history'] if x['kind']=='proposal')
        self.assertEqual((proposal['actual_tick'],proposal['observed_tick']),(480,540))
        self.assertEqual(public_aid(o)['current_goals_from_public_history']['blue'],'right')

    def test_real_source_records_same_except_note_and_public_aid(self):
        for r in records():
            s=source_record(ROOT,r);o=s['initial_observation'];self.assertNotIn('case',o);self.assertNotIn('score',o)
            self.assertEqual(o['remaining_decisions'],12 if r['stage']=='local' else 48)
            self.assertEqual(len(o['candidates']),12);self.assertEqual(s['initial_messages'],messages(o,r['view']))
            if r['stage']=='local':self.assertEqual(s['source_sequence'],9);self.assertEqual(s['prefix_cost']['decisions'],9)


def json_load(text):
    import json
    return json.loads(text)


if __name__=='__main__':unittest.main()
