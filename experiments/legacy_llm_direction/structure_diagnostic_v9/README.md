# 第九轮：真实参考轨迹上的14B离线作用域诊断

本轮80次调用已完成。原始历史视图协议推进34/40，公开归约辅助视图40/40。差异集中在局部指导已结束后的D5：原始历史2/8，辅助8/8。6次失败全部再次输出`finish_guidance`，属于已结束作用域仍被再次finish、未推进；没有观察到这6次选择了错误blue目标，不能将它们称为6个目标记忆错误。

这是独立离线单决策诊断，条件是已有规则参考轨迹。模型输出没有接回环境，没有执行新的物理动作，也没有产生模型自主episode。旧14B基础门槛single16/16、full9/12、aid12/12仍为未通过；本轮不设新gate、不替代或放宽旧gate，不据此启动神经物理评测。

## 来源与冻结

来源为v7八条真实摩擦抓放参考轨迹，每条全部五个决策，共40个检查点；outerblue left/right × seed60/61 × 菜单normal/reverse独立交叉。来源文件是`results/structure_v7/raw/reference/B_neutral_{left|right}_{60|61}_{normal|reverse}/decisions.json`；稳定stem和决策序号用于配对，不使用manifest。

- v7来源freeze：`experiments/structure_v7/cases/reference_freeze.json`，SHA256 `c5e25a7966c027b9ab1918616bcd5fcfd023102ba56211ed6ed3ad66d843362e`。
- 本轮freeze：`cases/freeze.json`，SHA256 `c3fd2f1d056a409066406ab045c7c439f8a8b297cbc6127b119a282a223e9e4e`。
- 80冻结输入：`results/structure_diagnostic_v9/raw/frozen_inputs.json`，SHA256 `5293e59cdcaf7550f936492e6dac3b49bbbb08645a57231672d97baab32823fb`。

freeze在模型运行前保存了9个来源文件hash、8个运行及依赖源码hash、model spec/download receipt hash、80条token长度和生成参数。所有80条输入都保存完整messages。case标签、seed、参考动作与目标分组只在评分元数据中，不额外送入模型。

`full_history`逐字使用原v7规范messages，原system/history/22候选/预算/位姿不改。`public_scope_aid`保留原system和原user字节前缀，仅在user JSON末尾追加`external_public_scope_aid`。两视图每点各调用一次，按full→aid交替，无输出历史累积。

辅助只读原公开字典事件历史和`physical_placements`，复用v7的`reduce_history`，显式给出当前目标、scope active/ended/检查通过、实际区域、依当前公开目标的完成/剩余物品、yield/终止义务及已接受清道帮助，并注明来源。它不读取case/参考动作/未来/隐藏评分完成标签。这是额外公开归约帮助，且同时增加多种信息；不能单因素归因为仅目标提示，更不能称裸模型能力。归约器适用于当前单child模板，不是任意深度作用域栈。

## 多解评分及结果

评分基于公开历史和实际区域推导协议推进集合，参照动作命中单列。合法无推进yield/request与协议拒绝单列，不把全部合法动作算推进。候选抓放没有在本轮执行，所有评分显式记录`physical_execution=false`、`physical_success=null`。

|检查点|公开状态下的推进候选|full|aid|实际模型选择|
|---|---|---:|---:|---|
|D1 child活动，blue尚未暂存|stage_blue_neutral；place/careful_green_right|8/8|8/8|两视图全stage|
|D2 实际占位，已接受先yield|yield|8/8|8/8|两视图全yield|
|D3 已检查、green尚未完成|place/careful_green_right；finish_guidance|8/8|8/8|两视图全finish|
|D4 green已完成，child仍活动|finish_guidance|8/8|8/8|两视图全finish|
|D5 child已结束，blue仍neutral|place/careful_blue_外层目标|2/8|8/8|full左normal成功2次，其余6次重复finish；aid全选正确blue直接抓放|
|合计|协议推进|34/40|40/40|没有解析失败或截断|

参照命中分别26/40、32/40，不能代替多解推进评分：D3提前finish合法，green完成不是终止child的硬前提，所以这16次不应按参考green动作判错。全部模型选择均未触发green抓放、careful、assisted或request_clear；本轮没有证明这些操作在该输入上可用。

D3的预测finish不改变D4输入：D4仍是规则参考轨迹中的child活动状态。D4/D5上的连续finish不能解释为模型自主执行两次，因为各检查点独立；只有D5原输入已经结束scope时的再次finish是拒绝/未推进。

|D5目标×菜单（每格2seed）|full推进|aid推进|
|---|---:|---:|
|left normal|2/2|2/2|
|left reverse|0/2|2/2|
|right normal|0/2|2/2|
|right reverse|0/2|2/2|

D5左右配对：full四组为one-correct两组、none-correct两组、two-correct零组；aid四组均two-correct。D1–4所有左右配对都two-correct。40个full→aid变化为34个correct→correct、6个incorrect→correct，没有correct→incorrect。分阶段×view×目标×菜单的全表和40配对保存在`summary.json`，不从两seed或反序描述性差异推断统计规律。

六失败原messages、原输出、acceptable集合、aid原messages/输出及唯一增加字段保存于`raw/failure_pairs.json`，薄索引为`failure_audit.json`。失败分布：两个seed各3，normal右2、reverse左2/右2。所有full/aid原物理字段相同，原blue为neutral；预测从未执行，物理tick增量0，不声称测得物理恢复成功。

## 等同性和解释边界

四组同seed/menu左右D5在去掉整个history后可见输入逐字段相同；相同菜单两目标原历史仅outerblue left/right一处不同，有效blue目标集合不交。14B tokenizer给seed60的D5 full 1950tokens、seed61的1949tokens，normal/reverse和左右各自等token数，左右仅一个token替换。1949/1950差异来自seed对应真实位姿文本，不是菜单；字符长度与token长度不同。因此可排除该配对的token-count捷径，不能排除词面、固定模板或阶段代理。

历史是v7真实脚本共同背景，不是模型自行协商。任务固定单层child，原历史没有永久目标修正的对照；只查最初outerblue字段也可能回答正确，不足以证明一般作用域推理。D4/D5实际物理相同但预算9/8、历史10/13事件不同；这些阶段线索保持真实输入，未为追求等信息而重写。辅助改善同时涉及作用域、目标、进度等因素；裸历史失败仍容许接口表达/上下文使用等解释。无history策略也可能通过协议反馈或试错完成整段，目标集合不交只约束未获反馈前的这次blue放置选择。

本轮只提供参考轨迹条件下离线诊断证据，不是闭环成功率、结构留出、组合泛化、物理成功、因果隔离或新方法效果。

## 模型、资源与验证

使用既有本地Qwen/Qwen2.5-14B-Instruct，官方revision `cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8`，八分片官方LFS SHA验证沿用且绑定旧receipt SHA；本轮无下载，配置/tokenizer文件SHA重新比对旧核验回执相同。torch2.6.0+cu124、transformers4.49.0，单卡BF16/SDPA、greedy seed0、max_new_tokens96、batch1，无量化/offload/多卡。

最大输入2118tokens，含96输出的KV估计415.125MiB；BF16分片字节+3GiB要求free31244MiB。真实启动前GPU2 free32278MiB，选该单卡；峰值PyTorch allocated 30,389,625,344bytes。初始/结束UTC、PID4192973、GPU前检及model metadata保存在raw/model和execution_receipt。模型句柄32772真实exit0，80/80保存；PID已退出且不在GPU进程中，未操作其他任务。

新增五项永久协议/输入回归测试（无物理/模型调用）覆盖40来源准确、80仅aiddiff、私有标签不能影响aid、D1/D3多解和无物理声明、D5无history等同性与推进目标不交。focused5项通过；一次全套40项通过。独立只读后审计80条来源/实际token/parse/评分/截断/summary、40aid配对、4D5配对全部通过，句柄12308真实exit0。

`audit.py`和`archive.py`是在freeze后新增的只读派生产物程序，单列hash；没有改变冻结运行源、输入或评分。源码hash对应真实执行版本，不以事后程序hash替代。完整输入/输出/日志在`raw`数据盘软链接，薄summary/audit/receipt与源码提交git。

```bash
# 已执行；evaluate禁止覆盖现有80条原始结果。
.venv-llm/bin/python -m unittest tests.test_structure_diagnostic_v9
.venv-llm/bin/python -m unittest discover -s tests
.venv-llm/bin/python -m experiments.structure_diagnostic_v9.run freeze
CUDA_VISIBLE_DEVICES=2 .venv-llm/bin/python -m experiments.structure_diagnostic_v9.run evaluate
# 后两项只读重派生审计，不调用模型或物理环境。
.venv-llm/bin/python -m experiments.structure_diagnostic_v9.audit
.venv-llm/bin/python -m experiments.structure_diagnostic_v9.archive
```

若未来复现推理，应创建新结果目录/版本并先实时查显存，保留本轮冻结和原始结果；上述freeze/evaluate不允许原地重跑。
