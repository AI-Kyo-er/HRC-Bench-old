# HRC-Continuous v2

## 2026-10-06：真实机器人接触与生成式伙伴

[本阶段完整报告与 4 条真实 Sim 视频](../dynamic_contact_20261006/index.html)。
新增自由刚体摩擦抓放后端，独立 IK 教师实际完成抓放；原生 π0.5 + Qwen3-14B
运行接力、并行、重新协调三类任务，共 75 次机器人推理、41 次人类模型决策。
两条由人接管完成，一条失败；机器人合法贡献均为零。人体拿放出现约 1 米的单帧
跳变，三条均未通过动作连续性核查，只作诊断，不进入正式 Benchmark 成绩。
完整目标仍在进行，下一步优先替换人体拿放、建立真实模型基础操作表现，再扩展
动态伙伴与长时段、多任务评测。不要将旧的吸附结果与当前接触结果混为同一后端。

这是 v1 VC/Genesis pilot 之后的持续协作运行时。它解决的对象不是“把
状态机写得更长”，而是让人和机器人在同一个时间轴里并行执行动作，并
允许策略在动作块执行中根据新的公开观测重新选择动作。

## 2026-10-05 最新可核查进展

## 2026-10-06 最新视频核查

- [九类任务族动态伙伴 Genesis 正式运行 v2](../../results/continuous_v2/task_catalog_genesis_v2/index.html)：固定
  seed 0、`greedy_public` 机器人协议基线、`dynamic` 伙伴和 Genesis，覆盖
  `serial_relay`、`concurrent_overlay`、`nested_support`、
  `interruption_reprioritization`、`leave_and_return`、
  `robot_induced_rebalance`、`history_reinterpretation`、
  `trait_dependent_open_task`、`held_out_task_composition` 九类任务族。
  9/9 活动契约完成；其中 5 条发生机器人角色失败并由伙伴重新分工或接管，另有
  1 条记录公开重规划。9/9 episode 均有真实运行时 `demo.mp4`，并通过
  `video_timeline.json` 完整解码核验。该运行首次把任务族目录、动态伙伴、失败/延迟、
  重新分工、数据记录和真实 Sim 视频放在同一批正式结果中；它仍是规则策略、单 seed、
  运动学 attachment 的平台机制证据，不是 VLA/WLA 排行榜。
  [汇总 JSON](../../results/continuous_v2/task_catalog_genesis_v2/summary.json)
  · [视频核验](../../results/continuous_v2/task_catalog_genesis_v2/video_verification.json)

- [六场景动态意图伙伴 Genesis 报告](../../results/continuous_v2/dynamic_genesis_v2/index.html)：同一
  seed 下运行 `relay`、`nested_support`、`concurrent_overlay`、
  `history_reinterpretation`、`robot_induced_rebalance` 和 `leave_and_return`。
  6/6 episode 均有可解码的真实 `demo.mp4`、RGB、关节轨迹和完整
  `video_timeline.json`；每个视频都能从报告中的事件跳转到对应 benchmark 时间。
  六个活动契约均完成，其中两个扰动场景各记录一次失败、延迟和伙伴重新分工，
  `leave_and_return` 记录公开重规划。这是动态伙伴和视频链路的机制验证，不是
  VLA/WLA 或真人 HRC 能力结果。

- [匹配当前输入的历史实验](../../results/continuous_v2/matched_history_genesis_v2/index.html)：
  三 seed 下，首次观察 / RGB / 动作和回答前完整伙伴输入 / RGB 五项匹配全部
  通过；可靠历史接受、失败历史拒绝，冻结适应后差异消失。共 18 条真实视频，
  其中 6 条历史来源复用已完成运行、12 条探针新跑。明确重建当前世界的诊断，
  尚非无重置活动或真人规律。
- [关节抓放校准](../../results/continuous_v2/joint_calibration_genesis_v1/index.html)：
  公开几何 IK 教师只输出关节位置，实际靠近 / 夹爪闭合才触发物体绑定，打开
  后在实际位置释放。双相机实际 RGB 可查看；抓放仍是运动学抽象。
- 真实官方 π0.5-DROID 已接入，[6 秒运行](../../results/continuous_v2/pi05_droid_genesis_v1/index.html)
  和 [30 秒运行](../../results/continuous_v2/pi05_droid_genesis_v2/index.html) 分别调用模型
  12 / 57 次，执行 90 / 450 个关节目标。两条均未完成收纳，原始失败、视频和
  动作块全部保存。这是模型接入证据，尚无持续 HRC 能力结果。当前 OpenPI
  入口已支持动态伙伴；后续重要纵切片必须记录伙伴 profile、公开记忆和意图审计。
- [π0.5-DROID + 动态伙伴纵切片](../../results/continuous_v2/pi05_droid_dynamic_genesis_v2/index.html)：
  固定 seed、30 秒、15 Hz，动态伙伴实际处理红杯，真实模型处理蓝杯；模型调用 57 次、
  执行 450 个关节目标，保留 480 帧 / 15 FPS 的运行时 `demo.mp4` 和完整时间轴。
  人完成红杯但模型未完成蓝杯，整体任务失败。伙伴记录 4 次意图切换、2 条记忆写入、
  96 次检索和 4 次反思。这证明真实模型、动态伙伴反馈和视频审计链路已接通，不能
  解释为模型 HRC 能力排行榜；运动学 attachment、程序化伙伴和单 seed 仍是明确限制。
- [评分修订后关节校准](../../results/continuous_v2/joint_calibration_genesis_v2/index.html)
  与 [四条件恢复复核](../../results/continuous_v2/recovery_contract_genesis_v2/index.html)
  均保留真实视频和贡献事件；接管 / 重试 / 无失败完成，持续失败未完成。
- 新运行修复活动评分：必须释放到目标且提交符合依赖 / 交接的贡献；任意
  item_id 和接管方不会绕过同一约束。旧报告不重评分。

- [动态人类 benchmark 设计](dynamic_human_benchmark_design.md)：记录任务族目录、
  动态伙伴的 profile / memory / intention / reflection 审计、VLA/WLA 公开输入边界、
  泛化划分、指标和真实 Sim 视频门槛。`dynamic_genesis_v3` 是用仓库内 VC/Genesis
  环境完成的单场景视频烟测，报告中的 `relay/demo.mp4` 已通过逐帧解码与时间轴核查。

详细目的、设置、逐项结论和未验证项见 [`genesis_validation.md`](genesis_validation.md)。
真实视频、外部 / 腕部 RGB、事件与关节状态在各报告中展示。下一阶段仍需同一
活动无重置、真实模型和可适应伙伴共同执行、接触 / 安全，以及操作难度匹配
的组合和留出比较；整个 benchmark 研究目标尚未完成。

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
- `--partner-mode` 可选 `fixed_replay`、`reactive`、`adaptive`、`dynamic`。前三者分别
  对应固定回放、只根据当前公开行为反应、以及保留公开历史后的适应式伙伴；
  `dynamic` 还维护按 seed 固定的伙伴 profile、公开事件记忆和可切换的长期意图。
- `ExternalPolicyAdapter` 接受 VLA 的 RGB 加结构化输入或 WLA 的文本/状态输入，
  把 JSON 动作统一解码为 `Action`，并记录推理耗时、原始输出与异常审计。
  `GreedyPublicPolicy` 仅用于检查协议，不是模型能力结果。

## 运行

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir results/continuous_v2/formal
```

或在安装项目后使用：

```bash
hrc-continuous --output-dir results/continuous_v2/formal
```

生成一批可作为开发/压力测试实例的场景：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir results/continuous_v2/generated \
  --generated 20 --scenario-seed 42
```

运行结构对照集合：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir results/continuous_v2/suite \
  --suite --count-per-condition 5 --partner-mode adaptive
```

重要实验使用 Genesis 时，应把 `--partner-mode dynamic` 显式写入命令，并保留每个
episode 的真实 Sim `demo.mp4`、RGB、关节轨迹和 `video_timeline.json`。参考后端
可以快速核对协议，但不替代真实 Sim 画面。

使用自定义场景契约：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir results/continuous_v2/custom \
  --scenario-file path/to/activity.json --paired
```

运行历史条件化的反事实门槛实验：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --history-counterfactual \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/history_counterfactual_v2 \
  --seed 3
```

该实验固定场景几何和伙伴初始条件，只替换机器人是否在执行贡献前公开求助，
用于检查失败、求助和接管是否会通过伙伴历史改变后续动作。结果目录包含两条
episode、`history_counterfactual_summary.json`、事件/轨迹/策略输入输出及可视化
报告。它是参考运行时的机制验证，不代表已测试真实 VLA/WLA、Genesis 接触动力学
或真人 HRC。

`activity.json` 只需定义对象、区域、角色目标和 `activity.work_items` 的
前置关系；它不包含逐步事件脚本。`scenario_from_dict`/`load_scenario` 也可
直接被数据集生成器调用。

扩展任务族目录（每个任务族生成五个布局实例）：

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src .venv-vc-pilot/bin/python \
  scripts/run_continuous_benchmark.py \
  --task-catalog --count-per-family 5 --partner-mode dynamic \
  --backend genesis \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/task_catalog_v1
```

如果要把同一目录作为可评测数据集发布，可使用数据集入口；它不会生成
`manifest.json`，而是按稳定的 split/family/name 路径匹配 episode：

```bash
PYTHONPATH=src python scripts/run_hrc_dataset.py generate \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/continuous_catalog \
  --task-catalog --count-per-family 5 --repeats 3 --partner-mode dynamic
```

正式 Genesis 运行应保留每个 episode 的 `demo.mp4`、`video_timeline.json`、RGB、
关节轨迹、`policy_io.jsonl` 和动态伙伴审计文件；可用以下命令强制检查视频和时间轴：

```bash
PYTHONPATH=src .venv-vc-pilot/bin/python scripts/verify_genesis_videos.py \
  --input-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/task_catalog_v1 \
  --require-timeline
```

完整的研究设计和字段约束见 `design.md` 与 `benchmark_schema.md`。

## 动画与中场报告

报告现在同时包含来自 `trace.jsonl` 的桌面俯视动画和（Genesis 后端时）每个 episode 的
真实 Sim `demo.mp4`。页面提供事件跳转、逐帧检查、播放速度，配对实验使用同一时间轴
并排展示伙伴。视频由 VC/Genesis 在运行时录制，另存 RGB 观测和 `trajectory.npz` 关节
轨迹；它不是用轨迹动画重新渲染。动画内嵌在 `index.html`，无需联网或启动服务器，
视频和原始文件通过每个面板的链接访问。
输入缺失字段显示“未记录”，历史场景未记录的活动契约不会从当前代码补入。

已有两组报告已重建，可从仓库中的软链接入口打开：

- [六场景报告与动画](../../results/continuous_v2/formal_v6/index.html)
- [三种伙伴配对报告与动画](../../results/continuous_v2/paired_v8/index.html)

Genesis 验证结果：

- [六场景 Genesis 报告（含真实 Sim 视频）](../../results/continuous_v2/genesis_v10/index.html)
- [Genesis 伙伴条件对照（18 个 episode，含真实 Sim 视频）](../../results/continuous_v2/genesis_paired_v10/index.html)
- [动态意图伙伴 Genesis 报告（真实 Sim 视频、RGB 与时间轴）](../../results/continuous_v2/dynamic_genesis_v1/index.html)
- [动态意图伙伴六场景 Genesis 报告（6 条真实 Sim 视频、RGB 与时间轴）](../../results/continuous_v2/dynamic_genesis_v2/index.html)
- [九类任务族 Genesis 报告（9 条真实 Sim 视频、RGB 与时间轴）](../../results/continuous_v2/task_catalog_genesis_v1/index.html)
- [九类任务族动态伙伴正式 Genesis 报告（9 条真实 Sim 视频、9/9 时间轴核验）](../../results/continuous_v2/task_catalog_genesis_v2/index.html)
- [历史反事实 Genesis 报告（含真实 Sim 视频）](../../results/continuous_v2/history_counterfactual_genesis_v1/index.html)
- [失败恢复三条件 × 三 seed（9 条真实 Sim 视频）](../../results/continuous_v2/recovery_genesis_v1/index.html)
- [持续失败未恢复核查（3 条真实 Sim 视频）](../../results/continuous_v2/recovery_negative_genesis_v1/index.html)
- [修复失败预算后的历史反事实，seed 0](../../results/continuous_v2/history_counterfactual_genesis_v2/index.html)
- [历史反事实，seed 1](../../results/continuous_v2/history_counterfactual_genesis_seed1/index.html)
- [历史反事实，seed 2](../../results/continuous_v2/history_counterfactual_genesis_seed2/index.html)

2026-10-05 补齐了 Genesis 与参考后端的失败预算一致性。新增 12 条恢复核查中，
3 条由人接管完成、3 条机器人重试完成、3 条无失败完成、3 条持续失败未完成。
这验证了公开失败反馈、分工更新和恢复分类，但不是训练模型的 HRC 成绩。
一次失败但禁止接管的条件在 Genesis 中仍成功，不能把它写成未恢复负例；
持续失败条件另行保存，作为分类核查。具体设置和逐条证据见
[`genesis_validation.md`](genesis_validation.md)。

重要实验必须保留运行时真实 Sim 视频，并与轨迹、公开观察、事件、关节状态及
实验说明一起提供；仅有轨迹动画不满足报告要求。新 Genesis episode 保存
`video_timeline.json`，逐帧记录视频时间、物理步和 benchmark 时间，报告据此定位
视频，并支持慢放及 RGB 对照。旧实验没有映射时保持独立播放，不补造时间信息。
正式 Genesis 报告生成会检查每个 episode 的 `demo.mp4` 非空；缺失时直接报错，
并在 `replay_verification.json` 写入视频覆盖率。参考 `ContinuousWorld` 报告明确
标记视频不适用，不会用轨迹动画冒充真实 Sim 画面。

使用已安装 VC 环境复现本次多 seed 实验（运行器会先用 `nvidia-smi` 选择至少有
4 GB 空闲显存的单卡；输出目录必须为空）：

```bash
PYTHONPATH=src .venv-vc-pilot/bin/python scripts/run_genesis_recovery.py \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/recovery_new \
  --seeds 0 1 2
```

默认运行四条件，共 12 条。用 `--conditions persistent_failure` 可以独立运行分类负例。
这些场景只声明失败预算 / 概率、接管概率和活动约束；失败随实际动作启动触发，
没有预先规定某一 tick 必须发生某事件。当前伙伴仍是可审计的规则模型。

`genesis_v10` 在 VC/Genesis 后端运行六个 v2 场景，使用 60 Hz 物理时钟、RGB
观察、视频和关节轨迹；六个场景的活动契约均完成。`history_reinterpretation` 和
`robot_induced_rebalance` 各记录了一个 `robot_action_delayed` 以及随后的伙伴
trust/reliability 更新，但本次 seed 没有记录 `robot_action_failed`，因此不能把
结果描述为失败后的恢复。视频中的物体仍使用运动学 attachment；这验证后端和记录
链路，不是 cobalance 能力已被证明的结果。

`results/continuous_v2` 指向 `/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/`。
数据盘负责实际存储；查看报告与执行下面命令使用仓库路径，命令在仓库根目录运行。

报告围绕研究动机解释机器人如何驱动、伙伴如何变化、哪些变化实际被触发，
并区分当时运行证据、后续工程能力与尚未验证的研究假设。原页面保存在
`index.before-replay.html`；源文件哈希和逐帧伙伴比较保存在 `replay_verification.json`。
这些核查文件不承担 episode 配对。

只读取原始结果重建报告，不重新运行仿真：

```bash
PYTHONPATH=src python scripts/rebuild_continuous_report.py \
  --input-dir results/continuous_v2/formal_v6
PYTHONPATH=src python scripts/rebuild_continuous_report.py \
  --input-dir results/continuous_v2/paired_v8
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
可替换的最小 Python 包装见 [`examples/hrc_external_policy_adapter.py`](../../examples/hrc_external_policy_adapter.py)：
VLA 接收 RGB 加公开结构化观测，WLA 接收公开结构化/文本状态，二者都只能返回
定义好的 `Action` JSON。

每个 episode 的 `metrics.json` 还包含贡献互补、失败恢复、协调效率和
`cobalance_score` 四个透明组件。`recovery_status` 明确区分
`no_failure`（没有发生失败，`recovery_success` 为 `null`）、
`recovered_after_failure`（失败后完成，值为 `1.0`）和 `failed_to_recover`
（失败后未完成，值为 `0.0`）。聚合结果同时给出三类状态计数，避免把“没有失败”
误读为“成功恢复”。这些指标是当前 benchmark 的协议代理指标，
用于比较模型如何维持共同活动，不把模拟伙伴状态直接解释为真人心理量。
数据集 `summary.json` 会为各分组指标附带确定性 bootstrap 95% 区间。

## 证据边界

`ContinuousWorld` 是不依赖 Genesis 的参考后端，用来验证 benchmark 协议、
连续伙伴和记录/评测逻辑；它不声称完成接触动力学。`continuous_genesis.py`
已经提供 `GenesisContinuousAdapter`，六个 v2 场景现在都可在该适配器上运行。
VC 资产仍使用运动学夹持绑定，人的拿放仍是 Avatar 动作接口，物体碰撞和接触
力没有作为真实失败来源。因此这些结果是可复现的后端接缝和机制审计，不是接触
动力学或真实机械臂模型排行榜。下一步是在该适配面上加入接触安全量、视觉标定、
基础技能失败标签和真实 VLA/WLA 推理。

## 复现匹配历史与真实 VLA

匹配历史运行器从公开历史学习，不读 evaluator 状态注入判断：

```bash
PYTHONPATH=src .venv-vc-pilot/bin/python scripts/run_matched_history_probe.py \
  --backend genesis --seeds 0 1 2 \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/matched_history_new
```

真实模型与 Genesis 使用独立 Python 环境，分别位于数据盘 `envs/openpi` 与
`envs/vc-pilot`，仓库软链接为 `.venv-openpi` / `.venv-vc-pilot`。官方源码从
`vendor/openpi` 软链接访问，权重从 `models/pi05_droid` 访问。全部大文件、
缓存与结果实际存储在数据盘。已有权重的历史核查包含官方 GCS MD5；历史下载
工具不属于当前允许的新下载路径。后续模型和数据仅可从中国大陆镜像或本土服务
获取，禁止通过 VPN 下载。本阶段直接使用已有权重并启用离线推理。

启动前查看 `nvidia-smi`：本次 OpenPI 单卡占约 20 GB（设置 JAX 预分配 40%），
Genesis 单卡预留至少 4 GB。示例卡号是本轮空闲的 GPU 1 / 0，复现时据空闲
显存选择，并固定每个进程只用所选单卡。先在一个终端启动模型服务：

```bash
CUDA_VISIBLE_DEVICES=1 XLA_PYTHON_CLIENT_MEM_FRACTION=0.4 \
OPENPI_DATA_HOME=/data1/sieniwgroup/sieniw/models/Physical-Intelligence/openpi-cache \
.venv-openpi/bin/python scripts/serve_openpi_droid.py
```

看到“模型已加载”和端口就绪后，在另一个终端运行：

```bash
PYTHONPATH=src CUDA_VISIBLE_DEVICES=0 VICO_PILOT_MINIMAL_IMPORTS=1 \
.venv-vc-pilot/bin/python scripts/run_openpi_benchmark.py --ticks 450 \
  --partner-mode dynamic --human-profile balanced \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/pi05_droid_new
PYTHONPATH=src .venv-vc-pilot/bin/python scripts/verify_openpi_run.py \
  --input-dir results/continuous_v2/pi05_droid_new
```

这条纵切片中人动态处理红杯，机器人处理蓝杯；原生模型只看到真实双相机、本体和公开语言，没有物体坐标；具体输出是
10×8 速度 / 夹爪动作块，15 Hz 转关节目标，最多执行前 8 步再推理。消息更新
会使旧块失效。包装器不替模型生成协商或求助。当前同步推理暂停模拟时钟，
尚未验证真实推理延迟对伙伴的影响；相关耗时单独保存。

验证脚本核对真实 PNG 哈希、每个动作的数值转换与视频完整解码，不以审计
通过替代任务成功。任务未完成 / 没有失败事件不等于“已经成功恢复”。
