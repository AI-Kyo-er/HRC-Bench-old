"""独立离线核对规范输入、真实物理、成对全前缀及首次尝试定义。"""
import copy
import gzip
import json
import math

from experiments.physical.run import ROOT, save, sha
from experiments.structure_v5.audit import contact_audit
from experiments.structure_v5.run import prefix_digest
from experiments.structure_v7.protocol import SYSTEM, candidates, effective_blue_returns, reduce_history
from experiments.structure_v7.run import FREEZE, source_hashes

RESULT = ROOT / 'results/structure_v7'


def regions(state):
    observed = {}
    for index, item in enumerate(('red', 'blue', 'green')):
        obj = state['objects'][item]
        pos = obj['position']
        velocity = math.sqrt(sum(v * v for v in obj['velocity']))
        targets = [('left', [.59 + .06 * index, -.25]), ('right', [.59 + .06 * index, .25])]
        if item == 'blue':
            targets.append(('neutral', [.65, 0]))
        observed[item] = [t for t, xy in targets if math.dist(pos[:2], xy) < .035 and .025 < pos[2] < .055 and velocity < .04]
    return observed


def first_return_audit(rows):
    """以决策序列定位finish之后；不把同tick的child拒绝误当返回。"""
    finish_index = next((i for i, r in enumerate(rows)
                         if r['result']['choice'] == 'finish_guidance' and r['result']['valid']), None)
    if finish_index is None:
        return dict(answered=False, reason='没有成功终止指导', pre_first_blue_actions=[])
    pre_actions = []
    for index in range(finish_index + 1, len(rows)):
        row = rows[index]
        choice = row['result']['choice']
        blue = choice in {f'{m}_blue_{t}' for m in ('place', 'careful', 'assisted') for t in ('left', 'right')}
        if blue:
            target = reduce_history(row['observation']['history'])['goals']['blue']
            correct = choice.rsplit('_', 1)[1] == target
            prior_reveals = sum(a['blue_target_revealing_feedback'] for a in pre_actions)
            execution = row['result'].get('execution', {})
            return dict(answered=True, decision=index + 1, choice=choice, target_correct=correct,
                valid=row['result']['valid'], physical_attempt=execution.get('physical_attempt', False),
                placement_success=execution.get('success', False),
                blue_target_revealing_feedback_on_first=row['result'].get('target_revealing_feedback', False),
                prior_blue_target_revealing_feedback_after_finish=prior_reveals,
                first_choice_correct_without_prior_blue_target_feedback=correct and prior_reveals == 0,
                first_placement_success_without_prior_blue_target_feedback=execution.get('success', False) and prior_reveals == 0,
                pre_first_blue_actions=pre_actions)
        pre_actions.append(dict(choice=choice,
            target_revealing_feedback=row['result'].get('target_revealing_feedback', False),
            blue_target_revealing_feedback=False))
    return dict(answered=False, reason='finish后没有blue放置尝试，记未作答/未推进', pre_first_blue_actions=pre_actions)


def audit_episode(folder):
    summary = json.loads((folder / 'summary.json').read_text())
    rows = json.loads((folder / 'decisions.json').read_text())
    needed = {r['before_tick'] for r in rows} | {summary['finish_audit']['after']['tick']}
    snapshots = {}
    with gzip.open(folder / 'ticks.jsonl.gz', 'rt') as stream:
        for line in stream:
            state = json.loads(line)
            if state['tick'] in needed:
                snapshots[state['tick']] = state
    checks = []
    for index, row in enumerate(rows):
        observation = row['observation']
        state = snapshots[row['before_tick']]
        history = observation['history']
        expected_next = history + [{'kind': 'action_feedback', 'choice': row['result']['choice'], 'content': row['result']['feedback']}]
        if index + 1 < len(rows):
            next_history = rows[index + 1]['observation']['history']
            # 伙伴/作用域事件插在反馈之前，输入旧历史必须逐项保持前缀。
            prefix_unchanged = next_history[:len(history)] == history
            feedback_present_once = next_history[len(history):].count(expected_next[-1]) == 1
        else:
            prefix_unchanged = feedback_present_once = True
        check = dict(decision=index + 1,
            raw_messages_equal_observation=row['messages'][0] == {'role': 'system', 'content': SYSTEM} and json.loads(row['messages'][1]['content']) == observation,
            physical_objects_exact=observation['physical']['objects'] == state['objects'],
            physical_partner_exact=observation['physical']['partner_position'] == state['partner_position'],
            physical_regions_exact=observation['physical_placements'] == regions(state),
            full_public_menu_exact=observation['candidates'] == candidates(summary['case']['reverse_menu']),
            only_allowed_observation_keys=set(observation) == {'history', 'physical', 'physical_placements', 'remaining_decisions', 'candidates'},
            history_prefix_immutable=prefix_unchanged, feedback_present_once=feedback_present_once,
            budget_exact=observation['remaining_decisions'] == summary['case']['step_budget'] - index)
        check['passed'] = all(v for k, v in check.items() if k != 'decision')
        checks.append(check)
    finish = summary['finish_audit']
    finish_state = snapshots[finish['after']['tick']]
    finish_obs = summary['finish_observation']
    finish_row = next(r for r in rows if r['result']['choice'] == 'finish_guidance')
    first_scoring = first_return_audit(rows)
    first = summary['first_blue_return_attempt']
    first_exact = bool(first_scoring['answered'] and first and first['choice'] == first_scoring['choice'])
    ids = summary['body_ids']
    contacts = contact_audit(folder / 'ticks.jsonl.gz', ids['robot'], ids['partner'], ids['objects'].values())
    prefix = prefix_digest(folder / 'ticks.jsonl.gz', finish['after']['tick'])
    return dict(id=summary['case']['id'], decisions=checks, first_return_scoring=first_scoring,
        passed=all(c['passed'] for c in checks) and finish['before'] == finish['after'] == finish_state and
            finish_obs['physical']['objects'] == finish_state['objects'] and finish_obs['physical_placements'] == regions(finish_state) and
            finish_row['before_tick'] == finish_row['after_tick'] and first_exact and contacts == summary['contact_audit_raw_ticks'] and prefix == summary['prefix_to_finish_trace_sha256'],
        first_blue_attempt_matches_unfiltered_first_blue_action=first_exact,
        finish_event_does_not_restate_outer_blue_target=all('target' not in e and 'goals' not in e for e in finish_obs['history'][-3:]),
        finish_state_exact_matches_raw_tick=finish['after'] == finish_state,
        contacts=contacts, tick_sha256=sha(folder / 'ticks.jsonl.gz'), decisions_sha256=sha(folder / 'decisions.json'),
        prefix_to_finish_sha256=prefix)


def main():
    frozen = json.loads(FREEZE.read_text())
    assert frozen['source_sha256'] == source_hashes()
    output = RESULT / 'raw/reference'
    rows = [audit_episode(output / c['id']) for c in frozen['cases']]
    pair_checks = []
    for seed in (60, 61):
        for reverse in (False, True):
            cases = [c for c in frozen['cases'] if c['seed'] == seed and c['reverse_menu'] == reverse]
            summaries = [json.loads((output / c['id'] / 'summary.json').read_text()) for c in cases]
            no_history = [copy.deepcopy(s['finish_observation']) for s in summaries]
            for obs in no_history:
                del obs['history']
            blue_sets = [effective_blue_returns(s['finish_observation']) for s in summaries]
            # 规范messages同system，删整个history后的user文本也逐字相等。
            no_history_messages = [[{'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': json.dumps(o, ensure_ascii=False)}] for o in no_history]
            passed = (no_history_messages[0] == no_history_messages[1] and
                not (set(blue_sets[0]) & set(blue_sets[1])) and
                summaries[0]['finish_audit']['after'] == summaries[1]['finish_audit']['after'] and
                summaries[0]['prefix_to_finish_trace_sha256'] == summaries[1]['prefix_to_finish_trace_sha256'])
            pair_checks.append(dict(seed=seed, reverse_menu=reverse, ids=[c['id'] for c in cases],
                without_history_messages_byte_equal=no_history_messages[0] == no_history_messages[1],
                effective_blue_return_actions=blue_sets, passed=passed))
    report = dict(total_episodes=len(rows), total_decisions=sum(len(r['decisions']) for r in rows),
        all_passed=all(r['passed'] and r['finish_event_does_not_restate_outer_blue_target'] for r in rows) and all(p['passed'] for p in pair_checks),
        episodes=rows, pairs=pair_checks, freeze_sha256=sha(FREEZE), auditor_source_sha256=sha(ROOT / 'experiments/structure_v7/audit.py'),
        scope='只审计实际规则输入与物理；未运行模型，错误目标拒绝/恢复仅永久FactsWorld协议回归；首次错误拒绝不能在评分时删除。')
    save(RESULT / 'input_and_pair_audit.json', report)
    assert report['all_passed']
    print('v7审计', len(rows), report['total_decisions'], 'all_passed', report['all_passed'], flush=True)


if __name__ == '__main__':
    main()
