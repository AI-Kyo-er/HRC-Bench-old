"""按保存物理帧重放家具面接受／拒绝；不认证意图或选择另一策略。"""
import numpy as np

from .fixture_area_human_executor import CONTRACT, fixture_placement_areas
from .fixture_surface_placement import fixture_surface_placement
from .geometry_frame_replay import replay_recorded_geometry
from .placement_areas import PlacementAreaFull


def verify_fixture_receipts(provenance, trace, human, receipts, sim, regions):
    marker=provenance.get('human_fixture_surface_contract')
    tagged=[r for r in receipts if 'fixture_surface_placement' in r or 'fixture_surface_rejection' in r]
    if marker is None:
        if tagged:raise ValueError('旧协议不能出现未声明的家具面执行证据')
        return []
    if marker!=CONTRACT:raise ValueError('未知家具面执行协议')
    by_id={row['decision_id']:row for row in human}
    result=[]
    for receipt in tagged:
        decision=by_id[receipt['request_id']];choice=decision['choice']
        if choice['action'] not in {'place','relocate'} or not choice.get('object_id'):
            raise ValueError('家具面记录必须来自真实选定放置')
        allocation=receipt.get('fixture_surface_placement')
        physics_time=allocation['planning_physics_time_s'] if allocation else receipt['physics_time_s']
        index=round((physics_time-trace[0]['physics_time_s'])*20)
        if not 0<=index<=round(decision['time_s']*20):raise ValueError('规划帧不能来自未来')
        actual=trace[index]
        frame=replay_recorded_geometry(sim.model._model,sim.data._data,actual)
        areas=fixture_placement_areas(sim.model,sim.data,list(actual['objects']),regions)
        dest=choice['destination'];obj=choice['object_id']
        if dest not in areas:raise ValueError('所选目标不是可测家具面')
        surface=areas[dest]['fixture_surface']
        if allocation:
            if not receipt['accepted']:raise ValueError('拒绝不能冒充已执行放置')
            if allocation['object_id']!=obj or allocation['fixture_id']!=surface['fixture_id']:
                raise ValueError('已接受参数必须属于本次所选物品和家具')
            for payload in allocation['payload_names']:
                from .libero_native import perceived_object_contacts
                contacts=perceived_object_contacts(actual)[payload]
                if contacts['robot_hand_contact']:raise ValueError('不能代替Robot携带物品')
                if not (obj in contacts['contact_entities'] or
                        (actual['human_execution']['held_object']==obj and payload in actual['human_execution']['carried_objects'])):
                    raise ValueError('载荷必须有实际归属／支撑依据')
            computed=fixture_surface_placement(sim.model,sim.data,obj,surface,list(actual['objects']),
                payload_names=allocation['payload_names'],preferred_xy=allocation['preferred_xy'])
            np.testing.assert_allclose(allocation['body_target_xyz'],computed['body_target_xyz'],atol=.0002,rtol=0)
            assert allocation['support_geom']==computed['support_geom']
            status='selected_surface_point_replayed'
        else:
            if receipt['accepted'] or receipt['error']!='destination_area_has_no_free_placement':
                raise ValueError('家具面拒绝标签与实际接受状态不同')
            rejection=receipt['fixture_surface_rejection']
            if rejection['destination']!=dest or rejection['fixture_id']!=surface['fixture_id']:
                raise ValueError('不能把别的目标的拒绝套到本次请求')
            payloads=rejection['payload_names']
            from .libero_native import perceived_object_contacts
            for payload in payloads:
                contacts=perceived_object_contacts(actual)[payload]
                if contacts['robot_hand_contact'] or not (obj in contacts['contact_entities'] or
                        (actual['human_execution']['held_object']==obj and payload in actual['human_execution']['carried_objects'])):
                    raise ValueError('拒绝所用载荷需要真实归属依据')
            preferred=rejection['preferred_xy']
            np.testing.assert_allclose(preferred,actual['objects'][obj][:2],atol=.000001,rtol=0)
            try:
                fixture_surface_placement(sim.model,sim.data,obj,surface,list(actual['objects']),
                    payload_names=payloads,preferred_xy=preferred)
            except PlacementAreaFull:
                status='recorded_no_free_point_replayed'
            else:raise ValueError('存在安全候选，不能认证此处拒绝')
        result.append({'request_id':receipt['request_id'],'frame_index':index,'status':status,'geometry_frame':frame})
    return result
