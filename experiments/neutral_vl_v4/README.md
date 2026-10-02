# VL中性格式的限定事后对照

在原VL40输入冻结成绩16/16单动作、9/12全历史、10/12公开进度辅助之后，限定检验去除具体动作示例的跨模型中性协议。只把system末行原green/right示例换成3B锚定诊断预先固定的`输出格式：{"choice":"候选ID"}。`，其余system、40条用户messages、候选、允许集合、生成参数完全保持；不从六个具体示例中选择最好版本，不覆盖旧VL或3B成绩。该输入版本重新冻结，SHA为`15deca4241851af8f8bae0f7a5e928d8706e1412a77aa1ac03f2b03bc30affb3`。

实际40调用结果：单动作15/16、全历史6/12、辅助10/12，固定16/16+全历史12/12门槛仍未通过。JSON/候选解析错误0、截断0。本轮停止继续修改VL提示，不进入物理pilot。

| 输入视图 | 原VL | 中性格式VL | 选择改变 | 失败→通过 | 通过→失败 |
| --- | --- | --- | --- | --- | --- |
| 单动作 | 16/16 | 15/16 | 5/16 | 0 | 1 |
| 多物品全历史 | 9/12 | 6/12 | 7/12 | 0 | 3 |
| 公开进度辅助 | 10/12 | 10/12 | 6/12 | 1 | 1 |

单动作1例忽略yield要求；全历史6个失败中5次选已完成物品、2次目标错误（一例重叠）；辅助2例均目标错误。原全历史三处失败在中性版本均仍失败，并新增三处失败；因此不能以去除具体示例解释为接口修复。辅助总分相同也掩盖一好一坏的配对变化。全部配对与错误原输出见`results/neutral_vl_v4/{paired_changes,error_audit}.json`。

JSON中沿用的`reference_3b_choice`、`reference_3b_acceptable`与汇总`reference_3b_acceptable`仍来自旧具体green/right提示，只是旧3B描述参照，不能当作本次中性协议的同条件跨模型成绩。此前3B中性格式诊断只补跑12条全历史（4/12），本轮没有补跑3B中性单动作或进度辅助。本表比较的是同一VL权重两种提示的配对，不把上述旧reference当中性3B结果。

权重/API/纯文本适配器复用`local_vl_v4`，五分片/config再次核验SHA；来源revision仍未知，用全SHA识别，不称官方HF固定版本已核验，不称视觉能力或规模单因素因果。本轮GPU2加载前free30,412MiB，预估18,889MiB；greedy BF16、SDPA、seed0、batch1、96新token，无量化/卸载。运行结束GPU资源已释放。继承预检函数中`official`文字仅是原14B估计说明，本次计算实际用本地VL字节。

运行句柄2783 exit0；22项永久回归测试通过（56616 exit0），新增测试验证恢复原system后40条完整record精确等于原VL冻结。原结果及源码冻结均未修改。完整轨迹/log在数据盘，通过`results/neutral_vl_v4/raw`软链接。

```bash
.venv-llm/bin/python -m experiments.neutral_vl_v4.run freeze
CUDA_VISIBLE_DEVICES=2 .venv-llm/bin/python -m experiments.neutral_vl_v4.run evaluate
.venv-llm/bin/python -m unittest discover -s tests
```

本目录是事后接口对照，不是新泛化集，也不是选择最佳prompt流程。即使某协议过小集门槛，仍需独立新输入和包含自由物品顺序返工的安全控制验证才能推进持续物理诊断；本轮未达到这一前提。
