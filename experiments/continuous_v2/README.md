# HRC-Continuous v2

这是 v1 VC/Genesis pilot 之后的持续协作运行时。它解决的对象不是“把
状态机写得更长”，而是让人和机器人在同一个时间轴里并行执行动作，并
允许策略在动作块执行中根据新的公开观测重新选择动作。

## 当前实现

- `src/hrc_pilot/continuous.py` 提供 `ContinuousScenario`、`ContinuousWorld`、
  `AdaptivePartner` 和公开观测到动作块的接口。
- 六个场景对应 relay、nested support、concurrent overlay、history
  reinterpretation、robot-induced rebalance、leave-and-return。场景由物体、
  区域、任务分工和伙伴参数组合，不用第 N 步事件表驱动。
- 伙伴的参数被冻结以便复现，但其行为会随着机器人当前占用、可见进度、
  距离、工作负载和信任连续变化。它不会读取机器人的隐藏目标或评测标签。
- 每个 episode 输出 `trace.jsonl`、`events.jsonl` 和 `metrics.json`，顶层
  `index.html` 汇总场景、动作、打断和接近警告。
- `generate_scenarios(count, seed)` 会生成不同布局、目标区域、公开分工和伙伴
  可用性的实例；实例不携带固定的事件时间表，伙伴根据观测、距离、负载和
  机器人占用连续地改变行为。
- `ModelPolicy` 接受 VLA 的 RGB 加结构化输入或 WLA 的文本/状态输入，并把
  JSON 动作统一解码为 `Action`。`GreedyPublicPolicy` 仅用于检查协议，不是模型
  能力结果。

## 运行

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/formal
```

或在安装项目后使用：

```bash
hrc-continuous --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/formal
```

生成一批可作为开发/压力测试实例的场景：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/generated \
  --generated 20 --scenario-seed 42
```

每个 episode 目录是一个独立数据单元。`scenario.json` 保存实例条件，
`public_observations.jsonl` 和 `policy_io.jsonl` 保存模型可见输入及动作，
`trace.jsonl`/`events.jsonl` 保存审计轨迹，`metrics.json` 保存独立评测结果。
Genesis 后端的 RGB 文件按 `observation_<step>_<index>.png` 命名，可依据
JSONL 中的 `rgb_artifact` 稳定配对；不依赖 `manifest.json`。

## 证据边界

`ContinuousWorld` 是不依赖 Genesis 的参考后端，用来验证 benchmark 协议、
连续伙伴和记录/评测逻辑；它不声称完成接触动力学。`continuous_genesis.py`
已经提供 `GenesisContinuousAdapter`，而 `VCWorkspace` 也提供逐 tick 的
机器人动作队列和 Avatar 拿放动作入口。当前 VC 场景仍使用 v1 的固定两杯
布局和运动学夹持抽象，尚未把六个 v2 场景全部实体化为经过验证的 Genesis
资产，因此还不能把这次报告称为真实机械臂模型排行榜。下一步是在该适配面
上加入接触安全量、视觉标定、基础技能失败标签和真实 VLA/WLA 推理；然后用
训练/开发/测试场景分割和多 seed 结果报告模型的泛化与协调代价。
