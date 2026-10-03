"""事实替身协议/时钟/比较回归，不代替真实物理安全或抓放证据。"""
import copy
import json
import unittest
from experiments.responsive_transport_v16.world import ResponsiveWorld,BUSY_TICKS,CONFIG
from experiments.responsive_transport_v16.protocol import Episode,cases,candidates,reference
from experiments.structure_handoff_v15.reference_audit import physical_equal
from experiments.responsive_transport_v16.canonical import physics_equal
from experiments.physical.run import ROOT
from tests.test_structure_v8 import DeliveryFacts


class ResourceFacts(DeliveryFacts):
    availability=ResponsiveWorld.availability
    def __init__(self,status):
        super().__init__();self.initial_availability=status;self.common_start_tick=self.tick
        self.start_calls=0;self.partner_target=.6
    def state(self):
        s=super().state();s.update(partner_joint=.6,partner_command=self.partner_target,availability=self.availability());return s
    wait_ready=ResponsiveWorld.wait_ready
    def start_delivery(self):
        self.start_calls+=1;self.delivery_start_tick=self.tick
    def simulate(self,ticks):
        self.tick+=ticks
        if self.delivery_start_tick is not None and self.tick-self.delivery_start_tick>=3715 and self.delivery_event is None:
            self.delivery_event=dict(first_tick=self.delivery_start_tick+3715,note='协议替身，非真实交付')
    def wait_delivery(self):
        before=self.tick;self.simulate(3715 if self.delivery_start_tick is not None else CONFIG['wait_budget_ticks'])
        return dict(success=self.delivery_event is not None,ticks=self.tick-before,delivery_event=copy.deepcopy(self.delivery_event))
    def pick_place(self,*args):
        result=super().pick_place(*args);self.simulate(3179);return result


class ResponsiveTests(unittest.TestCase):
    def episode(self,status):return Episode(ResourceFacts(status))
    def test_no_autostart_and_shared_menu_no_private_keys(self):
        self.assertEqual(len(cases()),16);self.assertEqual(len(candidates()),21)
        a,b=self.episode('ready'),self.episode('temporarily_busy')
        for e in (a,b):
            self.assertIsNone(e.world.delivery_start_tick);self.assertEqual(e.world.start_calls,0)
            for key in ('policy','case','seed','initial_availability','plan'):self.assertNotIn(key,e.observation())
        self.assertEqual(a.observation()['candidates'],b.observation()['candidates'])
    def test_reject_no_pending_then_ready_requires_new_request(self):
        e=self.episode('temporarily_busy');r=e.act('request_transport');self.assertEqual(r['request_decision'],'rejected');t=e.world.tick
        e.world.simulate(BUSY_TICKS);self.assertEqual(e.world.availability()['status'],'ready');self.assertIsNone(e.world.delivery_start_tick)
        self.assertEqual(e.world.start_calls,0);self.assertIsNone(e.world.delivery_event)
        self.assertEqual(e.act('request_transport')['request_decision'],'accepted');self.assertEqual(e.world.delivery_start_tick,t+BUSY_TICKS)
    def test_duplicate_no_reaccept_restart_or_time_cost(self):
        e=self.episode('ready');e.act('request_transport');start=e.world.delivery_start_tick;e.world.simulate(1000);before=copy.deepcopy(e.world.state())
        r=e.act('request_transport');self.assertEqual(r['request_decision'],'already_started');self.assertTrue(r['no_op'])
        self.assertEqual(before,e.world.state());self.assertEqual(e.world.delivery_start_tick,start);self.assertEqual(e.world.start_calls,1)
        self.assertEqual(e.cost['accepted_requests'],1);self.assertEqual(e.cost['duplicate_requests'],1);self.assertEqual(e.cost['decisions'],2)
    def test_clear_yield_never_start_or_implicit_accept(self):
        for status in ('ready','temporarily_busy'):
            e=self.episode(status);e.act('request_clear');e.act('yield');self.assertEqual(e.world.start_calls,0)
            self.assertIsNone(e.world.delivery_start_tick);self.assertIsNone(e.world.delivery_event)
    def test_wait_ready_uses_public_status_and_does_not_start(self):
        e=self.episode('temporarily_busy');self.assertEqual(reference(e.observation(),'wait_ready'),'yield')
        r=e.act('yield');self.assertEqual(r['wait']['ticks'],1920);self.assertIsNone(e.world.delivery_start_tick)
        self.assertEqual(reference(e.observation(),'wait_ready'),'request_transport')
        e.act('request_transport');self.assertEqual(reference(e.observation(),'wait_ready'),'careful_red_left')
        for word in ('8秒','1920','ready_tick','ready_at'):
            self.assertNotIn(word,e.messages()[0]['content'])
        busy=self.episode('temporarily_busy');self.assertIsNone(busy.observation()['partner_availability']['ready_event'])

    def test_blue_before_delivery_and_unassigned_green_never_execute(self):
        e=self.episode('ready')
        for choice in ('place_blue_left','careful_blue_left','assisted_blue_left','place_blue_right','place_green_left'):
            self.assertFalse(e.act(choice)['valid'])
        self.assertEqual(e.world.pick_calls,0);self.assertEqual(e.cost['physical_attempts'],0)
    def test_red_progress_survives_rejection_and_reacceptance(self):
        e=self.episode('temporarily_busy');e.act('request_transport');e.act('careful_red_left');before=copy.deepcopy(e.world.state())
        self.assertTrue(e.world.at_goal('red','left'));self.assertEqual(e.act('request_transport')['request_decision'],'accepted')
        self.assertTrue(e.world.at_goal('red','left'));self.assertEqual(before['objects'],e.world.state()['objects'])
    def test_policy_only_public_input_adapts_and_tracks_rejection(self):
        e=self.episode('temporarily_busy');obs=e.observation();self.assertEqual(reference(obs,'availability_greedy'),'careful_red_left');self.assertEqual(reference(obs,'serial'),'careful_red_left');self.assertEqual(reference(obs,'eager'),'request_transport')
        e.act('request_transport');self.assertEqual(reference(e.observation(),'eager'),'careful_red_left')
        ready=self.episode('ready');self.assertEqual(reference(ready.observation(),'availability_greedy'),'request_transport')
    def test_actual_and_observed_tick_distinct_no_future_mutable_history(self):
        e=self.episode('temporarily_busy');old=e.observation();e.act('careful_red_left');events=e.availability_events
        self.assertEqual(len(events),1);self.assertEqual(events[0]['availability_actual_tick'],e.world.common_start_tick+1920)
        self.assertEqual(events[0]['observed_tick'],e.world.common_start_tick+3180);self.assertEqual(e.history[:len(old['history'])],old['history'])
        self.assertEqual([x['event_sequence'] for x in e.history],list(range(len(e.history))))
    def test_real_state_canonical_preserves_contacts_and_rejects_unknown_fields(self):
        path=ROOT/'results/structure_v8/raw/reference/A_delivery_shared_overlap_70/summary.json';state=json.loads(path.read_text())['checkpoint'];state['availability']={}
        b=copy.deepcopy(state)
        for c in b['contacts']:c['position_a']=tuple(c['position_a']);c['position_b']=tuple(c['position_b'])
        self.assertTrue(physics_equal(state,b));b['contacts'][0]['contact_distance']+=1e-9;self.assertFalse(physics_equal(state,b))
        b['unclassified']=1
        with self.assertRaises(AssertionError):physics_equal(state,b)


if __name__=='__main__':unittest.main()
