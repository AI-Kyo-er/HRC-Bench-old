"""派生评分与初始化注解边界；不运行新物理。"""
import unittest
from experiments.transport_goal_v17.audit import actual_regions,availability_for_input

class AuditTests(unittest.TestCase):
    def test_regions_both_endpoints_no_declared_goal_argument(self):
        for destination,y in (('left',-.25),('right',.25)):
            objects={'blue':{'position':[.65,y,.036],'velocity':[0,0,0]}}
            self.assertEqual(actual_regions(objects,'blue'),[destination])
            objects['blue']['velocity']=[.1,0,0];self.assertEqual(actual_regions(objects,'blue'),[])
    def test_constructor_tick_annotation_then_real_tick(self):
        summary={'common_start_tick':180,'initial_state':{'availability':{'common_start_tick':180,'status':'ready'}}}
        before={'availability':{'common_start_tick':None,'status':'ready'}}
        after={'availability':{'common_start_tick':180,'status':'ready','physics_tick':181}}
        self.assertEqual(availability_for_input(summary,before,180),summary['initial_state']['availability'])
        self.assertEqual(availability_for_input(summary,after,181),after['availability'])

if __name__=='__main__':unittest.main()
