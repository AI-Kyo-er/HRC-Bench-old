# 2026-10-05：Genesis 失败恢复与视频证据

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-05
- Verification Status: UNVERIFIED（研究效度与完整可复现性；局部工程检查另列）
- Version Label: genesis_recovery_v1

## 必须持续保留的用户要求

重要实验不能只有轨迹动画，必须提供运行时真实 Sim 视频。报告面向没有参与
长程运行的人，说明目的、条件、机器人驱动、伙伴机制、过程、结果及证据边界。
任务环境要支持真实具身模型，不把状态机或手写策略的成功称为模型能力。
研究核心仍是持续共同活动中交互结构的组合与演化，以及机器人行为如何改变人
的后续协作方式；不是把研究目标收窄成失败接管。

## 本次实际完成

- Genesis 原先忽略 `robot_failure_budget`；现在 episode 重置预算，实际启动搬运
  时消耗，产生公开失败反馈。参考后端已有同一语义。
- `history_counterfactual_genesis_v2`、`history_counterfactual_genesis_seed1`、
  `history_counterfactual_genesis_seed2` 共 6 条：直接执行均一次失败后人接管；
  先求助均无失败完成。视频和事件原始数据保留。
- `recovery_genesis_v1` 共 9 条（3 seed × 3 条件）：可接管 3/3 由人完成；
  不接管 3/3 由机器人重试完成；无失败 3/3 完成。
- `recovery_negative_genesis_v1` 共 3 条：持续合成失败且不接管，全部未恢复；
  每条 30 次失败，3 秒时限。此条件只用于分类核查，不能替代匹配的因果对照。
- 新 12 条恢复视频保存逐帧 `video_timeline.json`，完整解码核对帧数、fps 和终态
  时间。报告支持慢放、事件跳转、RGB 对照、关节位置和明确的策略 / seed 标识。
- 正式测试 47 项通过，Python 编译、JavaScript 语法、diff 格式检查通过。
  三份主要报告共 14 条运行的 Chromium 离线检查通过，无 JavaScript 错误。
- `scripts/run_genesis_recovery.py` 提供可复现多 seed / 条件入口，默认四条件。
  输出仍按 `seed_NNN/<scenario>/` 组织，不生成配对 manifest。

所有大文件位于 `/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/`，
仓库 `results/continuous_v2` 为软链接。说明及结果表见
[`genesis_validation.md`](../../../../experiments/continuous_v2/genesis_validation.md)。

## 不能跨越的证据边界

策略仍是手写 `greedy_public` / `request_help_public`，没有实际 VLA/WLA 权重推理。
Genesis 物体使用无碰撞运动学 attachment；人的拿放是 Avatar 接口。一次合成失败
后公开接管成立，但不证明真人信任变化、真实接触恢复或模型 cobalance 泛化。
相同几何的动作分化也没有匹配当前公开消息，因此不能独立识别持久历史的因果作用。
当前动作时长很短，不能用来估计真人 / 真机效率。

## 全目标尚需完成

1. 在匹配当前公开输入与剩余任务的条件下，运行完整历史 / 状态冻结 / 当前反馈
   消融，证明过去机器人表现影响未来伙伴行为，而不是仅发生公开消息路由。
2. 搭建有物理必要性的支持、交接、干预和持续任务依赖，核查六结构标签真正产生
   可测约束；避免靠标签或更长时长制造所谓组合难度。
3. 接入训练后的具身模型，验证相机、机械臂状态、动作规范和技能执行的标定，
   分别报告操作失败和协调失败。
4. 建立训练 / 开发 / 结构留出数据划分，对多模型运行同任务对照；伙伴行为需要
   多参数与后续真人校准，不能把手写伙伴心理变量当真人测量。

因此总研究目标仍保持 active，本次只完成恢复链路与报告证据的一个阶段。
