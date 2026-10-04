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
- `generate_benchmark_suite` 生成 `isolated`、`matched_serial`、`compositional`
  和 `held_out` 四类结构条件；`InteractionStructure` 记录作用片段、跨片段
  依赖、并发关系和 train/dev/test 划分。它用于组织数据和评测，不是逐步
  触发器。
- `ActivityContract` 把“真实场景”落成可执行约束：活动目标、工作项、前置
  承诺、共享资源、允许交接和重规划触发器。运行时只在动作提交时检查约束，
  不使用第 N 步事件表；前置不满足时会产生公开 `action_blocked` 反馈。
- `--partner-mode` 可选 `fixed_replay`、`reactive`、`adaptive`。三者分别
  对应固定回放、只根据当前公开行为反应、以及保留公开历史后的适应式伙伴。
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

运行结构对照集合：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/suite \
  --suite --count-per-condition 5 --partner-mode adaptive
```

使用自定义场景契约：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/custom \
  --scenario-file path/to/activity.json --paired
```

`activity.json` 只需定义对象、区域、角色目标和 `activity.work_items` 的
前置关系；它不包含逐步事件脚本。`scenario_from_dict`/`load_scenario` 也可
直接被数据集生成器调用。

完整的研究设计和字段约束见 `design.md` 与 `benchmark_schema.md`。

## 动画与中场报告

报告现在包含来自 `trace.jsonl` 的桌面俯视动画、事件跳转、逐帧检查、播放速度，
配对实验使用同一时间轴并排展示伙伴。动画内嵌在 `index.html`，无需联网或启动服务器。
它只回放保存的位置和动作，没有补造关节轨迹、人体姿态、接触过程或最后终态。
输入缺失字段显示“未记录”，历史场景未记录的活动契约不会从当前代码补入。

已有两组报告已重建，结果仍位于外部存储：

- `/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/formal_v6/index.html`
- `/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/paired_v8/index.html`

报告围绕研究动机解释机器人如何驱动、伙伴如何变化、哪些变化实际被触发，
并区分当时运行证据、后续工程能力与尚未验证的研究假设。原页面保存在
`index.before-replay.html`；源文件哈希和逐帧伙伴比较保存在 `replay_verification.json`。
这些核查文件不承担 episode 配对。

只读取原始结果重建报告，不重新运行仿真：

```bash
PYTHONPATH=src python scripts/rebuild_continuous_report.py \
  --input-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/formal_v6
PYTHONPATH=src python scripts/rebuild_continuous_report.py \
  --input-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/paired_v8
```

详细的回放方法与证据边界见 `replay_report.md`。

每个 episode 目录是一个独立数据单元。`scenario.json` 保存 evaluator 私有实例条件，
`public_scenario.json`、`public_observations.jsonl` 和 `policy_io.jsonl` 保存模型可见输入及动作，
`trace.jsonl`/`events.jsonl` 保存审计轨迹，`metrics.json` 保存独立评测结果。
`public_scenario.json` 只含任务语义和几何，不含角色目标、伙伴动力学、活动契约或资产引用。
Genesis 后端的 RGB 文件按 `observation_<step>_<index>.png` 命名，可依据
JSONL 中的 `rgb_artifact` 稳定配对；不依赖 `manifest.json`。

`metrics.json` 另外记录 `activity_success` 和 `blocked_transfers`：前者按活动
契约的工作项终态评分，后者帮助区分单纯操作失败和跨贡献依赖带来的协调成本。

除了内置 suite，也可以直接从场景契约目录生成数据集。目录中的每个 JSON 是一个
场景，文件名和 `name` 必须稳定且唯一；场景只声明工作项、前置关系和可重规划边界，
不需要预写逐步事件脚本：

```bash
PYTHONPATH=src python scripts/run_hrc_dataset.py generate \
  --scenario-dir path/to/scenarios \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/my_tasks \
  --repeats 3 --partner-mode adaptive
```

随后用 `hrc-dataset evaluate` 对同一批 episode 运行任意 VLA/WLA 适配器，
评测器仍从私有 `scenario.json` 独立计算活动终态、接管、重规划、冲突和伙伴状态变化。

## 证据边界

`ContinuousWorld` 是不依赖 Genesis 的参考后端，用来验证 benchmark 协议、
连续伙伴和记录/评测逻辑；它不声称完成接触动力学。`continuous_genesis.py`
已经提供 `GenesisContinuousAdapter`，而 `VCWorkspace` 也提供逐 tick 的
机器人动作队列和 Avatar 拿放动作入口。当前 VC 场景仍使用 v1 的固定两杯
布局和运动学夹持抽象，尚未把六个 v2 场景全部实体化为经过验证的 Genesis
资产，因此还不能把这次报告称为真实机械臂模型排行榜。下一步是在该适配面
上加入接触安全量、视觉标定、基础技能失败标签和真实 VLA/WLA 推理；然后用
训练/开发/测试场景分割和多 seed 结果报告模型的泛化与协调代价。
