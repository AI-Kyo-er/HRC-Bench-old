# Genesis 阶段验证记录

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
