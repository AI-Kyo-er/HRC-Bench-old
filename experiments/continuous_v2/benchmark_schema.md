# HRC-Continuous v2 数据契约

## Episode 目录

每个 episode 使用独立目录和稳定文件名：

```text
<output>/<episode-name>/
  scenario.json
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
