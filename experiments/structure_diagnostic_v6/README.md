# 当前结构原型的可辨识性诊断

本轮保留v5冻结、任务语义、21候选、真实控制与评分，仅增加独立事后诊断。结果表明当前A成功率可被统一保守策略绕过；当前B返回blue的目标可由所在盘反推。两点属于任务可辨识性缺口，不能归咎模型，也不通过人为禁令/惩罚追回预期。

## A：统一公开策略的真实六例

策略`BlindYieldThenDetour`只在第一次调用读取初始公开物品目标，无条件yield一次；随后只读实际物理区域，对剩余物品永远careful。不读取/归约exclusive/shared条款，不读取yield反馈、不依据是否撤离来选路线。永久回归测试在首次调用后删除全部history、注入相反目标/反馈仍得到相同选择，验证该历史盲性。

对原A六case（exclusive/shared/independent × seed40/41）实际运行，**6/6任务完成且全60240tick robot–partner和object–partner接触记录均0**。真实检查点与对应旧reference保存后的JSON精确匹配。总18决策、12策略抓放、0物理失败，公共prefix另有6次真实抓放；旧reference为14决策、相同抓放数、59280tick。全部成本来自原始状态/tick和逐case结果，没有预置结论。

| 条件（每seed相同） | reference决策→统一策略 | checkpoint后reference tick→统一策略 | 首次yield实际tick | 实际差异 |
| --- | --- | --- | --- | --- |
| exclusive | 3→3 | 6300→6780 | 420 | 伙伴实际释放；统一策略仍careful而reference用direct，额外480tick即2秒 |
| shared | 2→3 | 6360→6360 | 0 | yield合法无害，全部物理状态不变，仅多1决策 |
| independent | 2→3 | 6360→6360 | 0 | yield合法无害，全部物理状态不变，仅多1决策 |

因此A末态成功率不能单独证明历史赋义。统一策略虽然无需辨别占位约定，也能全完成；差别是实际冗余决策与路线成本，而exclusive路线差不是纯历史效应。A_exclusive的request_clear不能替代yield，只返回先yield的反馈、计请求/决策而不释放；此分支属于代码事实，本诊断没有运行请求物理分支。没有把shared/independent的合理保守yield改成非法。

## B：已有快照的只读目标反推

旧四条B的temporary_blue_target始终是outer_blue_target反面。在每条真实finish后快照中读取blue实际所在盘，取另一盘，4/4都匹配真实已接受blue返回目标及合法blue抓放集合（place/careful）。审计的历史归约只用于核对真值，不是反推规则输入；没有重跑B物理或调用模型。

此结论只说明**blue返回目标无需外层历史即可反推**，不证明整个episode完全无需记忆。scope终止、green保留等其他环节仍需独立评价。数据与快照SHA在`results/structure_diagnostic_v6/B_flip_readonly_audit.json`。A/B原型先前10/10规则可行性结论仍成立，但不能提升为历史依赖/组合能力测量的可辨识性证明。

## 冻结、失败与复现

初版`run.py`/`cases/freeze.json` SHA `fc166b357dc086aa8f4a965557589f52f5550c66e7b254c78f0ea3a7a7fe3945`的首例物理成功且两类接触0，但比较器将运行内接触位置tuple与旧JSON list直接比较，导致52816 exit1；两份保存JSON检查点实际精确相同。此为比较器错误，不是物理失败；原freeze、runner、日志、首例轨迹和`comparator_failure_v0.json`全部保留。

独立v6.1 `run_v1.py`/`cases/freeze_v1.json` SHA `fe51b64d029c4ad81ab681b49a12e5452886f32fdce29e4098ae1f6eb8ea9a4c`仅把检查点比较规范化为JSON，改版本标记和输出目录；策略/任务/菜单/评分/物理不变。72189实际完成六例exit0，结果只使用完整新六例，没有混入中止版本的首例。25测试通过（25272 exit0）。规范messages、全tick和所有决策在数据盘，通过`results/structure_diagnostic_v6/raw`软链接访问。

```bash
.venv-llm/bin/python -m experiments.structure_diagnostic_v6.run_v1 freeze
.venv-llm/bin/python -m experiments.structure_diagnostic_v6.run_v1 run
```

入口拒绝覆盖。对照引用原v5 source/freeze哈希，未改变已接受约定、动作集合或成功判据。本轮不增加提示变体、不运行v5神经，不以旧14B公开进度辅助12/12放宽全历史门槛。
