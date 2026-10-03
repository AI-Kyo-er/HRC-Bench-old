# 第四轮事后接口锚定诊断

检查具体动作格式例子是否影响模型选择分布。原SYSTEM末行是：

```text
示例：选择把green独立绕行放到right，输出{"choice":"careful_green_right"}。
```

推理前冻结7版本：物品red/blue/green×目标left/right六种具体例子，以及只写 `输出格式：{"choice":"候选ID"}。` 的format_only。除了这一行，其他system逐字保持。固定原v3.2的12个full_history人工接口fixture、完整20候选与集合评分，共84次真实3B调用。不是新物理rollout，不是选择最好提示的调参流程，不重算旧formal。

| 版本 | 有效推进 | 选择示例物品 | 选择示例目标 | 选择已完成物品 | 错误目标 |
|---|---:|---:|---:|---:|---:|
| red/left | 4/12 | 3/12 | 11/12 | 6/12 | 5/12 |
| red/right | 5/12 | 4/12 | 4/12 | 5/12 | 5/12 |
| blue/left | 5/12 | 6/12 | 9/12 | 4/12 | 5/12 |
| blue/right | 4/12 | 5/12 | 5/12 | 5/12 | 6/12 |
| green/left | 4/12 | 12/12 | 12/12 | 4/12 | 6/12 |
| 原green/right | 4/12 | 12/12 | 0/12 | 4/12 | 6/12 |
| format_only | 4/12 | — | — | 6/12 | 3/12 |

原green/right和green/left都输出12次careful_green_left。改变red/blue例子会改变部分对象选择分布；去具体例子后仍有10/12选择green，有效推进仍4/12。因此具体样例是可测的接口敏感性来源，但证据不支持它是唯一根因，也不支持format_only修好了基础进度使用。已完成物品与错误目标是可重叠的错误维度，不相加作独立错误数。

原green/right fresh重跑与旧12次choice及集合评分分别12/12完全一致。全部84次JSON合法、无输出截断。原始完整messages/response、token、耗时在数据盘 `raw/evaluation/calls.json`；小摘要在 `summary.json`，逐fixture配对变化在 `paired_changes.json`。全部版本报告，不用最高5/12的版本替换旧评测。

仍使用固定Qwen2.5-3B-Instruct revision `aa8e72537993ba99e69dfaafa59ed015b17504d1`，原BF16、greedy、seed0、96 token、单样本输入，真实GPU编号由新适配器记录。GPU检查通过后启动，句柄75488 exit0。19项永久测试通过（49743），新增测试覆盖原40输入、锚定仅改一行、显存前检和实际模型/GPU元数据。

这是事后诊断；format_only改变示例语义与token长度，不能归因为单个词。改变例子后推进仍不可靠，不能将旧模型失败归因于交互结构或宣布新提示解决问题。

```bash
nvidia-smi --query-gpu=index,memory.free --format=csv
CUDA_VISIBLE_DEVICES=3 .venv-llm/bin/python -m experiments.interface_anchor_v4.run evaluate --output-dir results/interface_anchor_v4/raw/reproduce
.venv-llm/bin/python -m unittest discover -s tests -v
```

冻结文件禁止覆盖，输出目录非空则拒绝覆盖。权重和完整结果仍在数据盘，项目仅保存链接及小摘要。没有启动新的3B连续formal。
