# 第十三轮：公开状态报告与独立动作重放

本轮完成128次本地14B调用：v12全部64条full_history观察各做一次原样action_replay及一次独立state_readout。64个动作的response、choice、score全部复现v12；状态报告外层目标61/64正确，但指导活动性与当前目标分别32/64正确，联合状态0/64。状态报告任务尚未校准成功，不能据单字段正确断言模型掌握完整状态或已经理解HRI结构。

## 固定输入与任务差异

来源是v12的16条件×D4/D5×normal/reverse，共64条full_history，包含全部条件。action messages逐字原样；state user观察逐字原样，候选、原始history、预算、物理字段均保留。state只改system以下三处，其他公开协议语义（接受/拒绝、child期间neutral、finish恢复最新有效outer等）逐字保留：

| 原指令 | 状态报告指令 |
|---|---|
| `你控制持续桌面任务。只输出{"choice":"候选ID"}。` | `你读取持续桌面任务的公开观察。只输出一个严格JSON对象，按outer_blue_destination、guidance_active、current_blue_destination的键顺序。` |
| `依据公开原始历史和真实区域继续任务，自主选择尚未满足约定的物品。` | `依据公开原始历史和真实区域报告最新有效外层blue投递目标、局部指导是否仍活动、当前blue执行目标。不输出动作或分析。` |
| `输出格式：{"choice":"候选ID"}。` | `输出字段与类型：outer_blue_destination是left或right字符串；guidance_active是JSON布尔值true或false；current_blue_destination是left、right或neutral字符串。不得加字段、动作、分析或Markdown。` |

没有具体答案JSON示例，只有字段类型与枚举说明。正确状态仅由v11公开history的dual-ledger归约，不读取case目标、未来、参考action或旧模型答案；正确值仅留在评分元数据。D4指导仍活动，因此当前blue目标neutral；D5指导已结束，当前目标等于最新有效outer目标。

action/state是彼此独立的两次query，state答案未送给action。任务指令改变后独立报告的准确率不等价于动作query的内在知识，也不是状态已提供给动作策略后的实验。原v11是规则参考轨迹，离线检查点不是模型自生轨迹；这里没有执行模型动作、闭环成功率或新的能力门槛。旧14B40门槛仍未通过。

## 结果

状态报告主表采用JSON语义评分。固定字段順序仅单列写作合规；64/64均满足键顺序，因此与冻结的原严格键序评分完全一致。重复、缺失、多余key、错枚举、bool字符串/整数、Markdown、尾随文本、NaN仍严格拒绝，不修复、不重试。本轮128条均无parse错误或截断。

| 检查点 | 动作协议推进 | 外层blue字段正确 | 指导活动字段正确 | 当前blue字段正确 | 联合状态正确 |
|---|---:|---:|---:|---:|---:|
| D4（child active） | 28/32 | 32/32 | 0/32 | 32/32 | 0/32 |
| D5（finish之后） | 4/32 | 29/32 | 32/32 | 0/32 | 0/32 |
| 全部 | 32/64 | 61/64 | 32/64 | 32/64 | 0/64 |

所有state输出均为`guidance_active=false`、`current_blue_destination=neutral`。outer输出right35次、left29次；三次outer错误均为before_child、accepted、initial_blue=right、effective_blue=left的D5：seed60正常/反序及seed61反序。逐条原输出、真值与对应action保存在`state_field_audit.json`。

| 分组（每组32对） | 动作推进 | 外层字段正确 | 活动字段正确 | 当前字段正确 | 联合正确 |
|---|---:|---:|---:|---:|---:|
| before_child | 18 | 29 | 16 | 16 | 0 |
| during_child | 14 | 32 | 16 | 16 | 0 |
| accepted | 17 | 29 | 16 | 16 | 0 |
| rejected | 15 | 32 | 16 | 16 | 0 |
| normal | 16 | 31 | 16 | 16 | 0 |
| reverse | 16 | 30 | 16 | 16 | 0 |
| initial left | 15 | 32 | 16 | 16 | 0 |
| initial right | 17 | 29 | 16 | 16 | 0 |

完整stage×timing×acceptance×initialblue×menu分组在`semantic_state_summary.json`。两seed/同模板/菜单变体不构成独立结构样本，不作显著性推断。

64配对中联合状态对且动作对0、联合状态对而动作错0、联合状态错而动作对32、二者均错32。另按outer单字段配对：outer对且动作对31、outer对而动作错30、outer错而动作对1、二者均错2。后者不能改称完整状态已知。

动作输出52次finish、11次blue-left、1次blue-right。D4四次错误blue放置违反活动child的neutral目标，不能因符合outer就计作当前方向正确。D5含24次重复finish（未推进，非目标记忆错误）、4次错误方向、4次正确方向。合法no-op、帮助授权错误均0。协议推进与参考action命中本轮都为32/64，仍独立记分；没有未执行动作的物理成功声明。

旧v12八个D5方向错误由full4与aid4组成。本轮只重放full，不重跑aid；`old_error_observation_links.json`保留八个旧query与对应full观察的新action/state关联，明确旧aid错误不当作本轮action错误。主要评分始终覆盖全部64观察，不挑旧失败。

## 冻结、运行与审计

- freeze SHA256：`04317bc74eb0b5dae36b089de627408fc6df3d9624d093d4679c5f69cfa418af`。
- 128输入SHA256：`e3a75ea3a79cea0bdea51a8c75755c9101f5c8057de092ceb5328438c0ea1420`。
- 官方本地Qwen2.5-14B-Instruct，revision `cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8`；复用8分片官方LFS SHA核验receipt，重新核对config/tokenizer SHA。本轮无下载。
- torch2.6.0+cu124、transformers4.49.0；BF16、SDPA、单卡、batch1、greedy、seed0、max_new_tokens96，无量化/offload。
- 最大输入2160 tokens；KV上界423MiB，权重+3GiB估需31244MiB。实时前检GPU2空闲48494MiB，实测峰值allocated约28987MiB。
- model句柄79320、PID30711，UTC 2026-10-02 19:29:23开始、19:31:47完成；`write_stdin`确认exit0。进程和自有GPU占用已释放，无活句柄。
- 冻结后收到“键序不是状态语义”的澄清，保留原freeze、parser、calls和summary不改；独立`semantic.py`派生语义评分，`audit.py`/`receipt.py`独立SHA归档。实际评分差异0，不追加调用。

审计核对128来源/原输入token/原解析/原score/两个summary、公开真值、冻结运行源未变，以及64action anchors的messages/response/choice/score精确一致。`raw/incorrect_calls.json`保存全部96错误query的原messages和outputs（32动作+64状态）；`failure_audit.json`索引，`state_field_audit.json`记录常量与交叉表。原始数据在数据盘，`results/state_readout_v13/raw`为软链，约5.5MB；执行回执记录准确字节与所有资源/源文件SHA。

## 验证与复用命令

冻结前永久focused5项通过，随后全套62项通过；键序澄清后补语义parser回归并运行focused6项通过。未声称最终全套63项运行，未再次重复全套。测试验证输入/公开归约/评分与严格schema，属于单元协议验证，不是模型或物理成功证据。

```bash
.venv-llm/bin/python -m unittest tests.test_state_readout_v13
.venv-llm/bin/python -m unittest discover -s tests
.venv-llm/bin/python -m experiments.state_readout_v13.run freeze
CUDA_VISIBLE_DEVICES=2 .venv-llm/bin/python -m experiments.state_readout_v13.run evaluate
.venv-llm/bin/python -m experiments.state_readout_v13.semantic
.venv-llm/bin/python -m experiments.state_readout_v13.audit
.venv-llm/bin/python -m experiments.state_readout_v13.receipt
```

freeze/evaluate拒绝覆盖既有冻结或已开始输出。GPU号属于本次实查结果，未来执行需重新检查，不直接假设GPU2空闲。本轮到结果与归档为止，不追加改词试验。
