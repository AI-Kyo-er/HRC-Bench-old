# v3.2：停车接触修复与多物品进度诊断

本阶段在独立目录修复和诊断，保留v3.1冻结代码、原始神经调用、物理轨迹及高力接触。没有新增3B连续formal，未重新调整v3.1提示或评分。环境仍为数据盘上的pybullet3.2.7与原固定Qwen2.5-3B权重；完整数据通过 `results/physical_v3_2/raw` 链接访问。

## 控制修复与实测

v3.1在伙伴拒绝后绕行抓放成功，随后直接关节插值回home，机械臂停车路径扫到伙伴占位块。v3.2的 `SafeParkingWorld`继承冻结世界，不修改父实现；截获park阶段，以关节电机执行侧向抬升（x=.52，y=目标侧±.40，z=.40）、侧向收臂（x=.30，z=.45）后再回home。没有运行期物体或关节reset、attachment或直接赋值成功。每个物理step监测整个robot与partner所有link的接触，而非只查末端waypoint。

最终不可变日志版控制覆盖：

| 控制 | 覆盖 | 物理任务完成 | robot-partner接触 |
|---|---|---:|---:|
| 基础直接抓放 | 三物品×两目标，无占位 | 6/6 | 0 tick |
| 基础绕行抓放 | 三物品×两目标，实际占位 | 6/6 | 0 tick |
| 连续公开规则控制 | seed20/21 × 接受/拒绝 × upfront/revision | 8/8 | 0 tick |

20条控制共123,600个240Hz物理step，伙伴电机不到位0，最大停车航点误差0.0002193m。运行时计数与独立读取 `ticks.jsonl.gz` 的接触审计一致；既有记录不会被后续history追加污染。结果见 `control_summary.json` 与 `trajectory_audit.json`。第一轮同一修复已取得相同无接触结果，但发现日志引用问题后在 `raw/controls_immutable` 完整复跑；`control_before_logging_fix.json`及`raw/controls`保留为开发尝试，最终证据使用不可变记录。

此修复只证明覆盖场景中robot-partner未发生接触，不是全场景碰撞规划或真人安全验证。抓取中的robot-object接触与物体-托盘接触是正常物理过程，不能把“robot-partner无接触”简写为“所有接触为零”。父实现的中央waypoint前提屏障仍是粗略几何检查；没有泛化到新人体形状、运动、资产或任意初态。

代表联系图/视频在 `raw/controls_immutable/control_revision_21_0/contact_sheet.png`和同目录 `rollout.mp4`，对应拒绝后绕行和无接触停车。原v3.1停车碰撞保留在 `results/physical_v3/trajectory_audit.json`及原始压缩轨迹。

## 96步原始消息审计与日志勘误

逐步审计原v3.1模型的96次原始 `messages`：system与冻结一致；真实传入观察保留历史前缀和上一步反馈；物理区域与位姿/速度一致；20候选全部存在；没有按隐藏评分目标给免费完成标志。传入检查违规0。

发现一项真实记录bug：`row.observation.history`引用Episode可变events列表，保存时变成最终历史，96条记录都与实际传入消息不等，差异只在history字段。这没有改变已即时序列化、实际送入 `predict` 的messages，也没有向模型传入未来事件。旧raw保持不变；v3.1 README和执行回执已勘误，另存 `canonical_representative_calls.json` 从原始messages恢复正确观察。新记录通过deepcopy断开引用，并新增针对后续事件追加/物理区域修改的永久回归测试。

因此重复green不是这个日志别名bug造成的历史传入错误。审计支持“本配置未稳定使用多物品进度”的行为诊断；它不能排除提示样例锚定、表达/长度、候选ID理解或模型规模等原因，也不能确定模型内部原因。规范输入以原始messages为准，不能用污染的旧row.observation.history重建决策。

## 独立多物品开发对照

新开发fixture由上述失败启发，但未复制旧formal状态：已完成red/blue/green × 目标反转 × 候选正常/反序，共12个状态。每个状态有两个未完成物品、完整20候选和多个有效推进动作。fixture的位姿/区域是明确构造的接口状态，不是物理rollout。`cases/dev_freeze.json`在推理前冻结；没有边运行边调提示。

两view使用相同v3.1系统提示：full_history给完整公开历史与区域；public_progress_aid额外附确定性归约出的当前目标、已完成/剩余物品及授权信息，归约只读公开历史和物理区域，不读隐藏case目标。候选不筛选、内容和顺序在配对view相同。辅助属于外部信息加工baseline，是已有状态维护思想的诊断应用，不能称新方法或裸模型；两view token长度不同，不作纯提示长度或结构因果估计。

| 观察 | 有效推进选择 | 已完成red | 已完成blue | 已完成green |
|---|---:|---:|---:|---:|
| full_history | 4/12 | 2/4 | 2/4 | 0/4 |
| public_progress_aid | 6/12 | 3/4 | 1/4 | 2/4 |

24次单调用全部JSON合法，无输出截断。辅助总体多两次推进，但一组分层下降，仍有对象/目标错误；不能说公开摘要解决了失败。这里不是12个闭环任务完成率，没有操作或伙伴回应效果估计。完整原始输入输出、集合评分、token和耗时在 `raw/dev/calls.json`；小摘要与配对选择在 `progress_dev_summary.json`和`dev_pair_analysis.json`，代表原始调用在 `representative_calls.json`。

## 验证与复现

15项永久测试通过，包括旧语言/符号机制、新物理协议、候选顺序控制、公开辅助的局部修正保留其他目标及日志不可变回归。规范输入审计和每tick独立接触审计通过。主要运行句柄：53401开发控制exit0；63158不可变版控制exit0；63476模型开发exit0；15536测试exit0；42679只读报告exit0。模型退出后GPU3已释放，未启动下一批formal。

```bash
.venv-llm/bin/python -m unittest discover -s tests -v
.venv-llm/bin/python -m experiments.physical_v3_2.audit
.venv-llm/bin/python -m experiments.physical_v3_2.run controls --output-dir results/physical_v3_2/raw/reproduce_controls
nvidia-smi --query-gpu=index,memory.free --format=csv
CUDA_VISIBLE_DEVICES=3 .venv-llm/bin/python -m experiments.physical_v3_2.run dev --output-dir results/physical_v3_2/raw/reproduce_dev
```

输出目录非空时拒绝覆盖；已有开发冻结禁止重建。模型运行前重查显存，3B预计<12GB。执行回执记录v3.1冻结未改的SHA、新开发冻结、源/资产/包版本和轨迹/调用校验。尚未全量复跑神经推理以验证完全确定性。后续先决定更强模型和更细的独立基础控制，再设计严格匹配的交互依赖比较；当前结果不支持交互组合能力或论文级推广结论。
