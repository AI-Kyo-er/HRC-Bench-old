"""许可/先后约束与固定运输profile回归；事实替身不作物理证据。"""
import copy
import unittest
import gzip
import tempfile
from pathlib import Path
from experiments.structure_v5.run import prefix_digest
from experiments.physical.run import sha

from tests.test_structure_v5 import FactsWorld
from experiments.structure_v8.protocol import Episode, cases, reference, candidates
from experiments.structure_v8.world_v2 import profile_distance, CONFIG


class DeliveryFacts(FactsWorld):
    def __init__(self):
        super().__init__()
        self.delivery_event = None
        self.delivery_start_tick = None
        self.pick_calls = 0

    def state(self):
        state = super().state()
        state.update(partner_velocity=0, delivery_event=copy.deepcopy(self.delivery_event))
        return state

    def start_delivery(self):
        self.delivery_start_tick = self.tick

    def wait_delivery(self):
        before = self.tick
        if self.delivery_event is None:
            self.tick += 100
            self.delivery_event = dict(first_tick=self.tick, note='事实替身，非真实交付')
        return dict(success=True, ticks=self.tick-before, delivery_event=copy.deepcopy(self.delivery_event))

    def pick_place(self, *args):
        self.pick_calls += 1
        return super().pick_place(*args)


class DeliveryProtocol(unittest.TestCase):
    def episode(self, agreement):
        case = next(c for c in cases() if c['agreement']==agreement)
        return Episode(case, DeliveryFacts())

    def test_fixed_profile_and_geometry_fix_without_wait_tuning(self):
        self.assertEqual(CONFIG['nominal_velocity_m_s'], .04)
        self.assertEqual(CONFIG['ramp_seconds'], .5)
        self.assertAlmostEqual(profile_distance(.5), .01)
        self.assertAlmostEqual(profile_distance(15), .59)
        self.assertAlmostEqual(profile_distance(15.5), .6)
        self.assertAlmostEqual(profile_distance(20), .6)
        values=[profile_distance(t/240) for t in range(3721)]
        self.assertTrue(all(a <= b for a,b in zip(values,values[1:])))
        self.assertLessEqual(max(b-a for a,b in zip(values,values[1:])), .04/240+1e-12)
        self.assertGreater(CONFIG['carrier_center_start'][2]-CONFIG['carrier_half_extents'][2], .028)

    def test_physical_comparator_ignores_gzip_metadata_but_detects_state_change(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=[Path(folder)/f'{i}.jsonl.gz' for i in range(3)]
            for index,path in enumerate(paths):
                line=b'{"tick":1,"objects":{"blue":[0.65,0,0.072]}}\n' if index<2 else b'{"tick":1,"objects":{"blue":[0.66,0,0.072]}}\n'
                with gzip.GzipFile(filename=str(path),mode='wb',mtime=index+1) as stream:
                    stream.write(line)
            self.assertNotEqual(sha(paths[0]),sha(paths[1]))
            self.assertEqual(prefix_digest(paths[0],1),prefix_digest(paths[1],1))
            self.assertNotEqual(prefix_digest(paths[0],1),prefix_digest(paths[2],1))

    def test_common_checkpoint_menu_and_public_responsive_policy(self):
        exclusive,shared=self.episode('exclusive'),self.episode('shared')
        self.assertEqual(exclusive.checkpoint,shared.checkpoint)
        self.assertEqual(len(candidates()),20)
        self.assertEqual(exclusive.observation()['candidates'],shared.observation()['candidates'])
        self.assertEqual(reference(exclusive.observation()),'yield')
        self.assertEqual(reference(shared.observation()),'careful_red_left')
        self.assertEqual(reference(shared.observation(),'conservative'),'yield')
        for ep in (exclusive,shared):
            for key in ('case','caseid','seed','phase','policy','agreement','allow_overlap'):
                self.assertNotIn(key,ep.observation())

    def test_exclusive_red_and_all_early_blue_rejected_without_execution(self):
        exclusive,shared=self.episode('exclusive'),self.episode('shared')
        before=copy.deepcopy(exclusive.world.state())
        self.assertFalse(exclusive.act('careful_red_left')['valid'])
        self.assertEqual(exclusive.world.pick_calls,0)
        self.assertEqual(before,exclusive.world.state())
        self.assertEqual(exclusive.cost['invalid'],1)
        self.assertEqual(exclusive.cost['decisions'],1)
        self.assertFalse(shared.act('place_blue_left')['valid'])
        self.assertEqual(shared.world.pick_calls,0)
        self.assertTrue(shared.act('careful_red_left')['valid'])
        self.assertEqual(shared.world.pick_calls,1)

    def test_wait_cost_latched_event_green_retained_and_history_immutable(self):
        ep=self.episode('shared')
        observation=ep.observation()
        result=ep.act('yield')
        self.assertEqual(result['wait']['ticks'],100)
        self.assertEqual(ep.cost['wait_ticks'],100)
        event=copy.deepcopy(ep.world.delivery_event)
        ep.act('careful_red_left')
        self.assertTrue(ep.act('place_blue_left')['success'])
        self.assertEqual(ep.world.delivery_event,event)
        self.assertIsNone(ep.world.regions['green'])
        self.assertEqual(len(observation['history']),3)
        before=ep.world.tick
        self.assertTrue(ep.act('yield')['valid'])
        self.assertEqual(ep.world.tick,before)
        self.assertEqual(ep.cost['wait_ticks'],100)


if __name__=='__main__':
    unittest.main()
