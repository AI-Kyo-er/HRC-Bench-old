"""可复现的机制验收；没有学习模型，也没有物理仿真。"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

CONDITIONS = ('isolated', 'concatenated', 'dependent', 'concurrent', 'closed_loop')
POLICIES = ('full_state', 'memoryless_tie', 'single_constraint', 'fixed_response', 'solo_robust')


def generate(seed: int, variant: int, condition: str, source: str, steps: int = 12):
    """variant 翻转历史目标；dependent 当前场景完全相同。"""
    rng = random.Random(seed)
    jobs = []
    for i in range(steps):
        target = rng.randrange(2) ^ variant
        route = rng.randrange(2)
        accepts = rng.random() < .75
        compound = condition in ('concurrent', 'closed_loop')
        jobs.append({
            'cue': {'source': 'person' if source == 'human' else 'system', 'target': target, 'item': i},
            'scene': {'item': i, 'target': target if condition in ('isolated', 'concatenated') else None,
                      'open_route': route if compound else 0, 'needs_support': compound},
            'truth': {'target': target, 'accepts': accepts if condition == 'closed_loop' else True},
            'reset_each': condition == 'isolated',
        })
    return jobs


def observe_size(obs):
    # 字符长度，不声称模型 tokenizer 的 token 数。
    return len(json.dumps(obs, sort_keys=True, separators=(',', ':')))


def rollout(jobs, policy, source):
    counts = dict(completed=0, commitment_violations=0, unsafe_attempts=0,
                  requests=0, rejections=0, waits=0, decision_opportunities=0,
                  observation_chars=0, observations=0, action_cost=0,
                  clairvoyant_min_cost=0)
    trace = []
    memory = {}
    if jobs and not jobs[0]['reset_each']:
        cues = [job['cue'] for job in jobs]
        memory = {cue['item']: cue['target'] for cue in cues}
        counts['observation_chars'] += sum(map(observe_size, cues))
        counts['observations'] += len(cues)
        trace.append({'phase': 'initial_instructions', 'public_observations': cues})
    for job in jobs:
        cue, scene, truth = job['cue'], job['scene'], job['truth']
        if job['reset_each']:
            memory = {cue['item']: cue['target']}
            public = [cue, scene]
        else:
            public = [scene]
        counts['observation_chars'] += sum(map(observe_size, public))
        counts['observations'] += len(public)
        target = scene['target'] if scene['target'] is not None else (
            0 if policy == 'memoryless_tie' else memory[scene['item']])
        route = 0 if policy == 'single_constraint' else scene['open_route']
        support = scene['needs_support']
        granted = False
        actions = []
        if support and policy != 'solo_robust':
            counts['requests'] += 1
            counts['decision_opportunities'] += 1
            counts['action_cost'] += 1
            # 伙伴仅收到公开 request(item)，不能查看策略内部状态。
            response = {'source': 'person' if source == 'human' else 'system', 'item': scene['item'],
                        'response': 'accept' if truth['accepts'] else 'reject'}
            public.append(response)
            counts['observation_chars'] += observe_size(response)
            counts['observations'] += 1
            counts['rejections'] += int(not truth['accepts'])
            granted = truth['accepts']
            actions.append({'type': 'request', 'item': scene['item']})
            method = 'assist' if (granted or policy == 'fixed_response') else 'solo'
        else:
            method = 'solo'
        action = {'type': 'place', 'target': target, 'route': route, 'method': method}
        actions.append(action)
        wrong_target = target != truth['target']
        unsafe = route != scene['open_route'] or (support and method == 'assist' and not granted)
        counts['commitment_violations'] += int(wrong_target)
        counts['unsafe_attempts'] += int(unsafe)
        counts['completed'] += int(not wrong_target and not unsafe)
        counts['decision_opportunities'] += 1
        counts['action_cost'] += 4 if support and method == 'solo' else 1
        counts['clairvoyant_min_cost'] += (2 if truth['accepts'] else 4) if support else 1
        trace.append({'public_observations': public, 'actions': actions,
                      'completed': not wrong_target and not unsafe})
    counts['episode_success'] = int(counts['completed'] == len(jobs))
    counts['progress_steps'] = len(jobs)
    counts['shortest_feasible_action_count'] = len(jobs)  # 全部 solo 的1次宏动作/物品
    return counts, trace


def verify_mechanisms():
    """验收观测混叠、最优解和非社会同构，而非检验预期弱策略分数。"""
    for seed in range(20):
        for condition in CONDITIONS:
            a = generate(seed, 0, condition, 'human')
            b = generate(seed, 1, condition, 'human')
            if condition in ('dependent', 'concurrent', 'closed_loop'):
                assert [j['scene'] for j in a] == [j['scene'] for j in b]
                assert all(x['truth']['target'] != y['truth']['target'] for x, y in zip(a, b))
            machine = generate(seed, 0, condition, 'machine')
            for policy in POLICIES:
                h, _ = rollout(a, policy, 'human')
                m, _ = rollout(machine, policy, 'machine')
                # human/machine 仅改变长度相同的来源标签。
                assert h == m
            for policy in ('full_state', 'solo_robust'):
                result, _ = rollout(a, policy, 'human')
                assert result['episode_success'] == 1
    return {'counterfactual_scene_identity': True, 'opposite_required_targets': True,
            'human_machine_isomorphism': True, 'strong_baselines_solve': True,
            'tested_seeds': 20}


def run(seeds, steps, output):
    output.mkdir(parents=True, exist_ok=True)
    gates = verify_mechanisms()
    aggregates = {}
    episodes_path = output / 'episodes.csv'
    with episodes_path.open('w', newline='') as f, (output / 'traces.jsonl').open('w') as tf:
        writer = None
        for condition in CONDITIONS:
            for source in ('human', 'machine'):
                for policy in POLICIES:
                    totals = {}
                    for seed in range(seeds):
                        for variant in (0, 1):
                            jobs = generate(seed, variant, condition, source, steps)
                            row, trace = rollout(jobs, policy, source)
                            # isolated 是 steps 个各自重置的 1 步 episode 的聚合。
                            row['resets'] = steps if condition == 'isolated' else 1
                            record = dict(condition=condition, source=source, policy=policy,
                                          seed=seed, variant=variant, **row)
                            if writer is None:
                                writer = csv.DictWriter(f, fieldnames=list(record))
                                writer.writeheader()
                            writer.writerow(record)
                            if seed == 0:
                                tf.write(json.dumps(dict(condition=condition, source=source,
                                    policy=policy, variant=variant, trace=trace), sort_keys=True) + '\n')
                            for key, value in row.items():
                                totals[key] = totals.get(key, 0) + value
                    n = 2 * seeds
                    aggregates[f'{condition}/{source}/{policy}'] = {
                        'generated_instances': n,
                        'episode_success_rate': totals['episode_success'] / n,
                        'step_completion_rate': totals['completed'] / (n * steps),
                        **{f'mean_{k}': v / n for k, v in totals.items() if k != 'episode_success'},
                    }
    summary = {'experiment': 'symbolic_mechanism_v1', 'seeds': seeds, 'steps': steps,
               'template_count': 1, 'gates': gates,
               'memoryless_step_success_upper_bound_dependent': .5,
               'length_match_status': '仅串接与历史依赖的动作数、观测条数及最短计划长度匹配；字符长度须看记录。并发/闭环未匹配。',
               'causal_expected_optimal_cost_per_support_step_p075': 2.75,
               'clairvoyant_bound_is_not_causal_policy': True,
               'aggregates': aggregates}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (episodes_path, output / 'traces.jsonl', output / 'summary.json')}
    (output / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
    for condition in CONDITIONS:
        for policy in POLICIES:
            a = aggregates[f'{condition}/human/{policy}']
            print(condition, policy, f"step={a['step_completion_rate']:.3f}",
                  f"episode={a['episode_success_rate']:.3f}",
                  f"cost={a['mean_action_cost']:.3f}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seeds', type=int, default=1000)
    parser.add_argument('--steps', type=int, default=12)
    parser.add_argument('--output-dir', type=Path, default=Path('results/symbolic_v1'))
    args = parser.parse_args()
    run(args.seeds, args.steps, args.output_dir)
