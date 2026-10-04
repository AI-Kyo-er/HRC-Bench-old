# Genesis v2 阶段验证记录

## 目的

验证 HRC-Continuous v2 是否能在 VC/Genesis 后端按共同时间轴运行：模型只接收
公开观察，机器人动作可在动作块中重新规划，伙伴根据当前占用、进度和公开消息
更新行为，评测器从活动契约计算终态。

## 设置与循环

- 后端为 `GenesisContinuousAdapter`，60 Hz 物理步；场景 tick 必须整除 60。
- 场景为 `relay`、`nested_support`、`concurrent_overlay`、
  `history_reinterpretation`、`robot_induced_rebalance`、`leave_and_return`。
- 策略为 `greedy_public` 协议基线，没有加载 VLA/WLA 权重。
- 六场景使用 adaptive 伙伴；两个高变化场景另运行 fixed/reactive/adaptive 配对。

每个 benchmark tick 先读取公开观察，再运行伙伴命令和状态更新；策略选择动作块，
Genesis 推进六个物理帧。延迟、失败、阻塞、抢占和帮助消息进入事件流，下一 tick
重新读取公开反馈。结束时捕获实际终态，再按活动工作项评分。

## 实际结果

| 场景 | 完成时间（秒） | 活动成功 | 机器人动作数 | 人状态更新 | 重新分工 |
|---|---:|---:|---:|---:|---:|
| `relay` | 0.6 | 是 | 1 | 2 | 0 |
| `nested_support` | 2.1 | 是 | 2 | 2 | 0 |
| `concurrent_overlay` | 2.2 | 是 | 2 | 2 | 0 |
| `history_reinterpretation` | 1.5 | 是 | 2 | 2 | 0 |
| `robot_induced_rebalance` | 2.3 | 是 | 2 | 4 | 0 |
| `leave_and_return` | 1.7 | 是 | 6 | 6 | 0 |

短时长来自当前 VC 动画和操作抽象，不能解释为真实机器人效率。随机动力学在
本次 seed 没有造成任务分工变化；所以本阶段证明运行和审计链路，尚未证明历史
会改变伙伴后续协作，也未比较真实具身模型。

## 边界

Genesis 当前使用运动学 attachment；人类拿放是 Avatar 动作接口，物体未建成可产生
接触失败的刚体任务。需要加入真实接触、视觉标定、可控失败标签和训练后的 VLA/WLA
策略后，才能进行模型排行榜和 cobalance 泛化评测。Dataset CLI/API 已支持
`--backend genesis`，输出按 episode 目录和稳定文件名组织，不使用 `manifest.json`。

证据入口：`results/continuous_v2/genesis_v9/`、`results/continuous_v2/genesis_paired_v9/`。
