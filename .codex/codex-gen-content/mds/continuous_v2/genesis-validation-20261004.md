# 2026-10-04 Genesis v2 验证进度

- 已修复 v2 闭环：模型接收真实 RGB 像素，Genesis 以 60 Hz 推进并映射到场景 tick，episode 输出绑定和 close 生命周期完整。
- 已在 GPU 1 完成六场景 `genesis_v9`；活动契约六项均成功，但 `human_reassignments=0`，不能把结果解释为 cobalance 已验证。
- 已在 GPU 1 完成 `genesis_paired_v9` 的两个高变化场景和 fixed/reactive/adaptive 三种伙伴条件；延迟被记录，仍没有接管差异。
- Dataset CLI/API 已支持 `--backend reference|genesis`，并记录 backend provenance；已在 GPU 2 生成一份 Genesis episode 数据集检查样例。
- 当前 Genesis 限制：运动学 attachment、Avatar 拿放接口、无接触失败/安全评测；策略仍是 `greedy_public`，没有训练后的 VLA/WLA 权重。
- 正式证据入口：`results/continuous_v2/genesis_v9/`、`results/continuous_v2/genesis_paired_v9/`；阶段说明见 `experiments/continuous_v2/genesis_validation.md`。
