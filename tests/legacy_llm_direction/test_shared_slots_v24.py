"""v24公开事实/独立审计反例；不代替8真实物理。"""
import copy
import unittest
from experiments.shared_slots_v24.run import cases,waiting_satisfied,PREFIX,CONFIG
from experiments.shared_slots_v24.audit import destination_facts,recovery_exposed,preserved_within


class SharedSlotsTests(unittest.TestCase):
    def test_eight_fixed_cases_and_sources(self):
        cs=cases();self.assertEqual(len(cs),8)
        self.assertEqual({c['id'] for c in cs},{f'{n}_{s}' for n in 'ABCD' for s in (120,121)})
        self.assertTrue(all(c['commands'][:6]==PREFIX for c in cs))
        self.assertTrue(all('request_check' not in c['commands'] for c in cs))
        self.assertEqual(CONFIG['blue_route'],'direct');self.assertEqual(CONFIG['green_route'],'careful')

    def test_wait_requires_current_far_and_idle(self):
        s=dict(cycle=dict(active=2),current_carrier_facts=dict(far=True,near=False,payload_stable=False),return_event=dict(first_tick=10))
        self.assertFalse(waiting_satisfied(s,'wait_far_empty'))
        s['cycle']['active']=None;self.assertTrue(waiting_satisfied(s,'wait_far_empty'))
        s['current_carrier_facts']['far']=False;self.assertFalse(waiting_satisfied(s,'wait_far_empty'))

    def test_near_wait_requires_payload(self):
        s=dict(cycle=dict(active=None),current_carrier_facts=dict(far=False,near=True,payload_stable=False))
        self.assertFalse(waiting_satisfied(s,'wait_near_payload'))
        s['current_carrier_facts']['payload_stable']=True;self.assertTrue(waiting_satisfied(s,'wait_near_payload'))

    def test_position_without_real_support_is_insufficient(self):
        ids=dict(objects=dict(red=1,blue=2,green=3),trays=dict(left=5,right=6))
        s=dict(objects=dict(green=dict(position=[.71,-.25,.032],velocity=[0,0,0])),contacts=[])
        f=destination_facts(s,'green','left',ids)
        self.assertTrue(f['stable']);self.assertFalse(f['supported'])
        s['contacts']=[dict(body_a=3,body_b=5,contact_distance=0.,normal_force=.1)]
        self.assertTrue(all(destination_facts(s,'green','left',ids).values()))
        s['contacts'][0]['normal_force']=0.;self.assertFalse(destination_facts(s,'green','left',ids)['supported'])

    def test_wrong_tray_contact_not_support(self):
        ids=dict(objects=dict(green=3),trays=dict(left=5,right=6))
        s=dict(objects=dict(green=dict(position=[.71,-.25,.032],velocity=[0,0,0])),contacts=[dict(body_a=3,body_b=6,contact_distance=0,normal_force=.1)])
        self.assertFalse(destination_facts(s,'green','left',ids)['supported'])

    def test_continuous_preservation_not_only_final(self):
        self.assertTrue(preserved_within(dict(red=.0002,blue=.0001)))
        self.assertFalse(preserved_within(dict(red=.02,blue=0.)))
        self.assertFalse(preserved_within(dict(red=.01)))

    def test_return_requires_intermediate_actual_destination_and_motion(self):
        case=dict(sequence='C');tail=[]
        for i,choice in enumerate(CONFIG['sequences']['C'],6):
            _,item,target=choice.split('_');tail.append(dict(sequence=i,choice=choice,item=item,target=target,actual_destination=True,physical_attempt=True,source_displacement_m=.5))
        self.assertTrue(recovery_exposed(case,tail))
        bad=copy.deepcopy(tail);bad[2]['actual_destination']=False;self.assertFalse(recovery_exposed(case,bad))
        bad=copy.deepcopy(tail);bad[2]['source_displacement_m']=0.;self.assertFalse(recovery_exposed(case,bad))
        self.assertFalse(recovery_exposed(case,[tail[-1]]))

    def test_blue_and_green_recovery_both_ordered(self):
        for name in ('C','D'):
            tail=[]
            for i,choice in enumerate(CONFIG['sequences'][name],6):
                _,item,target=choice.split('_');tail.append(dict(sequence=i,choice=choice,item=item,target=target,actual_destination=True,physical_attempt=True,source_displacement_m=.5))
            self.assertTrue(recovery_exposed(dict(sequence=name),tail))
            self.assertFalse(recovery_exposed(dict(sequence=name),list(reversed(tail))))


if __name__=='__main__':unittest.main()
