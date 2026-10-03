"""纯公开事实替身的事件反例回归；不把它作为真实运动/接触证据。"""
import copy
import unittest
from experiments.sustained_structure_v21.service import InspectionService
from experiments.sustained_structure_v21.cases import cases
from experiments.sustained_structure_v21.protocol import Episode, public_ledger, candidates, reference


def facts(tick, near=True, moving=False, supported=True, held=False):
    return dict(tick=tick, presence=dict(near=near, far=not near),
                presence_moving=moving, inspection=dict(satisfied=supported),
                robot_blue_contact=held)


class ServiceTests(unittest.TestCase):
    def make(self, clause='stay'):
        self.events=[];self.motions=[]
        def move(where):
            self.motions.append(where)
            return dict(destination=where)
        return InspectionService(clause, self.events.append, move)

    def test_fixed_matrix_36(self):
        self.assertEqual([len(cases(s)) for s in ('C','N','H')],[8,24,4])
        rows=sum([cases(s) for s in ('C','N','H')],[])
        self.assertEqual(len({r['id'] for r in rows}),36)

    def test_rejected_request_has_no_queue(self):
        s=self.make();self.assertEqual(s.request(facts(0,supported=False))['decision'],'rejected')
        for tick in range(1,241):s.step(facts(tick))
        self.assertEqual(s.qualified_ticks,0);self.assertFalse(s.completed)

    def test_presence_or_robot_holding_rejects(self):
        for state in (facts(0,near=False),facts(0,moving=True),facts(0,held=True)):
            s=self.make();self.assertEqual(s.request(state)['decision'],'rejected')
            self.assertFalse(s.committed)

    def test_duplicate_does_not_restart_or_sample(self):
        s=self.make();s.request(facts(0))
        for tick in range(1,61):s.step(facts(tick))
        self.assertEqual(s.request(facts(60))['decision'],'already_committed')
        self.assertEqual((s.qualified_ticks,s.acceptances),(60,1))

    def test_240_real_samples_only_and_single_handoff(self):
        s=self.make();s.request(facts(0))
        for tick in range(1,240):s.step(facts(tick))
        self.assertFalse(s.completed);s.step(facts(240));self.assertTrue(s.completed)
        s.step(facts(241));self.assertEqual(s.qualified_ticks,240)
        self.assertEqual(sum(e['kind']=='partner_check_handoff' for e in self.events),1)
        self.assertEqual(s.request(facts(241))['decision'],'already_completed')

    def test_blue_off_support_or_held_pauses_not_resets(self):
        s=self.make();s.request(facts(0))
        s.step(facts(1));s.step(facts(2,supported=False));s.step(facts(3,held=True))
        self.assertEqual(s.qualified_ticks,1);s.step(facts(4));self.assertEqual(s.qualified_ticks,2)

    def test_retain_leaves_at_60_resumes_on_real_return(self):
        s=self.make('retain');s.request(facts(0))
        for tick in range(1,61):s.step(facts(tick))
        self.assertEqual(self.motions,['far']);self.assertTrue(s.committed)
        for tick in range(61,541):s.step(facts(tick,near=False))
        self.assertEqual(self.motions,['far']);s.step(facts(541,near=False))
        self.assertEqual(self.motions,['far','near'])
        s.step(facts(542,near=True,moving=True));self.assertEqual(s.qualified_ticks,60)
        s.step(facts(543));self.assertEqual(s.qualified_ticks,61)

    def test_withdraw_return_is_not_automatic_recommit(self):
        s=self.make('withdraw');s.request(facts(0))
        for tick in range(1,61):s.step(facts(tick))
        self.assertFalse(s.committed)
        for tick in range(61,542):s.step(facts(tick,near=False))
        for tick in range(542,782):s.step(facts(tick))
        self.assertEqual(s.qualified_ticks,60);self.assertFalse(s.completed)
        self.assertEqual(s.request(facts(781))['decision'],'accepted')
        for tick in range(782,962):s.step(facts(tick))
        self.assertTrue(s.completed);self.assertEqual(s.acceptances,2)

    def test_duplicate_tick_does_not_count(self):
        s=self.make();s.request(facts(0));s.step(facts(1))
        with self.assertRaises(ValueError):s.step(facts(1))
        self.assertEqual(s.qualified_ticks,1)

    def test_truth_does_not_read_goal_or_future_plan(self):
        s=self.make();a=facts(0);a.update(private_goal='left',future_action='take_blue')
        first=s.request(a);left=s.snapshot()
        s=self.make();a=facts(0);a.update(private_goal='right',future_action='leave_blue')
        self.assertEqual(first,s.request(a));self.assertEqual(left,s.snapshot())


class FactsWorld:
    """协议替身，不运行刚体动力学、不构造真实碰撞证据。"""
    def __init__(self):
        self.tick=0;self.delivery_start_tick=0;self.delivery_event={'first_tick':0}
        self.return_start_tick=None;self.return_event=None;self.payload_return_event=None
        self.regions={'blue':['inspection'],'red':[],'green':[]};self.motion=None
        self.state_data=dict(objects={'blue':{},'red':{},'green':{}},partner_position=[.65,0,.045],
            partner_joint=0,partner_velocity=0,presence=dict(near=True,far=False),
            presence_motion=None,inspection_facts=dict(satisfied=True),
            delivery_event=self.delivery_event,return_event=None,payload_return_event=None)
    def state(self):return copy.deepcopy(dict(self.state_data,tick=self.tick))
    def at_goal(self,item,destination):return destination in self.regions[item]
    def start_presence(self,destination):return {'destination':destination}
    def public_inspection_sample(self):return facts(self.tick,supported='inspection' in self.regions['blue'])
    def delivery_facts(self):return dict(satisfied=False,carrier_joint=0,carrier_speed=0)
    def start_return(self):self.return_start_tick=self.tick;return {'start_tick':self.tick}
    def start_delivery(self):self.delivery_start_tick=self.tick
    def pick_place(self,item,destination,route):
        self.regions[item]=[destination]
        return dict(physical_attempt=True,success=True,reason='实际所选区域已满足')


class ProtocolTests(unittest.TestCase):
    def make(self, family='N', reply='accepted', presence='stay'):
        return Episode(FactsWorld(),'left',reply,presence,family)

    def test_menu_same_11_all_roles_and_targets(self):
        menus=[self.make(family,reply).observation()['candidates']
               for family in ('N','H') for reply in ('accepted','rejected')]
        self.assertEqual(len(candidates()),11)
        self.assertTrue(all(menu==menus[0] for menu in menus))
        self.assertNotIn('finish_guidance',[c['id'] for c in menus[0]])

    def test_outer_acceptance_inside_child_latest_restored(self):
        ep=self.make();ep.act('request_check');ledger=public_ledger(ep.history)
        self.assertTrue(ledger['child_active']);self.assertEqual(ledger['goals']['blue'],'right')
        ep._append(dict(kind='partner_check_handoff',qualified_ticks=240,content='实际贡献交还。'))
        ledger=public_ledger(ep.history);self.assertFalse(ledger['child_active'])
        self.assertEqual(ledger['goals'],dict(red='left',green='right',blue='right'))

    def test_rejected_outer_does_not_change_accepted_goal(self):
        ep=self.make(reply='rejected');ep.act('request_check')
        self.assertEqual(public_ledger(ep.history)['goals']['blue'],'left')

    def test_multiple_accepted_outer_updates_not_old_snapshot(self):
        ep=self.make();ep.act('request_check')
        ep._append(dict(kind='proposal',proposal_id='outer2',binding='outer_blue',destination='left'))
        ep._append(dict(kind='proposal_reply',proposal_id='outer2',decision='accept'))
        ep._append(dict(kind='partner_check_handoff',qualified_ticks=240))
        self.assertEqual(public_ledger(ep.history)['goals']['blue'],'left')

    def test_wrong_goal_during_child_really_executes_in_protocol(self):
        ep=self.make();ep.act('request_check')
        response=ep.act('place_blue_left') # 当前有效outer是right，child仍活动。
        self.assertTrue(response['valid']);self.assertIn('execution',response)
        self.assertEqual(ep.world.regions['blue'],['left'])
        self.assertTrue(public_ledger(ep.history)['child_active'])
        self.assertNotIn('应到',response['feedback'])

    def test_far_source_not_allowed_by_old_delivery_latch(self):
        ep=self.make('H');ep.world.regions['blue']=[]
        result=ep.act('place_blue_left')
        self.assertFalse(result['valid']);self.assertNotIn('execution',result)

    def test_wrong_role_request_return_not_semantically_filtered(self):
        ep=self.make('H',reply='rejected') # 当前职责为机器人接手。
        response=ep.act('request_return')
        self.assertTrue(response['valid']);self.assertEqual(ep.world.return_start_tick,0)

    def test_any_declaration_stops_without_score_or_correction(self):
        ep=self.make();response=ep.act('declare_done');before=copy.deepcopy(ep.history)
        self.assertTrue(response['terminated']);self.assertNotIn('success',response)
        with self.assertRaises(RuntimeError):ep.act('careful_red_left')
        self.assertEqual(ep.history,before);self.assertEqual(ep.world.tick,0)
        self.assertEqual(ep.cost['decisions'],1)

    def test_raw_observation_no_derived_goal_scope_case_or_score(self):
        ep=self.make();ep.world.private_goal='right';ep.world.score=False
        observation=ep.observation()
        self.assertTrue(set(observation).isdisjoint({'case','score','current_goals','child_active','private_goal','future_schedule'}))
        self.assertEqual(observation['candidates'],candidates())

    def test_public_reference_allows_simple_red_first(self):
        ep=self.make();ep.world.regions['blue']=[]
        ep._append(dict(kind='transport_request_reply',decision='accepted',content='公开接受运输。'))
        self.assertEqual(reference(ep.observation(),'public_ledger_progress'),'careful_red_left')
        self.assertEqual(reference(ep.observation(),'conservative_wait'),'careful_red_left')


if __name__=='__main__':unittest.main()
