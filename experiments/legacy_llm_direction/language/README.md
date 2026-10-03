# 本地语言模型决策诊断 v2.1

## 执行前冻结

本轮是自然语言共同活动的连续关键决策切片，不是物理HRC评测。三领域（装箱、餐桌、工具准备）是三个词汇场景，共用一个逻辑模板，不代表三个独立任务机制。每episode保留三物品的已接受约定、尚未接受建议和完成进度；关键决策按照任务顺序外部指定。伙伴只有在模型实际request或yield之后响应。

开发集12个实例覆盖retain/revoke/nested/reentry，正式集60个实例覆盖上述结构与nested_reentry组合留出。正式集目标反事实变体与伙伴accept/refuse独立交叉；初稿v2.0曾绑定这两个轴，尚未推理前已修正为v2.1并重新冻结。冻结文件见cases/freeze.json；Git冻结提交先于第一次开发集模型调用。开发集无nested_reentry。这里的留出只限于本项目开发提示流程，不表示模型预训练未见这些语义。

每episode分别执行full_history与oracle_summary，两者维护各自真实动作引起的轨迹。摘要由参考规则从可见事件生成，维护生效约定、待接受建议、已完成进度、伙伴可用性和公开请求响应；它不是模型免费可得的信息，是状态维护的oracle干预。模型观察接口只接受消息字符串，不接受case、条件标签、隐藏伙伴响应或标准答案。参考规则根据公开事件归约，不读取结构标签或未来响应。目标动作通过允许动作集合判分，solo与获授权的assisted均可有效，不限定唯一JSON字符串排序。

首个开发结果出现后不根据正式结果改提示、生成器或解析器。本轮不进行模型排名、显著性检验、真人成本推断或社会特异性推断。小模型用于流程校准；成功和失败都如实记录。结构差异与输入token数/决策机会一起记录，未严格匹配长度或信息密度时不得归因纯结构效应。若模型全选solo，则支撑响应机制虽然可运行，本轮不构成实际闭环能力证据。

## 本地模型与存储

模型：公开[Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)，3.09B BF16，固定revision `aa8e72537993ba99e69dfaafa59ed015b17504d1`。按官方模型卡使用transformers chat template；推理GPU3，greedy，seed0，max_new_tokens96。包版本锁定在requirements.txt，实际依赖完整记录到结果。

大型文件全部放数据盘，项目链接使用：

- `.venv-llm` → `/data1/sieniwgroup/sieniw/HRC-Bench/venv-llm`
- `models/Qwen2.5-3B-Instruct` → `/data1/sieniwgroup/sieniw/HRC-Bench/models/Qwen2.5-3B-Instruct`
- UV/HF新下载缓存 → `/data1/sieniwgroup/sieniw/HRC-Bench/cache/`
- `results/language_v2/dev`与`formal` → 数据盘同名结果目录，保存所有prompt/response/解析错误与连续事件。
- 首轮`results/symbolic_v1/episodes.csv`亦已移数据盘并链接，SHA256不变。

```bash
python -m unittest discover -s tests -v
CUDA_VISIBLE_DEVICES=3 .venv-llm/bin/python -m experiments.language.run --split dev --output-dir results/language_v2/dev
CUDA_VISIBLE_DEVICES=3 .venv-llm/bin/python -m experiments.language.run --split formal --output-dir results/language_v2/formal
```

运行前重新检查nvidia-smi；预计3B BF16加短上下文KV与激活<12GB，实际峰值随结果记录。权重首次下载通过用户clashon后运行download模块，token=False，不读取或发送认证凭据。此处仅下载公开文件，没有上传私有数据或调用他人推理服务。

## 覆盖审查

环境外部指定下一物品，并由参考事件归约器维护完成记录与阻止重做。因此结果只检验指定步骤下的有效约定/分工响应，不能声称检验机器人自主维护进度、选择未完成子任务或恢复行动规划。完整事件轨迹保留进度，不等于模型实际使用了这些信息。

nested目前是第二物品前注入局部纠正的近似，没有子任务栈、暂停点或恢复执行；reentry是在伙伴离开/返回事件后接受指定物品分工，没有开放式伙伴进度推断。本轮没有并发物理占位、安全运动、伙伴主动反提议或真正具身行动。五个结构标签不能当作已覆盖原idea的六种交互融合结构，测试通过也不证明科学覆盖完整。

后续优先仿真闭环：把三物品/两容器活动接到物理场景与行动执行器，使观察由仿真当前状态产生，机器人实际动作与伙伴状态改变后续可行行动、进度和交互。当前自然语言观察接口可复用，外部指定步骤与文本判分器需替换。仿真选择应在本轮结果后依据正式文档、许可证和实际环境可运行性核验；本轮不额外安装仿真器，不以文本轨迹代替仿真证据。

本轮retain亦包含连续历史与未接受建议扰动，不能当作独立局部能力基线。本轮没有真实语言isolated或长度匹配concat对照，不能据此验证“局部能力强而组合能力弱”。轨迹分析按首物品未接受proposal、第二物品更新、第三物品重返阶段分解，避免共享首步错误被叙述成组合结构特有困难。

## 实测记录与接口审查（2026-10-02）

正式集在两view各60个连续实例上实际推理，合计432调用、360指定物品步骤。所有调用JSON解析成功，没有96-token截断。完整历史平均输入494.70 tokens，摘要368.69 tokens；二者长度、表达和诱发轨迹未匹配。

| 观察 | 完整实例 | 完成指定步骤 | 实际调用 | 合法并实际触发的请求 | 无效动作 |
|---|---:|---:|---:|---:|---:|
| 完整历史 | 0/60 | 38/180 | 216 | 54 | 124 |
| Oracle摘要 | 3/60 | 38/180 | 216 | 54 | 124 |

相同的完成步骤总数不能说明摘要改善了状态保持；完整实例差异来自成功步骤的分布。配对完整实例为57组均未完成、3组仅摘要完成。没有显著性检验。开发集完整历史10/36步骤、摘要6/36，完整实例均0/12；正式并非根据这些低分调整后的题库。

阶段分解（每view每阶段60个指定步骤）：

| 阶段 | 完整历史完成 | 摘要完成 | 每view调用数 |
|---|---:|---:|---:|
| 首物品未接受proposal扰动 | 0/60 | 10/60 | 60 |
| 第二物品更新与支撑 | 13/60 | 14/60 | 96 |
| 第三物品保留或返回分工 | 25/60 | 14/60 | 60 |

完整历史的全部60个实例已经在共享首步失败，因此完整实例0不能用来讲组合结构特有困难。第二阶段更多调用来自request后响应，不能用calls作物品任务成功率分母。两view共108次合法且实际触发伙伴的request：接受型伙伴36次、拒绝型72次。原协议允许拒绝后再次请求，因此拒绝型的部分调用是合法重复request，消耗2次预算而没有完成物品；有效动作与完成动作须分开。

248个无效动作按可见输出分类：无需支撑仍request 111次、伙伴暂离仍request 48次、当前应由伙伴负责而输出其他动作48次、目的地错误41次。错误类别不是隐藏记忆机制证据，也不是物理安全风险。当前协议第一次无效动作即结束该物品步骤，无恢复机会；非必要求助在真实合作中可能应计通信成本而允许恢复，且模型可能把request当作澄清。由此造成的低完成可能含动作接口过严的测量伪差。冻结原始分数没有修改，也没有对未发生的恢复轨迹编造修正成功率。

事后新增12个独立接口控制（同模型、同SYSTEM、直接给有效状态，无pending/修正/组合）实际结果：

| 控制 | 允许集合内动作 | 立即完成当前物品 |
|---|---:|---:|
| solo | 0/3 | 0/3 |
| 已接受支撑assisted | 3/3 | 3/3 |
| yield | 0/3 | 0/3 |
| 已拒绝支撑后solo | 3/3 | 0/3 |

solo与yield控制仍全部输出request；拒绝后控制也输出request，原协议允许再次请求，故动作有效但不完成。这是12次单调用接口诊断，不是12个完整连续episode，也不是结构留出结果。当前模型/接口连基础协议都未稳定使用，不能将正式低分归因为交互组合或有效状态遗忘。摘要同样有错是关键负面证据。下一轮应先校准明确的公开动作候选、request子类型与可恢复求助，再进入真实物理仿真；不在本轮追求分差或扩题库。

## 运行证据与复现边界

下载session18507正常退出；开发44716、正式11216、事后校准62118均exit0。实际BF16分配峰值正式为6,364,283,904字节；GPU3整体使用观察约6.7GB。8个永久测试最终通过。模型与原始文件SHA256、源版本、case hash、提示hash、调用token数、耗时、截断标记分别保存；未将本轮神经模型输出独立全量重跑，不能声称已验证神经推理完全确定复现。

`results/language_v2/` 仓库内保存小摘要、分析、校验值及代表性原始输入输出。dev/formal/calibration完整调用与连续事件在数据盘同名链接目录。模型权重与环境锁亦保存校验和版本；事后校准命令：

```bash
CUDA_VISIBLE_DEVICES=3 .venv-llm/bin/python -m experiments.language.calibrate
python -m experiments.language.analyze --root results/language_v2/formal --output results/language_v2/formal_analysis.json
```

SDPA启动时出现sliding-window警告，权重配置实际`use_sliding_window=false`且本轮输入远短于窗口；警告记录于execution_receipt。模型generation_config中的temperature/top_p/top_k在`do_sample=false`下不参与采样，实际greedy配置未修改。
