"""本条冻结抽屉开发例的来源审阅；草稿留在前缀目录，终态核验后才发布。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from hrc_pilot.joint_review_evidence import pointer_value, verify_review
from hrc_pilot.reviewed_coordination_metrics import reviewed_metrics


RUN = 'candidate_drawer_leave_return_symbolic_20261009'


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))


def prepare(root):
    source = {}
    for name in ['human_policy_io', 'robot_planner_io', 'trace',
                 'human_command_receipts', 'public_dialogue', 'placement_evidence']:
        path = root / 'episode' / (name + '.jsonl')
        source[name] = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def index(name, time):
        return next(i for i, row in enumerate(source[name]) if abs(row['time_s'] - time) < 1e-6)

    def anchor(name, row, pointer):
        return {'file': 'episode/' + name + '.jsonl', 'row': row, 'pointer': pointer,
                'equals': pointer_value(source[name][row], pointer)}

    def at(name, time, pointer):
        return anchor(name, index(name, time), pointer)

    def h(time, pointer):
        return at('human_policy_io', time, pointer)

    def r(time, pointer):
        return at('robot_planner_io', time, pointer)

    def t(time, pointer):
        return at('trace', time, pointer)

    def dialogue(time, speaker):
        return next(i for i, row in enumerate(source['public_dialogue'])
                    if row['time_s'] == time and row['speaker'] == speaker)

    if source['human_policy_io'][index('human_policy_io', 12)]['choice']['destination'] != 'drawer_storage':
        raise ValueError('本条案例的实际选择已不同，不能套用既有解释')
    first = next(i for i, row in enumerate(source['placement_evidence']) if row['native_physical_goal_success'])
    if source['placement_evidence'][first]['time_s'] != 11.3:
        raise ValueError('首次开门见证不同，须重新人工审阅')
    for time in [28, 32]:
        if source['human_policy_io'][index('human_policy_io', time)]['choice']['action'] != 'pause_current':
            raise ValueError('本条实际暂停选择不同')
    receipt = next(i for i, row in enumerate(source['human_command_receipts']) if row['request_id'] == 11)
    if source['human_command_receipts'][receipt]['effect'] != 'already_at_requested_supported_position':
        raise ValueError('44秒请求并非既有位置满足，须重新审阅贡献')

    findings = []
    def finding(label, interpretation, evidence):
        findings.append({'label': label, 'interpretation': interpretation, 'evidence': evidence})

    finding('Robot实际开门，Human据可达线索开始存物',
        '人0秒公开请求开中抽屉，Robot实际选择开门，11.3秒首次原生关节稳定见证。人12秒看到可达开口后选择Cream到抽屉。开门与存物是不同主体贡献，开门不等于整个共同活动完成。',
        [h(0, '/choice/message'), r(0, '/model_selected_skill_id'),
         anchor('placement_evidence', first, ''), h(12, '/choice'),
         h(12, '/private_agenda_inference/request/current_observation/drawer_measurement')])
    finding('自己的搬运被误归Robot',
        '人16/20/24秒说Robot取、举和插入Cream；实际own_execution分别是自己的取物接近、抬升和搬运，Robot16秒后保持并公开说Human在处理。有效实物依赖与伙伴角色误判分开。',
        [h(16, '/choice/message'), h(16, '/private_input/scene/own_execution'),
         h(20, '/choice/message'), h(20, '/private_input/scene/own_execution'),
         h(24, '/choice/message'), h(24, '/private_input/scene/own_execution'), r(16, '/decision')])
    finding('私人记忆与可用事实矛盾',
        '人36秒意图记忆仍写Robot尚未执行、Plate由本人持有，当前意图输入则明确actor=human、持Cream且原搬运已取消，并有Robot公开说明。60秒理解又把Cream存入归Robot。现有事实输入并未可靠约束内部解释，不能将伙伴视为已合格。',
        [h(36, '/private_agenda_inference/agenda_after/private_memory'),
         h(36, '/private_agenda_inference/request/current_observation/own_execution'),
         h(36, '/private_agenda_inference/request/current_observation/public_partner_statements_not_execution_facts'),
         h(60, '/private_agenda_inference/agenda_after/understood_shared_arrangement')])
    finding('有效公开暂停与当前参与变化',
        '22.6秒紧急私人联系后，人28/32秒选pause_current并公开暂停，实际保留Cream、取消请求3。Robot28秒公开认可，但16秒已保持，不把28秒当首次停止触发。操作暂停与身体离开另判。',
        [h(28, '/observation_source_scene/private_context'), h(28, '/choice'), h(32, '/choice'),
         t(32, '/human_execution'), r(16, '/decision/mode'), r(28, '/decision/message'), t(32, '/human_body_xy')])
    finding('同一世界内恢复，未重置贡献',
        '人36秒重新选择Cream到抽屉，Robot同轮公开认可恢复；32与36秒保留同一持物和打开的抽屉，未清空进度。人可以自主提前恢复，但其理由说联系已经处理，在当时实际私人信息中没有结束消息，不认证由59.2秒结束cue触发的返回。',
        [h(36, '/choice'), h(36, '/observation_source_scene/private_context'), r(36, '/decision/message'),
         t(32, '/human_execution/held_object'), t(36, '/human_execution/held_object'),
         t(32, '/articulated_joints'), t(36, '/articulated_joints')])
    finding('Cream实际释放并接触中抽屉底面',
        '43.95秒Cream已离手，其真实碰撞盒与g27底面接触；48秒仍支持。声明区域碰撞盒包含的七帧重建另见前缀几何记录。此处底面与释放见证不代替全部抽屉几何或Robot搬运成绩。',
        [t(43.95, '/human_execution/held_object'), t(43.95, '/contacts'),
         t(48, '/observable_world/released_object_support_contacts/cream_cheese_1'), h(44, '/choice/message')])
    finding('Plate后续请求没有新增搬运',
        '人44秒说现在移动Plate到个人位置，但请求11回执是already_at_requested_supported_position。Plate在之前处理Cream请求时已由自动暂放执行清出；不能把44秒无运动满足另计一次新增贡献。',
        [h(44, '/selected_tool_call'), anchor('human_command_receipts', receipt, ''),
         t(44, '/objects/plate_1'), t(48, '/objects/plate_1')])
    finding('完成表达有实物前提，贡献归属仍误记',
        '48秒人公开全部完成，Robot认可人存物和处理Plate；60秒新的私人消息已进入人的实际输入，仍选择结束。在已完成需要下没有强迫身体返回，但该条不能认证暂离返回能力，也不能将内部误记当正确共同理解。',
        [h(48, '/choice/message'), r(48, '/decision/message'),
         h(60, '/observation_source_scene/private_context'), h(60, '/choice'),
         t(48, '/human_body_xy'), t(48, '/human_execution/held_object')])
    process_evidence = root / 'joint_process_evidence.json'
    if process_evidence.exists():
        measured = json.loads(process_evidence.read_text())
        observations = measured['original_arrangement_physical_observations']
        if observations['first_physical_match_s'] != 41.4 or not observations['last_second_consistently_matches']:
            raise ValueError('完整释放支撑结果不同，须重新审阅')
        findings.append({'label': '完整原安排的释放支撑与终态',
            'interpretation': '原安排首次物理匹配为41.4秒，末秒持续匹配；开门由Robot执行、存物由Human执行。summary的44.05秒完成见证对应请求11的既有位置满足，原搬运请求9被取消，不计原请求自然退手完成或新增搬运。完整物理匹配不自动认证共享理解、离返或cobalance。',
            'evidence': [{'file': 'joint_process_evidence.json',
                'pointer': '/original_arrangement_physical_observations', 'equals': observations},
                t(41.4, '/human_execution/held_object'), t(44.05, '/human_execution'),
                anchor('human_command_receipts', receipt, '/effect'), t(120, '/human_execution/held_object')]})
        contact = measured['shared_resource_execution']['robot_gripper_contact_with_human_owned']
        findings.append({'label': '保持时的人持物夹爪接触',
            'interpretation': '19.85至21.6秒Robot保持期间，原始夹爪与人持Cream接触累计1.75秒；同资源VLA暴露0不表示没有接触。该测量不含全身接触、力或合法交接判断，不能自动给安全分数。',
            'evidence': [{'file': 'joint_process_evidence.json',
                'pointer': '/shared_resource_execution/robot_gripper_contact_with_human_owned', 'equals': contact}]})
        geometry = root / 'drawer_region_verification.json'
        if geometry.exists():
            region = json.loads(geometry.read_text())
            if not all(row['whole_collision_box_inside'] and row['held_object'] is None and row['bottom_contact']
                       for row in region['checks']):
                raise ValueError('声明区域内释放包含的检查不成立')
            findings.append({'label': '声明区域的首次释放帧及末秒包含',
                'interpretation': '独立CPU重建41.4秒及119至120秒全部采样共22帧，Cream完整碰撞盒在资产原箱形中抽屉region内、离手且接触真实底面。只证明所查采样的声明区域包含，不认证视觉mesh、全身安全、整段稳定时间或共享约定。',
                'evidence': [{'file': 'drawer_region_verification.json', 'pointer': '/scope', 'equals': region['scope']},
                    {'file': 'drawer_region_verification.json', 'pointer': '/checks', 'equals': region['checks']}]})
    review = {'review_type': 'assistant_review_of_saved_records_not_human_study',
        'formal_benchmark_score': None, 'findings': findings,
        'interpretation': '真实Robot开门与Human存物形成跨主体依赖，公开暂停与恢复保留同一进度；人的内部解释和部分公开话语误记执行主体。当前证据不认证可靠伙伴、身体离返、全部六情境或cobalance。'}

    intervals = []
    def interval(label, start, end, interpretation, evidence):
        intervals.append({'label': label, 'start': start, 'end': end,
                          'interpretation': interpretation, 'evidence': evidence})
    def public(time, speaker):
        return anchor('public_dialogue', dialogue(time, speaker), '/time_s')
    interval('开门请求到首次物理见证', public(0, 'human'),
        t(11.3, '/time_s'),
        '11.3秒是本例请求后首次稳定开门见证，不是总体模型响应性能或协作总分。',
        [r(0, '/model_selected_skill_id'), anchor('placement_evidence', first, '/native_physical_goal_success')])
    interval('公开暂停到自主恢复', public(28, 'human'), public(36, 'human'),
        '8秒为公开暂停到恢复窗口。Robot在此前已保持；身体没有在此窗口离开。人自述电话处理完与已收到的外部消息分开。',
        [h(28, '/choice/action'), h(32, '/choice/action'), h(36, '/choice/action'), r(16, '/decision/mode')])
    interval('恢复到完整记录的首次释放支撑', public(36, 'human'), t(41.4, '/time_s'),
        '5.4秒为恢复公开表达到完整记录首次释放支撑帧，包含人低层执行，不认证Robot搬运或身体返回。',
        [h(36, '/choice/destination'), t(41.4, '/human_execution/held_object'),
         t(41.4, '/observable_world/released_object_support_contacts/cream_cheese_1')])
    interval('完成表达后的保持窗口', public(48, 'human'), public(60, 'robot'),
        '完成表达有实物前提。12秒是实际保持窗口，不自动解释为无谓等待；公开完成与内部主体误记另判。',
        [h(48, '/choice/message'), r(60, '/decision/mode')])
    if process_evidence.exists():
        interval('已释放存物到整段终态', t(41.4, '/time_s'), t(120, '/time_s'),
            '78.6秒为首次释放支撑到终态的观察窗口，不是额外工作贡献，也不将保持自动记为无谓等待。',
            [{'file': 'joint_process_evidence.json',
              'pointer': '/original_arrangement_physical_observations/last_second_consistently_matches', 'equals': True}])
    process = {'review_type': review['review_type'], 'formal_benchmark_score': None,
               'reviewed_intervals': intervals}
    return review, process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draft', action='store_true')
    args = parser.parse_args()
    root = Path('results/continuous_v2') / RUN
    if not args.draft:
        for name in ['interaction_verification.json', 'independent_video_verification.json']:
            if json.loads((root / name).read_text())['status'] != 'verified':
                raise ValueError('完整独立核查尚未通过')
        provenance = json.loads((root / 'provenance.json').read_text())
        if (root / 'failure.json').exists() or provenance['steps'] != 2400 or provenance['source_files_changed_during_run']:
            raise ValueError('不满预定范围、失败或运行源码变化，不能发布完整案例')
    review, process = prepare(root)
    if args.draft:
        output = Path('results/candidate_joint_prefix_20261009/drawer_review_draft.json')
        write(output, {'role': 'unpublished_prefix_review_not_terminal', 'review': review, 'process': process,
                       'reviewer_source_sha256': sha256(Path(__file__).read_bytes()).hexdigest()})
        print('已保存前缀草稿，不生成正式案例或成绩')
        return
    write(root / 'public_request_response_review.json', review)
    write(root / 'coordination_process_review.json', process)
    write(root / 'review_evidence_verification.json', verify_review(root))
    write(root / 'reviewed_coordination_metrics.json', reviewed_metrics(root))
    print(json.dumps({'findings': len(review['findings']), 'intervals': len(process['reviewed_intervals']),
                      'formal_score': None}, ensure_ascii=False))


if __name__ == '__main__':
    main()
