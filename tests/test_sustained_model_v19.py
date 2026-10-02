"""模型输入/耗步回归；事实替身不是物理执行证据。"""
import copy
import json
import unittest
from experiments.physical.run import ROOT
from experiments.sustained_model_v19.inputs import recognition_records,base_cases,messages,public_aid,parse_output,digest
from experiments.sustained_model_v19.run import initial_records
from experiments.sustained_activity_v18.protocol import Episode,candidates
from tests.test_sustained_activity_v18 import Facts

class ModelInputsTests(unittest.TestCase):
    def test_recognition_sources_12_exact_and_reverse_only(self):
        records=recognition_records(ROOT);self.assertEqual(len(records),12)
        for i in range(0,12,2):
            normal,reverse=records[i:i+2];a=copy.deepcopy(normal['observation']);b=copy.deepcopy(reverse['observation']);b['candidates'].reverse();self.assertEqual(a,b)
            path=ROOT/'results/sustained_activity_v18/raw/reference'/normal['source_case']/'decisions.json'
            source=json.loads(path.read_text())[normal['source_sequence']]
            a.pop('explicit_next_instruction');self.assertEqual(a,source['observation']);self.assertEqual(digest(a),normal['source_observation_sha256'])
            self.assertEqual(normal['seed'],1909000+i);self.assertEqual(reverse['seed'],1909001+i)
            self.assertEqual(normal['messages'][0],source['messages'][0])
    def test_recognition_actual_conditions(self):
        records={r['expected']:r['observation'] for r in recognition_records(ROOT)}
        self.assertFalse(records['request_transport']['transport_started']);self.assertFalse(records['careful_red_left']['physical_placements']['red'])
        self.assertTrue(records['yield']['transport_started']);self.assertIsNone(records['yield']['delivery_event'])
        for action in ('place_blue_left','place_blue_right'):
            self.assertIsNotNone(records[action]['delivery_event']);self.assertFalse(records[action]['physical_placements']['blue'])
        d=records['declare_done'];self.assertIn('left',d['physical_placements']['red']);self.assertIn('left',d['physical_placements']['blue'])
    def test_24_initials_match_source_and_only_aid_added(self):
        records=initial_records();self.assertEqual(len(base_cases()),12);self.assertEqual(len(records),24)
        for full,aid in zip(records[:12],records[12:]):
            self.assertEqual(full['initial_observation'],aid['initial_observation']);self.assertEqual(full['case'],aid['case'])
            x=json.loads(aid['initial_messages'][1]['content']);x.pop('external_public_ledger_aid');self.assertEqual(x,json.loads(full['initial_messages'][1]['content']))
            self.assertEqual(full['initial_messages'][0],aid['initial_messages'][0])
    def test_public_aid_history_only_no_private_or_future(self):
        for initial in ('left','right'):
            for update in ('none','accepted','rejected'):
                ep=Episode(Facts('temporarily_busy'),initial,update);o=ep.observation();a=public_aid(o)
                target=('right' if initial=='left' else 'left') if update=='accepted' else initial
                self.assertEqual(a['current_goals_from_public_history']['blue'],target);self.assertEqual(a['remaining_items'],['red','blue'])
                noisy=copy.deepcopy(o);noisy.update(case='private',seed=0,score={'target':'wrong'},reference_action='declare_done',future_ready_tick=123)
                self.assertEqual(a,public_aid(noisy));self.assertNotIn('future',json.dumps(a));self.assertFalse(a['transport']['accepted_started'])
    def test_progress_and_request_binding_public(self):
        e=Episode(Facts('temporarily_busy'),'left','rejected');e.act('request_transport');e.act('careful_red_left');e.act('request_transport')
        a=public_aid(e.observation());self.assertTrue(a['done_under_current_goals']['red']);self.assertEqual(a['remaining_items'],['blue'])
        self.assertEqual(a['transport']['rejected_count'],1);self.assertTrue(a['transport']['accepted_started'])
    def test_strict_boundaries_and_invalid_cost_no_fallback(self):
        for response,error in (('{"choice":"yield"}','missing_think_end'),('<think>x</think>','empty_final'),('<think>x</think>bad','json'),('<think>x</think>{"choice":"outside"}','candidate')):
            parsed=parse_output(response);self.assertIsNone(parsed['choice']);self.assertIsNotNone(parsed['parse_error'])
        p=parse_output('<think>x</think>ignored</think>{"choice":"yield"}');self.assertEqual(p['choice'],'yield')
        e=Episode(Facts('ready'),'left');before=copy.deepcopy(e.world.state());e.act(None);self.assertEqual(e.cost['decisions'],1);self.assertEqual(e.cost['invalid'],1);self.assertEqual(before,e.world.state())
        self.assertEqual(e.history[-1]['choice'],None)
    def test_all_legal_slow_actions_are_costed_not_wrong(self):
        e=Episode(Facts('ready'),'left');self.assertTrue(e.act('yield')['valid']);self.assertTrue(e.act('request_transport')['valid']);self.assertTrue(e.act('request_transport')['valid'])
        self.assertEqual(e.cost['invalid'],0);self.assertEqual(e.cost['decisions'],3);self.assertEqual(e.cost['duplicate_requests'],1)
    def test_messages_immutable_and_no_goal_leak_full(self):
        e=Episode(Facts('ready'),'left','accepted');o=e.observation();m=messages(o);e.act('request_transport');self.assertEqual(json.loads(m[1]['content']),o)
        self.assertNotIn('external_public_ledger_aid',json.loads(m[1]['content']));self.assertEqual(o['candidates'],candidates())

if __name__=='__main__':unittest.main()
