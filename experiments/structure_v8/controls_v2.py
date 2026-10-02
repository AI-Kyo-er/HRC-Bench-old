"""三开发控制，失败也原样归档；不调nominal速度制造等待效果。"""
import copy
import json
import math

from experiments.physical.run import ROOT, save, sha, versions, asset_hashes
from experiments.structure_v5.audit import contact_audit
from experiments.structure_v5.run import keyframe
from experiments.structure_v8.world_v2 import TransportWorld, CONFIG_PATH, CONFIG

RESULT = ROOT / 'results/structure_v8'


def review(world, initial, intervals, executions, wait_ticks):
    final = copy.deepcopy(world.state())
    event = copy.deepcopy(world.delivery_event)
    overlap = 0
    red = next((i for i in intervals if i['item'] == 'red'), None)
    if event and red:
        overlap = max(0, min(red['end'], event['first_tick']) - max(red['start'], world.delivery_start_tick))
    green_displacement = math.dist(initial['objects']['green']['position'], final['objects']['green']['position'])
    goals = {item: world.at_goal(item, 'left') for item in ('red', 'blue')}
    success = all(goals.values()) and event is not None
    return dict(delivery_event=event, final_state=final, initial_state=initial,
        goals=goals, goal_first_ticks=world.goal_first_ticks,
        delivery_start_tick=world.delivery_start_tick, end_tick=world.tick,
        closed_task_makespan_ticks=world.tick-world.delivery_start_tick, makespan_includes_final_robot_parking=True,
        red_skill_transport_overlap_ticks=overlap, overlap_includes_skill_dwell_and_parking=True,
        robot_intervals=intervals, executions=executions, wait_ticks=wait_ticks,
        green_displacement=green_displacement, green_preserved=green_displacement < .01,
        success=success, robot_partner_online=copy.deepcopy(world.contact_audit),
        other_objects_partner_online=copy.deepcopy(world.object_partner_audit),
        expected_blue_carrier_support_online=copy.deepcopy(world.support_audit),
        non_target_robot_online=copy.deepcopy(world.non_target_robot_audit),
        body_ids=dict(robot=world.robot, partner=world.partner, objects=dict(world.objects)))


def offline_contacts(folder, summary):
    ids = summary['body_ids']
    # blue承载接触属于贡献，禁止组只包含red/green，不沿用全部object-partner零。
    audit = contact_audit(folder / 'ticks.jsonl.gz', ids['robot'], ids['partner'], [ids['objects'][x] for x in ('red', 'green')])
    assert audit['robot_partner']['ticks'] == summary['robot_partner_online']['robot_partner_ticks']
    assert audit['object_partner']['ticks'] == summary['other_objects_partner_online']['ticks']
    assert audit['total_ticks'] == summary['robot_partner_online']['total_ticks']
    return audit


def main():
    output = RESULT / 'raw/controls_dev2'
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError('禁止覆盖开发控制。')
    records = []
    for kind in ('transport_only', 'serial_handoff', 'overlap_handoff'):
        folder = output / kind
        folder.mkdir()
        world = TransportWorld(70, trace_path=folder / 'ticks.jsonl.gz')
        intervals, executions, wait_ticks = [], [], 0
        try:
            initial = copy.deepcopy(world.state())
            assert world.delivery_event is None
            keyframe(world, folder / 'frames')
            world.start_delivery()
            if kind != 'overlap_handoff':
                waited = world.wait_delivery(); wait_ticks += waited['ticks']
                keyframe(world, folder / 'frames')
            if kind != 'transport_only':
                before = world.tick
                red = world.pick_place('red', 'left', 'careful')
                executions.append(red); intervals.append(dict(item='red', start=before, end=world.tick))
                keyframe(world, folder / 'frames')
                if kind == 'overlap_handoff':
                    waited = world.wait_delivery(); wait_ticks += waited['ticks']
                    keyframe(world, folder / 'frames')
                before = world.tick
                blue = world.pick_place('blue', 'left', 'direct')
                executions.append(blue); intervals.append(dict(item='blue', start=before, end=world.tick))
                keyframe(world, folder / 'frames')
            summary = review(world, initial, intervals, executions, wait_ticks)
            summary['kind'] = kind
        finally:
            world.close()
        audit = offline_contacts(folder, summary)
        summary['contact_audit_raw_ticks'] = audit
        support = summary['expected_blue_carrier_support_online']
        summary['passed'] = bool(summary['delivery_event'] and audit['zero_record_passed'] and
            audit['all_missing_distance_records'] == 0 and summary['green_preserved'] and
            support['transport_supported_ticks'] == support['transport_ticks'] and
            (kind == 'transport_only' or (summary['success'] and all(e['success'] for e in executions))) and
            (kind != 'overlap_handoff' or summary['red_skill_transport_overlap_ticks'] > 0))
        save(folder / 'summary.json', summary)
        records.append(summary)
        print(kind, 'pass', summary['passed'], 'delivery', summary['delivery_event'],
              'wait_ticks', wait_ticks, 'overlap_ticks', summary['red_skill_transport_overlap_ticks'],
              'robot_carrier', audit['robot_partner']['ticks'], 'other_carrier', audit['object_partner']['ticks'], flush=True)
    save(RESULT / 'control_dev2_summary.json', dict(cases=len(records), passed=sum(r['passed'] for r in records),
        all_passed=all(r['passed'] for r in records), config=CONFIG, config_sha256=sha(CONFIG_PATH),
        source_sha256={n:sha(ROOT/n) for n in ('experiments/structure_v8/world_v2.py','experiments/structure_v8/controls_v2.py')},
        packages=versions(), assets_sha256=asset_hashes(),
        cases_summary=[{k:r[k] for k in ('kind','passed','wait_ticks','red_skill_transport_overlap_ticks','closed_task_makespan_ticks','green_preserved')} for r in records],
        total_ticks=sum(r['contact_audit_raw_ticks']['total_ticks'] for r in records),
        robot_partner_ticks=sum(r['contact_audit_raw_ticks']['robot_partner']['ticks'] for r in records),
        other_objects_partner_ticks=sum(r['contact_audit_raw_ticks']['object_partner']['ticks'] for r in records),
        expected_support_records=sum(r['expected_blue_carrier_support_online']['records'] for r in records)))
    print('开发控制', len(records), sum(r['passed'] for r in records), flush=True)


if __name__ == '__main__':
    main()
