# Dynamic Human Benchmark 设计

## 1. 研究对象

HRC-Continuous-Cobalanced-Benchmark 要测的是：机器人在持续、公开、可重规划的共同活动中，能否支持人的目标，同时保持自己的有效贡献。评测对象可以是 VLA（图像到动作）、WLA（语言/状态到动作），也可以是带记忆或规划器的策略。机器人不能读取 `scenario.json`、人类私有状态、评测标签或 evaluator 文件；每个决策只能使用运行时公开 observation 和历史公开消息。

当前运行时把场景定义成 `ActivityContract`：它声明工作项、前置贡献、交接边界、共享资源和成功条件。它不声明第 N 个 tick 要发生什么。人和机器人各自根据当前观测选择动作，失败、延迟、占用冲突、求助、接管、离开和返回都会改变后续公开信息。这是可泛化的活动约束，而不是扩展后的固定状态机。

## 2. COOPERA 借鉴与差距

COOPERA 的高价值设计包括稳定的人格/Big-5 profile、长时段记忆和时间上下文、对象与环境条件、生成式意图与任务分解、人体动作数据，以及 same-human/different-scenes 和 different-humans/same-scene 的划分。这里借用的是数据组织原则和“伙伴随时间变化”的研究对象，不把其生成模型直接当作本项目的 ground truth。

当前 `DynamicHumanPolicy` 是可复现、可审计的规则型伙伴：profile 改变节奏、坚持性、主动性、谨慎度和让行倾向；记忆按事件、显著性和时间新近性检索；公开反馈会触发 reflection；当前 intention 可因进度、失败和占用而切换。它还没有 COOPERA 级别的 LLM 开放任务生成、SMPL-X/Motion-X 全身动作 grounding、跨天长期记忆或真人校准。因此实验报告只能称为 dynamic partner mechanism validation，不能称为真实人的行为结果。

## 3. 伙伴接口与审计 schema

`DynamicHumanPolicy.step(observation)` 只接收公开 observation，返回 `PartnerOutput(command, messages, state_updates)`。其中 `HumanCommand` 包含 `intent`、物体与目标、连续速度 `speed_mps`、加速度 `acceleration_mps2` 和 `gaze_target`。reference backend 按速度和加速度逐 tick 积分；Genesis 将命令映射到 AvatarController，并把命令、RGB、关节状态和真实视频一并保存。

伙伴的私有审计状态分成五层：

| 层 | 关键字段 | 是否进入机器人 observation |
| --- | --- | --- |
| profile | `pace`、`assertiveness`、`persistence`、`caution`、`autonomy` | 否 |
| episode state | 当前 phase、开放承诺、最近公开反馈 | 否 |
| memory | `memory_id`、时间、事件、显著性、访问次数 | 否 |
| intention | objective、object、destination、phase、reason、commitment | 否 |
| reflection | trigger、evidence、检索 memory、结果、状态快照 | 否 |

每个 episode 写出 `human_memory.jsonl`、`human_memory_retrievals.jsonl`、`human_reflections.jsonl` 和 `human_intentions.jsonl`。这些文件是 evaluator trace，不是模型输入；`events.jsonl` 同时记录独立的 `human_memory_write`、`human_memory_retrieval`、`human_reflection` 和 `human_intention_update` 事件。普通适应变量仍用兼容的 `human_state_update` 事件记录。

## 4. 任务 taxonomy

可选任务目录 `make_extended_task_catalog()` 当前包含九个任务族：serial relay、concurrent overlay、nested support、interruption/reprioritization、leave-and-return、robot-induced rebalance、history reinterpretation、trait-dependent open task，以及 held-out task composition。每个任务族由布局扰动、活动契约和结构标签组成；同一个族可以更换机器人策略、伙伴 profile 和 Genesis/参考后端。

默认 `CONTINUOUS_SCENARIOS` 仍是六个机制验证场景，保证旧实验和测试可复现。正式扩展实验使用：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --task-catalog --count-per-family 5 --partner-mode dynamic \
  --backend genesis --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/task_catalog_v1
```

任务 JSON 只需提供对象、区域、`ActivityContract` 和结构标签。配对关系由稳定的 `split/family/name/seed` 路径确定，不使用 `manifest.json` 编码样本配对。

## 5. 数据划分与泛化协议

| 协议 | 训练可见内容 | 测试变化 | 目的 |
| --- | --- | --- | --- |
| same human / different scene | profile、伙伴动力学 | 新布局、新物体位置 | 场景泛化 |
| different human / same scene | 场景契约 | 未见 profile 与随机种子 | 伙伴泛化 |
| same family / held-out composition | 已见原子作用 | 未见作用组合与依赖 | 组合泛化 |
| held-out task family | 训练任务族 | 完整未见任务族 | 任务泛化 |
| within-day / across-day | 当天公开历史 | 跨 episode 或跨天记忆 | 长期适应 |

训练、开发、测试由 `InteractionStructure.split` 和任务族版本决定。每个测试 episode 使用固定 seed 重放相同公开场景，策略不能读取隐藏目标。对 VLA，保留真实外部/腕部 RGB；对 WLA，使用同一时间轴的公开消息、状态和动作历史；两者都必须记录动作块长度、推理延迟、实际执行动作、抢占和失败。

## 6. VLA/WLA 边界

公开 observation 包括相机像素（若后端提供）、机器人自身状态、可见几何、公开消息、当前动作 phase、已公开完成贡献以及可见的人类位置/动作。它不包括 `human_profile`、trust、workload、memory、private intention、scenario id 或 evaluator 文件。模型输出统一解码成 `Action`：`transfer`、`joint_position`、`request_help`、`acknowledge`、`wait` 或 `finish`。Genesis 中重要模型实验必须保存可解码的 `demo.mp4`、`video_timeline.json`、RGB、关节轨迹和 `policy_io.jsonl`，HTML 报告同时展示真实 Sim 视频、轨迹、事件和公开输入输出。

## 7. 指标

基础结果包含活动成功、机器人贡献完成率、人类贡献完成率、贡献互补、恢复成功、协调效率和 cobalance score。交互指标包含意图识别准确率/校准、求助 precision/recall/F1、公开重规划、等待和打断、响应延迟、冲突/近失和安全距离。泛化指标分别在 unseen human、scene、task family 和 across-day split 上计算，并报告多 seed 均值与 bootstrap 区间。

`cobalance_score` 目前是可审计的起始指标：活动成功 0.35、双方贡献互补 0.25、失败恢复 0.20、协调效率 0.20。它不是真人负担或信任的心理测量，真人研究前需要用主观负担、可用性和公平感重新校准。

## 8. 真实 Sim 视频要求

轨迹动画只能帮助逐 tick 审计，不能替代场景证据。每个重要 Genesis episode 都必须有非空、可逐帧解码的 `demo.mp4`，并由 `video_timeline.json` 对齐 benchmark 时间、FPS 和事件。报告页面默认先显示真实 Sim 视频，再显示俯视轨迹和事件跳转。当前抓放仍是运动学 attachment，视频不能被解释为已经验证了真实接触动力学、力闭合或真人 HRC 安全。

## 9. 能力边界

已有实验能证明：连续观察与动作块接口、公开历史依赖、伙伴动态适应、失败恢复、重新分工、离返、Genesis 视频和 VLA/WLA adapter 的可审计接入。它还不能证明先进 VLA/WLA 已具备协作能力，也不能证明规则型 dynamic partner 等同真人。下一阶段的有效比较应在同一活动契约和同一真实 Sim 视频协议下替换真实模型，并增加未见伙伴、未见任务组合、接触安全和真人校准。
