"""返程顺序的公开策略与原源保持；均为协议/元数据回归。"""
import copy
import json
import unittest
from experiments.physical.run import ROOT
from experiments.sustained_structure_v21.protocol import Episode
from experiments.sustained_structure_v21.run import hashes
from experiments.sustained_structure_v21.run_r1 import reference_r1,cases
from tests.test_sustained_structure_v21 import FactsWorld


class ReturnOrderTests(unittest.TestCase):
    def observation(self,initial='left',reply='rejected'):
        ep=Episode(FactsWorld(),initial,reply,'stay','H')
        ep._append(dict(kind='transport_request_reply',decision='accepted'))
        ep.world.regions['red']=['left'];ep.world.regions['blue']=[]
        return ep.observation()

    def test_both_robot_targets_buffer_before_return(self):
        for initial in ('left','right'):
            o=self.observation(initial)
            self.assertEqual(reference_r1(o),'place_blue_inspection')
            o['physical_placements']['blue']=['inspection']
            self.assertEqual(reference_r1(o),'request_return')
            o['history'].append(dict(kind='return_request_accepted'))
            self.assertEqual(reference_r1(o),'yield')
            o['carrier_return_event']={'first_tick':1}
            self.assertEqual(reference_r1(o),'place_blue_'+initial)

    def test_partner_stays_loaded_until_actual_return(self):
        o=self.observation(reply='accepted')
        self.assertEqual(reference_r1(o),'request_return')
        o['history'].append(dict(kind='return_request_accepted'))
        self.assertEqual(reference_r1(o),'yield')
        o['carrier_return_event']={'first_tick':1}
        self.assertEqual(reference_r1(o),'yield')
        o['payload_return_event']={'first_tick':2}
        self.assertEqual(reference_r1(o),'careful_green_right')

    def test_green_only_after_actual_return_and_final_blue(self):
        o=self.observation();o['history'].append(dict(kind='return_request_accepted'))
        o['carrier_return_event']={'first_tick':1};o['physical_placements']['blue']=['left']
        self.assertEqual(reference_r1(o),'careful_green_right')
        o['physical_placements']['green']=['right']
        self.assertEqual(reference_r1(o),'declare_done')

    def test_original_C_runtime_exact_and_matrices_unchanged(self):
        f=json.loads((ROOT/'experiments/sustained_structure_v21/cases/C_freeze_dev0.json').read_text())
        self.assertEqual(f['source_sha256'],hashes())
        self.assertEqual([r['control'] for r in cases('C_return')],[6,7])
        self.assertEqual(len(cases('H')),4)


if __name__=='__main__':unittest.main()
