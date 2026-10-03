"""事后聚合永久反例：不以早失败耗时制造效率或筛除配对条件。"""
import unittest
from experiments.dual_goal_model_v26.report import costs_for_summary,summary_group,pairs,behavior


def example(ident,ok,ticks):
    return dict(id=ident,safe_task_success=ok,task_success=ok,physical_contract_ok=True,trace_integrity_passed=True,
        termination_reason='declared_done',parse_failures=0,generation_hit_limit=0,behavior={'precondition_rejections':[]},costs={'measured_makespan_ticks':ticks,
        'measured_cost':dict(decisions=3 if ok else 1,physical_attempts=2 if ok else 0,yields=0,wait_ticks=0)})


class ReportTests(unittest.TestCase):
    def test_short_failed_declaration_not_success_efficiency(self):
        r=summary_group([example('good',True,6120),example('early',False,0)])
        self.assertEqual(r['total'],2);self.assertEqual(r['safe_task_success'],1)
        self.assertEqual(r['success_mean_cost']['makespan_ticks'],6120)
        self.assertEqual(r['failure_termination_costs'][0]['id'],'early')

    def test_failed_pair_retained_no_common_success_cost(self):
        a=example('a',True,6120);b=example('b',False,0);a.update(arm='direct',group=0);b.update(arm='relation',group=0)
        r=pairs([a,b],'arm',('direct','relation'),('group',))
        self.assertEqual(r['total'],1);self.assertEqual(r['outcomes'],{'first_only':1})
        self.assertIsNone(r['pairs'][0]['common_success_costs']);self.assertEqual(r['pairs'][0]['ids'],['a','b'])

    def test_local_cost_excludes_real_prefix_but_preserves_total(self):
        s=dict(stage='local',local_makespan_ticks=6120,makespan_ticks=16741,local_cost={'decisions':3},cost={'decisions':12},prefix_cost={'decisions':9})
        c=costs_for_summary(s);self.assertEqual(c['measured_makespan_ticks'],6120);self.assertEqual(c['prefix_makespan_ticks'],10621)
        self.assertEqual(c['total_episode_cost']['decisions'],12);self.assertEqual(c['measured_cost']['decisions'],3)

    def test_rejected_reload_has_no_physical_attempt(self):
        row=dict(sequence=9,phase='model',choice='reload_blue',actual_updates_during_skill=[],
            prediction={'parse_error':None},before_tick=10861,after_tick=10861,
            result=dict(valid=False,no_op=False,execution={'physical_attempt':False}))
        b=behavior([row]);self.assertEqual(len(b['precondition_rejections']),1)
        self.assertEqual(b['actual_model_grasp_places'],[])
        self.assertEqual(b['model_action_counts'],{'reload_blue':1})


if __name__=='__main__':unittest.main()
