# HRC-Continuous v2 数据契约

## Episode 目录

每个 episode 使用独立目录和稳定文件名：

```text
<output>/<episode-name>/
  scenario.json
  public_scenario.json
  public_observations.jsonl
  policy_io.jsonl
  trace.jsonl
  events.jsonl
  metrics.json
```

不使用 `manifest.json` 表达配对关系。加载器以 episode 目录为边界，并依据 `scenario.json` 的 `structure.split`、`condition` 和 `partner_mode` 分组。RGB 文件由 `policy_io.jsonl` 或 `public_observations.jsonl` 中的 `rgb_artifact` 指向。

## `scenario.json`

场景文件包含对象、区域、公开分工、伙伴条件和交互结构：

```json
{
  "name": "held_out_003",
  "condition": "held_out",
  "structure": {
    "family": "held_out_reinterpretation",
    "segments": ["guidance", "intervention", "joint_execution"],
    "dependencies": [["guidance", "intervention"]],
    "concurrency": [],
    "split": "test"
  },
  "objects": [],
  "regions": {},
  "robot_targets": {},
  "human_targets": {},
  "dynamics": {
    "robot_delay_probability": 0.0,
    "robot_failure_probability": 0.0,
    "max_delay_steps": 0,
    "human_replan_sensitivity": 0.65,
    "leave_pressure": 0.0,
    "return_on_robot_idle": true
  }
}
```

`robot_targets` 和 `human_targets` 是评测端的私有目标，不应送入模型。公开 assignment 消息是模型可以使用的任务信息；如果需要研究目标歧义，应在消息协议中显式记录，而不是把目标藏在私有字段后要求模型猜测。

`public_scenario.json` 是给模型或数据发布方的脱敏场景描述，只保留
`name`、`description`、`task_family`、物体与区域几何、`tick_hz` 和 `max_steps`。
它不包含 `robot_targets`、`human_targets`、`dynamics`、`human_availability`、
`activity` 或 `assets`；这些字段仅用于 evaluator 和后端复现。

`activity` 是场景的活动契约，保存任务目标和可执行工作项：

```json
{
  "objective": "共同整理物体",
  "interaction_acts": [
    {"act_id": "guidance", "kind": "guidance", "actor": "human", "target": "human:red:tray_red", "requires": []},
    {"act_id": "act:robot:blue:tray_blue", "kind": "joint_execution", "actor": "robot", "target": "robot:blue:tray_blue", "requires": ["guidance"]}
  ],
  "work_items": [
    {"item_id": "human:red:tray_red", "object_id": "red", "destination": "tray_red", "preferred_role": "human", "prerequisites": [], "handoff": "open"},
    {"item_id": "robot:blue:tray_blue", "object_id": "blue", "destination": "tray_blue", "preferred_role": "robot", "prerequisites": ["human:red:tray_red"], "handoff": "open"}
  ],
  "shared_resources": ["shared_workspace", "public_commitment_channel"],
  "replanning_triggers": ["action_failed", "action_delayed", "help_request", "partner_returned"]
}
```

`interaction_acts` 是场景的组合标注，不是事件脚本。它描述指导、共同
执行、干预、重新规划之间的局部依赖，运行时不会按 act 的顺序自动触发
动作；双方仍依据公开观测、几何占用、消息和工作项终态在线选择贡献。

前置条件是公开完成 skill 的约束，不是事件序列。工作项可以被另一方接管；后端在提交时检查约束并产生 `action_blocked`，模型需要从公开反馈中恢复。

## 观测与动作

`public_observations.jsonl` 保存 `Observation` 的公开编码：对象和区域几何、机器人末端、人的位置、公开消息、已完成公开技能、当前动作阶段和可见人类动作。`policy_io.jsonl` 保存模型收到的同一观测及其输出动作。

外部模型适配器可以实现一个 `predict(public_observation)` 函数，并通过
`hrc_pilot.benchmark.ExternalPolicyAdapter` 包装。输入只包含上述公开字段，
输出为 `Action`、动作 JSON 对象或 JSON 字符串。适配器在每次调用时校验动作，
记录推理耗时、状态、原始输出和解析后的动作；这些信息写入同一行的
`adapter` 字段，模型异常也会留下失败审计记录。这样本地 VLA/WLA、HTTP
客户端或 subprocess 推理都可以放在适配器内部，运行时和 evaluator 不需要
为每个模型分叉。

允许的动作包括 `transfer`、`request_help`、`acknowledge`、`wait`、`joint_position` 和 `finish`。`finish` 只表示模型的声明，终态成功由后端独立计算。

公开消息还可以报告 `action_delayed`、`action_failed`、`reassignment`、
`correction`、`temporarily_away` 和 `returned`。这些是 episode 中双方
发送的协作信号；模型需要根据它们重新规划。`DynamicsSpec` 中的概率参数
属于实例条件，不进入模型观测。

`events.jsonl` 还会记录 `human_state_update` evaluator 事件。事件包含
`trust`、`reliability_belief`、`workload`、`commitment_stability`、
`initiative`、`robot_dependency`、`willingness_to_help` 和 `available` 的
更新前后值及其公开证据。这些字段用于分析机器人行为是否改变人的后续
承诺、让行、接管和暂离，不会送入模型观测。

## 结构划分

训练/开发/测试的划分按 `structure.split` 执行。测试集可以包含训练中见过的局部作用，但不能复用同一依赖关系。例如训练可见 `guidance -> joint_execution`，测试使用 `guidance -> intervention -> joint_execution`。对象布局和初始分工仍需做 seed 与几何去重，避免模型只记住坐标。

## 配对实验

`run_paired_benchmark` 在同一组场景、同一 seed 和同一公开协议下依次运行
`fixed_replay`、`reactive`、`adaptive`。结果目录使用
`<partner_mode>/<scenario_name>/`，加载器用目录名、场景名和 seed 配对，
不需要额外的 `manifest.json`。

若要只改变机器人策略而固定场景、seed 和伙伴初始状态，可使用反事实
运行器：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/counterfactual \
  --generated 4 --seed 7 --counterfactual-policies greedy_public,package.module:factory
```

输出按 `<policy_name>/<scenario_name>` 保存，`counterfactual_group` 标记
配对单元。策略造成的延迟、失败、求助和公开承诺差异会进入同一套事件与
状态更新记录。

## 数据集级工作流

`hrc_pilot.dataset` 提供正式的数据集生成和批量评测入口：

```bash
PYTHONPATH=src python scripts/run_hrc_dataset.py generate \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/continuous_v1 \
  --count-per-condition 10 --repeats 3
PYTHONPATH=src python scripts/run_hrc_dataset.py evaluate \
  --dataset /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/continuous_v1 \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v1/model \
  --policy package.module:factory --split test
```

生成器将 episode 放在 `<split>/<episode_id>/`，并写入 `dataset.json` 和
`summary.json`；它们是版本和聚合信息，不承担 episode 配对。评测器重新读取
每个 `scenario.json`，沿用 episode 的 seed，在相同活动契约和伙伴条件下运行
模型。结果目录使用 `<policy>/<split>/<episode_id>/`，因此多个模型可以对同一
场景直接按稳定路径配对。聚合指标包括活动成功、机器人/人类角色成功、重分工
恢复时间、公共重规划、冲突率和伙伴隐藏状态的变化。

每个 episode 还会保存一组透明的 cobalance 协议代理指标：机器人和人的贡献
完成率、`contribution_complementarity`、失败后的 `recovery_success`、
`coordination_efficiency` 和加权的 `cobalance_score`。当前权重固定为活动
成功 0.35、双方贡献互补 0.25、恢复成功 0.20、协调效率 0.20；它们是可审计的
benchmark 起始定义，不是对真人信任或负担的心理测量，后续真人研究应重新校准。
`recovery_status`
明确区分 `no_failure`（没有发生失败，`recovery_success` 为 `null`）、
`recovered_after_failure`（失败后完成，值为 `1.0`）和 `failed_to_recover`
（失败后未完成，值为 `0.0`）。聚合器同时报告三类状态计数和每个数值指标的确定性
bootstrap 95% 区间，以便多 seed 结果不被单次 episode 的成功率替代。
