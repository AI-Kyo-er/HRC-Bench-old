# 第十轮：公开作用域、目标和进度字段的离线消融

本轮从v9全部D4/D5各八个真实检查点构造十视图，共160次单决策调用。D4作为仍需finish的正对照，D5作为已经finish、blue仍neutral的恢复检查点。没有按模型是否失败筛选检查点，没有新物理、下载、提示调参或后续rollout。模型输出从未送回环境；协议推进率不是整段任务成功率，旧14B基础gate仍为false。

160/160已完成，模型句柄9495真实exit0。D4十arm均8/8；D5各arm如下。所有未推进输出均再次finish，没有错误blue方向、合法no-op、解析失败或截断。

|arm|D5协议推进/blue尝试且方向正确|重复finish|左右pair two/one/none-correct|
|---|---:|---:|---|
|raw_full|2/8|6|0/2/2|
|S|4/8|4|1/2/1|
|G|5/8|3|2/1/1|
|P|6/8|2|2/2/0|
|SG|5/8|3|2/1/1|
|SP|6/8|2|2/2/0|
|GP|7/8|1|3/1/0|
|SGP|7/8|1|3/1/0|
|source_only|4/8|4|1/2/1|
|v9_full_aid|8/8|0|4/0/0|

D4全部选择finish；D5推进全部选择place_blue_left/right，未选择careful/assisted等替代。总26次重复finish完整原输入/输出保存。两个v9重复锚点各16/16的messages、原响应、选择及推进判断一致，没有新增重复调用。

S与source_only不仅同为4/8，它们在D4和D5各8个检查点的原响应、动作和score逐例全部相同；GP与SGP在D4和D5也逐例全部相同，完整表见audit.json。不能据此将内部机制判为相同。source_only已从2/8提升到4/8，单scope也4/8；P6/8、G5/8说明完整辅助改善不能独归scope。完整aid8/8与SGP7/8之差不能归因某个遗漏字段，因为多个字段与长度同时变化。

D5八cell描述性主差为S +6.25、G +18.75、P +31.25个百分点；两因素差中差均−12.5个百分点、三因素差+25个百分点。D4各差为0。它们只是固定字段呈现的比例对比，不是独立内部记忆机制贡献或统计显著结论。

## 冻结输入与十视图

原16个messages取自`results/structure_diagnostic_v9/raw/frozen_inputs.json`中所有stage4/5的full视图；同时取同检查点的v9aid作为原样重复锚点。保留原system、完整字典历史、22候选顺序、实际位姿/区域、决策预算。case/seed/outerblue/参考动作只作评分元数据，不新增到模型输入。历史来源为脚本预置已接受背景及真实规则轨迹反馈，不是模型自行协商或执行。

每点固定顺序`raw_full,S,G,P,SG,SP,GP,SGP,source_only,v9_full_aid`，仅调用一次。三因素从同一个v9公开归约结果取值，字段顺序按原v9顺序过滤：

|因素|加入的固定字段|
|---|---|
|S|scope：active、ended、local_check_passed|
|G|current_goals_from_public_history|
|P|done_under_current_goals、remaining_items|

七个非空子集仅在原user JSON尾部追加`external_public_scope_aid`，保留所选字段原值，并使用与v9逐字相同的source说明。它们不加obligations/help/重复physical placements，也不加动作答案。`source_only`只追加该source说明，不含因素字段。`raw_full`与v9原full逐字相同；`v9_full_aid`与v9原aid逐字相同，后者仍含完整scope/goal/progress/placements/obligations/help。

P依公开目标计算完成情况，因此不是与G信息论独立的因素；这里能控制的是字段呈现。八析因cell以raw为000，但非空cell还增加source包装和token，所以不是等长度的纯三因素心理机制实验。source_only只检查包装/来源提示的描述性影响，不能消除所有长度混淆。

本轮freeze SHA256为`893578e753030886744db0d5184b424f3395ae5a9e7b0dc66f1a5ee89289c46a`。`cases/freeze.json`保存原v7/v9来源hash、冻结运行和依赖源码hash、权重receipt/model spec hash、160输入SHA、各条token数及参数。禁止原地覆盖已开始的结果。

## 评分与解释

D4推进集合只有finish_guidance；D5为place/careful_blue_公开外层目标。yield/request_clear可合法但无推进，单列no-op；解析失败、非法候选、重复finish、错误目标、已完成物品、未接受help分别分类。另单列blue抓放是否尝试和方向正确性：没有blue尝试的重复finish，其方向为null，不计作忘目标或方向错误；assisted_blue即使方向正确，也可能因帮助未接受而非法。

每个点是独立参考状态。v9 D3允许合法提前finish，不意味着本轮D4已结束：D4仍采用原规则轨迹的活动child正对照，D5采用原规则轨迹结束child后的状态。这里不是模型自生状态序列。所有选择均声明physical_execution=false、physical_success=null，替代动作没有实际执行成功证据。

`summary.json`报告阶段×arm×目标×菜单，D5同seed/menu左右pair的two/one/none正确，以及八cell主差、两因素差中差与三因素差。后者仅是8个检查点上的描述性比例差，不对重复seed做显著性检验。原v9两个锚点的逐messages/输出重复一致性由独立`audit.json`报告，不靠额外重复调用保证一致。

## 模型、长度与资源

既有Qwen/Qwen2.5-14B-Instruct，官方revision `cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8`；八LFS分片SHA验证沿用并绑定原receipt，配置与tokenizer资产重新比对旧已核验hash。torch2.6.0+cu124、transformers4.49.0，greedy seed0、BF16/SDPA、batch1、max_new_tokens96。单卡运行，无量化/offload/多卡/外部模型API。

|arm|实际冻结输入token范围（D4/D5、两seed）|
|---|---:|
|raw_full|1868–1950|
|S|1934–2016|
|G|1939–2021|
|P|1943–2021|
|SG|1959–2041|
|SP|1963–2041|
|GP|1968–2046|
|SGP|1988–2066|
|source_only|1914–1996|
|v9_full_aid|2040–2118|

最大2118tokens，含96输出KV估415.125MiB；BF16权重字节+3GiB预算要求free31244MiB。实际启动实时nvidia-smi选择GPU2，free32278MiB；其他任务不受操作。运行和退出证据、峰值allocated及资产hash见execution_receipt。

## 验证与保存

冻结前新增五项永久协议/输入测试，无模型或物理调用：160来自全部16源检查点、两锚点逐字一致、十视图仅所选字段差异、公开归约忽略私有元数据、D4正对照/D5多解与no-op/方向判定。focused5/5；一次全套45/45。之后为派生比较器修复新增一项永久回归，focused6/6通过，未声称最终全套46已运行。原始日志存raw，不将这些单测当物理恢复验收。

后审计重新构造160来源，验证冻结运行源、原字段/aid、实际token、parse、评分、截断和summary，并保存全部非推进原messages/输出（含合法no-op）于raw/nonprogress_calls.json。`audit.py`和`receipt.py`是冻结后新增只读派生程序，单列hash，不改变运行源码/评分/冻结或旧v7/v9产物。完整输入/输出/日志在数据盘raw软链，薄结果/receipt和源码提交git。

首个后审计exit1仅因analysis的解释简述与runner按freeze正常覆盖的interpretation不同，实际数值/160来源/评分均一致。原失败报告、traceback与该审计源码完整保留为raw/audit_attempt001.{json,log,py}。修正只读比较器，使派生数值与analysis比、解释说明与freeze比；冻结运行版本和模型调用未变。最后同步后审计真实exit0、all_passed=true，并增加逐例arm一致性表。模型PID6941退出且不在GPU进程，自有资源释放，无活句柄。

```bash
.venv-llm/bin/python -m unittest tests.test_structure_ablation_v10
.venv-llm/bin/python -m unittest discover -s tests
.venv-llm/bin/python -m experiments.structure_ablation_v10.run freeze
CUDA_VISIBLE_DEVICES=2 .venv-llm/bin/python -m experiments.structure_ablation_v10.run evaluate
.venv-llm/bin/python -m experiments.structure_ablation_v10.audit
```

freeze/evaluate禁止覆盖现有结果。将来复现应独立新版本/目录，并重新检查显存；本轮只完成上述160调用，无追分流程。
