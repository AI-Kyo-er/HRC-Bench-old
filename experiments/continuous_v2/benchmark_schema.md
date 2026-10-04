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
  "human_targets": {}
}
```

`robot_targets` 和 `human_targets` 是评测端的私有目标，不应送入模型。公开 assignment 消息是模型可以使用的任务信息；如果需要研究目标歧义，应在消息协议中显式记录，而不是把目标藏在私有字段后要求模型猜测。

## 观测与动作

`public_observations.jsonl` 保存 `Observation` 的公开编码：对象和区域几何、机器人末端、人的位置、公开消息、已完成公开技能、当前动作阶段和可见人类动作。`policy_io.jsonl` 保存模型收到的同一观测及其输出动作。

允许的动作包括 `transfer`、`request_help`、`acknowledge`、`wait`、`joint_position` 和 `finish`。`finish` 只表示模型的声明，终态成功由后端独立计算。

## 结构划分

训练/开发/测试的划分按 `structure.split` 执行。测试集可以包含训练中见过的局部作用，但不能复用同一依赖关系。例如训练可见 `guidance -> joint_execution`，测试使用 `guidance -> intervention -> joint_execution`。对象布局和初始分工仍需做 seed 与几何去重，避免模型只记住坐标。

