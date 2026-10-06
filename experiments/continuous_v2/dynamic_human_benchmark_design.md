# Dynamic Human Benchmark 设计

## 1. 研究对象

HRC-Continuous-Cobalanced-Benchmark 要测的是：机器人在持续、公开、可重规划的共同活动中，能否支持人的目标，同时保持自己的有效贡献。评测对象可以是 VLA（图像到动作）、WLA（语言/状态到动作），也可以是带记忆或规划器的策略。机器人不能读取 `scenario.json`、人类私有状态、评测标签或 evaluator 文件；每个决策只能使用运行时公开 observation 和历史公开消息。

当前运行时把场景定义成 `ActivityContract`：它声明工作项、前置贡献、交接边界、共享资源和成功条件。它不声明第 N 个 tick 要发生什么。人和机器人各自根据当前观测选择动作，失败、延迟、占用冲突、求助、接管、离开和返回都会改变后续公开信息。这是可泛化的活动约束，而不是扩展后的固定状态机。

## 2. COOPERA 借鉴与差距

COOPERA 的高价值设计包括稳定的人格/Big-5 profile、长时段记忆和时间上下文、对象与环境条件、生成式意图与任务分解、人体动作数据，以及 same-human/different-scenes 和 different-humans/same-scene 的划分。这里借用的是数据组织原则和“伙伴随时间变化”的研究对象，不把其生成模型直接当作本项目的 ground truth。

早期 `DynamicHumanPolicy` 是可复现、可审计的规则型伙伴：profile 改变节奏、坚持性、主动性、谨慎度和让行倾向；记忆按事件、显著性和时间新近性检索；公开反馈会触发 reflection；当前 intention 可因进度、失败和占用而切换。它还没有 COOPERA 级别的 LLM 开放任务生成、SMPL-X/Motion-X 全身动作 grounding、跨天长期记忆或真人校准。这一路径的实验只能称为 dynamic partner mechanism validation，不能称为真实人的行为结果。

当前核心实测已转为本地 Qwen3-14B 生成式伙伴与真实 π0.5 模型。Qwen 根据公开观察、任务板、近期经历和先前目标生成意图、理由、消息和经验；机器人读取真实双相机、本体状态和公开任务语言，直接输出关节动作。人的目标选择不再由规则型伙伴决定。机器人和六DOF人手代理均通过摩擦接触移动自由刚体，显示人体仍用 IK 与动作库。合成人行为缺少真人校准，不能把模型输出当作真实人的规律。

## 3. 伙伴接口与审计 schema

当前 `QwenHumanPolicy.step(observation)` 只接收公开 observation，返回 `PartnerOutput(command, messages, state_updates)`。其中 `HumanCommand` 包含 `intent`、物体与目标、连续速度 `speed_mps`、加速度 `acceleration_mps2` 和 `gaze_target`。reference backend 按速度和加速度逐 tick 积分；Genesis 摩擦接触模式把命令交给连续接触手执行器，并把命令、RGB、关节状态和真实视频一并保存。接近、闭指、抬起等低层运动阶段不选择协作目标；它们仍是手写执行原语，不是学习得到的全身控制。

下面五层表是早期规则型伙伴的审计设计。当前 Qwen 路径实际保存 persona、模型生成目标/经历、公开任务板、实际检索的经验ID与完整输入输出；没有把下表中的信任分数或显著性公式用于生成式伙伴的决策。

早期伙伴的私有审计状态分成五层：

| 层 | 关键字段 | 是否进入机器人 observation |
| --- | --- | --- |
| profile | `pace`、`assertiveness`、`persistence`、`caution`、`autonomy` | 否 |
| episode state | 当前 phase、开放承诺、最近公开反馈 | 否 |
| memory | `memory_id`、时间、事件、显著性、访问次数 | 否 |
| intention | objective、object、destination、phase、reason、commitment | 否 |
| reflection | trigger、evidence、检索 memory、结果、状态快照 | 否 |

规则型路径每个 episode 写出 `human_memory.jsonl`、`human_memory_retrievals.jsonl`、`human_reflections.jsonl` 和 `human_intentions.jsonl`。这些文件是 evaluator trace，不是模型输入；`events.jsonl` 同时记录独立的 `human_memory_write`、`human_memory_retrieval`、`human_reflection` 和 `human_intention_update` 事件。普通适应变量仍用兼容的 `human_state_update` 事件记录。生成式路径以 `human_policy_io.jsonl` 的原始模型输出、`human_memory.jsonl` 和 `public_task_board.jsonl` 为证据；不存在的 reflection 文件不能当作已执行功能。

无重置活动流只初始化一次物理世界与双方策略，公开任务更新后保持物体、机械臂、人体位置与模拟时钟。新活动只清空贡献账本；历史与模型生成目标保留。当前上下文修订会根据公开 activity_change 替换旧任务板，并标明旧目标年代；不替模型决定新目标。该修订已做接口回归，尚未完成新的生成式模型实测。

## 4. 任务 taxonomy

可选任务目录 `make_extended_task_catalog()` 当前包含九个任务族：serial relay、concurrent overlay、nested support、interruption/reprioritization、leave-and-return、robot-induced rebalance、history reinterpretation、trait-dependent open task，以及 held-out task composition。每个任务族由布局扰动、活动契约和结构标签组成；同一个族可以更换机器人策略、伙伴 profile 和 Genesis/参考后端。

九类契约不等于九类真实接触模型任务已验证。当前真实学习模型联合实测主要覆盖接力、并行和重新分工；连续世界流覆盖目标区域变化与职责交换，且存在不合格运动片段。

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

公开 observation 包括相机像素（若后端提供）、机器人自身状态、可见几何、公开消息、当前动作 phase、已公开完成贡献以及可见的人类位置/动作。它不包括 `human_profile`、trust、workload、memory、private intention、scenario id 或 evaluator 文件。通用模型接口可以解码成 `Action`：`transfer`、`joint_position`、`request_help`、`acknowledge`、`wait` 或 `finish`。Genesis 中重要模型实验必须保存可解码的 `demo.mp4`、`video_timeline.json`、RGB、关节轨迹和 `policy_io.jsonl`，HTML 报告同时展示真实 Sim 视频、轨迹、事件和公开输入输出。已接入的 π0.5-DROID 只输出关节操作，π0.5-LIBERO 通过末端增量与实际IK执行；不能将通用接口列出的求助、确认等动作描述成现有VLA已经具备的能力。

## 7. 指标

基础结果包含活动成功、机器人贡献完成率、人类贡献完成率、贡献互补、恢复成功、协调效率和 cobalance score。交互指标包含意图识别准确率/校准、求助 precision/recall/F1、公开重规划、等待和打断、响应延迟、冲突/近失和安全距离。这些交互和泛化指标是目标协议，尚非全部实现/实测。生成式人的私有意图没有独立真实标签时，不报告意图识别准确率；没有独立标注的求助机会时，不报告求助F1。现阶段优先报告原始活动结果、双方实际贡献、物理失败、占用/等待和公开变化后的响应记录；正式泛化评测才采用多种子统计与区间。

`cobalance_score` 目前是可审计的起始指标：活动成功 0.35、双方贡献互补 0.25、失败恢复 0.20、协调效率 0.20。其权重未经研究验证，当前仅保留为历史工程字段，不作为正式排名的主指标。双方贡献与总任务结果分别展示；人接管并完成任务不能自动说明机器人协作良好。真人研究前需要用主观负担、可用性和公平感重新校准。

## 8. 真实 Sim 视频要求

轨迹动画只能帮助逐 tick 审计，不能替代场景证据。每个重要 Genesis episode 都必须有非空、可逐帧解码的 `demo.mp4`，并由 `video_timeline.json` 对齐 benchmark 时间、FPS 和事件。报告页面默认先显示真实 Sim 视频，再显示俯视轨迹和事件跳转。早期视频使用运动学 attachment，不能当作接触证据。当前 friction_contact 路径使用自由碰撞刚体、受力夹爪与实际支持/释放/驻留判定；数据教师和模型运行分别标识。接触手仍是简化人体代理，视频不证明完整人体动力学或真人HRC安全。重要实验在正式HTML生成前完整解码并核验时间轴；运动门槛失败的运行只保留诊断，不进入有效能力汇总。

## 9. 能力边界

已有证据包括真实模型像素/动作链路、实际接触示范数据、生成式伙伴决定与经历记录，以及同一世界活动转换点的物理状态保持。早期规则型恢复/离返成功不能归因于学习模型；当前学习模型基础操作和连续流运动有效性仍存在失败。它还不能证明先进 VLA/WLA 已具备可靠协作能力，也不能证明合成伙伴等同真人。下一阶段的有效比较应在同一活动契约和同一真实 Sim 视频协议下替换真实模型，并增加未见伙伴、未见任务组合、接触安全和真人校准。
