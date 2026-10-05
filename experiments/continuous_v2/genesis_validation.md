# Genesis 阶段验证记录

## 2026-10-05：匹配历史、关节抓放与真实 VLA

最新匹配历史报告：[matched_history_genesis_v2](../../results/continuous_v2/matched_history_genesis_v2/index.html)。
三 seed × 两个历史来源 + 四个探针，共 18 条视频；6 条来源复用 v1 已完成的真实
运行，12 条探针重新运行，来源与哈希均保存。五项匹配在 3/3 seed 全部通过：
首次模型公共输入、首次 RGB、首次动作、回答前伙伴完整公共输入及回答前 RGB。

| 条件 | 探针起始 trust / reliability | 同一公开求助回答（3 seed） |
|---|---|---|
| 可靠历史 + adaptive | 0.78 / 0.82 | 接受 3/3 |
| 连续失败历史 + adaptive | 0.34 / 0.16 | 拒绝 3/3 |
| 两种历史 + frozen | 0.70 / 0.70 | 均接受，各 3/3 |

四探针都能完成活动，但接受时由人完成，拒绝时由手写机器人策略自行完成。
因此机制差异在贡献组织，而不是只看成功率。这里重建了世界和协议，只带入
两个学习变量；它证明模拟机制的历史作用，不是真人规律或无重置持续 HRC。
来源最后一项完成后立即结束，伙伴未再观察该事件，可靠信念只记录两次完成
更新；没有凭终态补写第三次学习。18 个视频全部解码并核对帧数与 fps，浏览器
核查九个场景 / seed 组合、事件跳转、视频 / RGB 加载与移动端宽度通过。

底层关节校准：[joint_calibration_genesis_v1](../../results/continuous_v2/joint_calibration_genesis_v1/index.html)。
公开几何 IK 教师仅输出 18 个 `joint_position`，1.2 秒内实际触发
`abstract_grasp_attached` → `abstract_grasp_released` → `robot_transfer_completed`，
三事件的来源都是 `joint_control`。模型输出不再需要语义 `transfer` 才能搬运。
外部 / 腕部相机均为 320×240 实际渲染，第三人称 480×360 视频用于报告。
抓取仍是运动学 attachment，不是接触动力学或 VLA 操作成绩。

官方 OpenPI 的 π0.5-DROID 环境、权重、归一化资产和 tokenizer 已就绪。
源码固定为 `215abfb217dbac7d5f1273282331b9b1866c0479`，20 个权重对象共约
12.43 GB，全部核对 GCS MD5，权重位于共享 models 目录。

| 原生模型运行 | 模拟时限 | 真实推理次数 | 关节控制步 | 收纳成功 |
|---|---:|---:|---:|---|
| [v1](../../results/continuous_v2/pi05_droid_genesis_v1/index.html) | 6 秒 | 12 | 90 | 否 |
| [v2](../../results/continuous_v2/pi05_droid_genesis_v2/index.html) | 30 秒 | 57 | 450 | 否 |

控制为 15 Hz，真实模型动作块为 10×8、执行前 8 个；仅五项双相机 / 本体 /
公开语言输入。两条运行独立核查所有模型调用的 PNG 像素哈希、全部关节动作
转换，分别完整解码 98 / 458 视频帧，记录在 `model_execution_verification.json`。
模型臂关节与夹爪实际变化，但无抓取和完成事件，杯子没有搬运；结果保留。
首次推理含编译约 11.65 秒，随后 v1 推理约 88–94 ms。同步推理暂停模拟时钟，
这些耗时还未转为人的延迟反馈。v2 复用服务，模型随机流继续推进，不是与 v1
严格配对的时限因果对照。

这两条只证明实际权重推理和关节控制闭环，并暴露基础操作未达成；伙伴仅观察，
任务没有测试 HRC。视觉与 DROID 实机训练分布不同、抽象抓放、控制标定、语言
与时限都是待分析因素，不能归因为模型没有协作能力。运行出现 Genesis 的
reference joint limit / constraint time constant 提示，尚未完成真实硬件等价
的控制与视觉校准，因此不能当正式模型排行榜。

官方规格依据 [OpenPI DROID 输入变换](https://github.com/Physical-Intelligence/openpi/blob/215abfb217dbac7d5f1273282331b9b1866c0479/src/openpi/policies/droid_policy.py)、
[归一化与控制频率说明](https://github.com/Physical-Intelligence/openpi/blob/215abfb217dbac7d5f1273282331b9b1866c0479/docs/norm_stats.md)
及 [DROID RobotIKSolver](https://github.com/droid-dataset/droid/blob/main/droid/robot_ik/robot_ik_solver.py)。

新评分又修复了“几何接近目标即提前完成”的缺口：活动成功需要实际释放和合法
贡献，任意 item_id 与接管方都不能绕开依赖；循环按活动契约结束。旧结果保留
原评分，不回写成功标签。修订后 [关节校准 v2](../../results/continuous_v2/joint_calibration_genesis_v2/index.html)
仍为 18 步成功；[恢复契约 v2](../../results/continuous_v2/recovery_contract_genesis_v2/index.html)
在 seed 0 跑四条件，人接管 / 自行重试 / 无失败均完成，持续失败未完成。所有
蓝杯合法完成事件均在红杯前置完成之后，五条新增视频完整解码核对通过。

研究门槛仍未达到：需无重置持续活动、实际模型与自适应伙伴交互、真实接触 /
安全、可信的人行为校准，以及操作难度匹配的结构组合与留出评测。

本次报告重建还执行了统一的视频产物审计：`genesis_v10` 为 6/6、
`genesis_paired_v10` 为 18/18、`matched_history_genesis_v2` 为 18/18、
`recovery_genesis_v1` 为 9/9、`recovery_contract_genesis_v2` 为 4/4，
两条 `pi05_droid_genesis` 运行均为 1/1，所有 Genesis episode 都有非空运行时
`demo.mp4`。其中旧的六场景和 18 条配对快照没有保存逐帧时间轴，所以报告标记
为“demo.mp4（无时间轴）”并允许独立播放；匹配历史、恢复、关节校准和 π0.5
运行的时间轴完整性记录保留在各自的 `replay_verification.json` 中。


## 2026-10-05：失败预算与真实视频恢复实验

修复 `VCWorkspace` 原先未读取 `robot_failure_budget` 的问题。预算在 episode
初始化时重置，只在机器人实际启动 transfer 时消耗；等待和求助不消耗预算。
失败事件明确标记 `scenario_synthetic_failure`，不是抓取接触失败。
旧 v10 结果继续保留，不用修订后的逻辑重评分。

恢复实验固定 `greedy_public`、adaptive 规则伙伴、seed 0/1/2、relay 的目标和
贡献前置依赖、30 tick 时限。每个 seed 内三条件仅改变失败预算或失败接管概率。
物理频率为 60 Hz，benchmark 为 10 Hz，相机 480×360，视频 10 fps。

| 条件 | 每次搬运失败机制 | 失败接管概率 | 成功 / 运行 | 失败 / 运行 | 人接管 / 运行 | 恢复分类 | 时间范围（秒） |
|---|---|---:|---:|---:|---:|---|---|
| `failure_handoff` | 首次启动失败，预算 1 | 1 | 3/3 | 1 | 1 | `recovered_after_failure` | 0.5 |
| `failure_no_handoff` | 首次启动失败，预算 1 | 0 | 3/3 | 1 | 0 | `recovered_after_failure` | 0.7–0.8 |
| `no_failure` | 预算 0、随机失败概率 0 | 1 | 3/3 | 0 | 0 | `no_failure` | 0.6–0.7 |
| `persistent_failure`（另列核查） | 每次启动失败，概率 1 | 0 | 0/3 | 30 | 0 | `failed_to_recover` | 3.0（达到时限） |

人接管条件实际记录 `robot_action_failed` → 公开 `reassignment` →
`human_transfer_completed(blue)`，机器人初始角色贡献成功为 0。禁止接管的一次
失败条件实际记录机器人重试和 `robot_transfer_completed(blue)`，机器人角色贡献
成功为 1。因此两者虽然都完成活动，其分工结果不同。不能把人替机器人完成任务
解释成机器人的独立操作能力，也不能把禁止接管条件称为未恢复负例。

持续失败条件改变失败持续性，单独用来核查未恢复分类，不用于估计一次失败后
人接管的因果效果。三 seed 是小规模工程验证，不是有统计功效的模型实验。
时间短源于 VC 动作与运动学 attachment 抽象，不能解释为真人或真实机械臂效率。

证据：[9 条恢复对照](../../results/continuous_v2/recovery_genesis_v1/index.html)、
[3 条持续失败核查](../../results/continuous_v2/recovery_negative_genesis_v1/index.html)。
每条保存 `demo.mp4`、`trajectory.npz`、RGB、事件、公开输入与动作。
`video_timeline.json` 的每帧记录视频时间 / 物理步 / benchmark 时间；12 个 MP4
已完整解码，帧数和 fps 与记录一致，最后 benchmark 时间与评分终态一致，
核查保存在各运行目录 `video_verification.json`。

另运行了 3 seed × 2 策略的 Genesis 历史反事实：直接执行均为一次失败后人
接管完成；先求助均未启动失败搬运，因此属于 `no_failure`。先求助策略的
`same_geometry_steps=2`、`history_conditioned_action_divergence=0.5` 在三个 seed
相同。但这里只匹配几何，没有匹配当前公开消息和占用；不能据此证明脱离即时
反馈后的持久历史适应。下一阶段需要匹配当前可见输入的历史 / 冻结状态消融，
以及真实 VLA/WLA 推理、动作标定和物理技能验证。

证据：[seed 0](../../results/continuous_v2/history_counterfactual_genesis_v2/index.html)、
[seed 1](../../results/continuous_v2/history_counterfactual_genesis_seed1/index.html)、
[seed 2](../../results/continuous_v2/history_counterfactual_genesis_seed2/index.html)。

以下 v10 表格是修复前的历史记录。

## 目的

验证 HRC-Continuous v2 是否能在 VC/Genesis 后端按共同时间轴运行：模型只接收
公开观察，机器人动作可在动作块中重新规划，伙伴根据当前占用、进度和公开消息
更新行为，评测器从活动契约计算终态。

## 设置与循环

- 后端为 `GenesisContinuousAdapter`，60 Hz 物理步；场景 tick 必须整除 60。
- 场景为 `relay`、`nested_support`、`concurrent_overlay`、
  `history_reinterpretation`、`robot_induced_rebalance`、`leave_and_return`。
- 策略为 `greedy_public` 协议基线，没有加载 VLA/WLA 权重。
- 六场景使用 adaptive 伙伴；另对六场景运行 fixed/reactive/adaptive 三种伙伴配对。
- 另有一个历史反事实小实验，用相同几何比较不同公开历史是否改变动作选择。

每个 benchmark tick 先读取公开观察，再运行伙伴命令和状态更新；策略选择动作块，
Genesis 推进六个物理帧。延迟、失败、阻塞、抢占和帮助消息进入事件流，下一 tick
重新读取公开反馈。结束时捕获实际终态，再按活动工作项评分。

## 实际结果

| 场景 | 完成时间（秒） | 活动成功 | 机器人动作数 | 延迟步数 | 伙伴状态更新 | 公开重规划 |
|---|---:|:---:|---:|---:|:---:|:---:|
| `relay` | 0.6 | 是 | 1 | 0 | 否 | 否 |
| `nested_support` | 2.1 | 是 | 2 | 0 | 否 | 否 |
| `concurrent_overlay` | 2.2 | 是 | 2 | 0 | 否 | 否 |
| `history_reinterpretation` | 1.5 | 是 | 2 | 1 | 是 | 否 |
| `robot_induced_rebalance` | 2.3 | 是 | 2 | 1 | 是 | 否 |
| `leave_and_return` | 1.7 | 是 | 6 | 0 | 是 | 是 |

六个场景的活动契约均完成。`history_reinterpretation` 和
`robot_induced_rebalance` 各出现一次 `robot_action_delayed`，并触发伙伴的
trust/reliability 更新；`leave_and_return` 记录了一次公开重规划。当前 seed
没有 `robot_action_failed`，因此不能宣称已经验证失败后的恢复。短时长来自当前
VC 动画和操作抽象，不能解释为真实机器人效率；这些结果证明的是运行、记录和
审计链路，尚未比较真实具身模型的能力。

配对实验共 18 个 episode（六场景 × 三种伙伴），每个 episode 都有独立的
`demo.mp4`。`fixed_replay`、`reactive`、`adaptive` 在前五个场景的同一 seed
轨迹相同；`leave_and_return` 中 adaptive 会根据暂离/返回状态产生不同轨迹。
历史反事实实验的证据目录还记录了相同几何下的历史条件动作差异指标。

## 边界

Genesis 当前使用运动学 attachment；人类拿放是 Avatar 动作接口，物体未建成可产生
接触失败的刚体任务。需要加入真实接触、视觉标定、可控失败标签和训练后的 VLA/WLA
策略后，才能进行模型排行榜和 cobalance 泛化评测。Dataset CLI/API 已支持
`--backend genesis`，输出按 episode 目录和稳定文件名组织，不使用 `manifest.json`。

证据入口：`results/continuous_v2/genesis_v10/`、
`results/continuous_v2/genesis_paired_v10/`、
`results/continuous_v2/history_counterfactual_genesis_v1/`。

每个 Genesis episode 同时保存轨迹 `trace.jsonl` 和运行时录制的
`demo.mp4`。轨迹回放用于逐 tick 对齐、事件跳转和指标审计；`demo.mp4` 是
VC/Genesis 实际渲染过程的视频，包含初始化热身，视频时间与 benchmark tick
可能有约 0.33 秒偏移。两者是互补证据，不能把轨迹动画重新渲染当作真实 Sim
视频。
