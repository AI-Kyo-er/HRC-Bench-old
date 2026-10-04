# Genesis v10 阶段验证记录

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
