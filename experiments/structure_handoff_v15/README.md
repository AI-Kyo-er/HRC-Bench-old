# v15：伙伴交还与机器人主动终止的离线接口对照

本轮检验公开的终止主体与防重复提醒是否改变参考轨迹检查点上的下一动作选择，不评价模型闭环任务成功。两模型原工程门槛均未通过，故这些结果不表示已掌握局部操作或组合推理。伙伴仍是脚本控制的几何检查代理，不是自然人。

## 两阶段冻结与真实物理

保留v11全部16条件：seed60/61 × 更新时点before_child/during_child × accepted/rejected × 初始blue left/right。相反方向提议只有接受才更新外层ledger。真实控制顺序是red→left，进入blue局部指导，blue→neutral，伙伴实际进入检查，yield实际撤离，green→right（child仍活动），伙伴公开交还，再将blue抓放到最新有效外层目标。during更新仍发生在yield检查通过后、green之前；不移到交还后。复用原v7/v11 Panda摩擦抓放控制器、几何和22候选，没有瞬移、attachment或直接赋物理成功。

伙伴交还合法条件只有局部指导活动、实际检查通过、伙伴已撤离；green完成不是前提。本次在green后交还是为了与旧D5检查点机械匹配。交还公开事件是“局部检查已结束，现在交还blue，按当前有效外层约定继续。”，不含左右或目标字段。它零物理tick、零机器人决策，结束child并恢复最新outer；物体、red/green目标与实际进度保持。机器人在活动且检查通过时仍可finish，已经终止后finish拒绝；yield/request合法no-op仍保留。

新system和accepted_child公开文字同步允许伙伴交还或机器人finish，避免前后规则冲突。旧local_check_passed只写“可终止指导”，未限定主体，原样保留。全部逐字差异和公开history样例见[protocol_review](../../results/structure_handoff_v15/protocol_review.md)，旧锚点输入不作替换。

物理freeze SHA：`563625ee6cacac965aa31fc780360f8d48d9519472425cdc1a09e81f35af5ae0`。新16实际任务完成16/16，64次摩擦抓放（含red前缀），204480 tick；robot–partner和object–partner接触记录均0。每例删除旧零tick finish后，交还前后完整物理state、共同前缀和整条解压规范轨迹与对应旧v11精确一致。green在child内完成且交还后保留，blue真实位于neutral，再真实搬到outer。此处仅验证已覆盖几何的执行可行性。

**比较器errata：**冻结物理程序39099真实退出1，原summary success16但passed0，日志/source/freeze均保留。原因是两个全state比较字段直接比较live接触tuple与旧JSON list，错误判不等。未改冻结源或重跑；独立reference_audit仅将所有tuple/list规范为list，保留所有字段、接触和浮点数，无容差。16例全字段及全tick审计通过，19522真实退出0；原passed0不会被事后覆写。永久回归覆盖实际nested contact schema的容器表示差异及1e-9真实数值差异仍不等。后续使用此明确规范比较，而不复制直接==。

实际代表帧（不额外补跑）：`results/structure_handoff_v15/raw/reference/B_handoff_before_child_accepted_left_60/frames/00003.png`（green已入right、blue仍neutral）、`00004.png`（交还，物理不变）、`00005.png`（blue入有效right）。during对应目录也有同样6帧。

## 256个离线调用

每模型128条，4arm各32（16条件×normal/reverse菜单）：

| arm | 输入来源与干预 |
| --- | --- |
| old_anchor | 原v13全部D5 action32，messages逐字；14B对v13输出、8B对v14输出核对 |
| manual_reminder | 原user/候选/remaining8逐字，仅旧system原finish规则行末加“已终止后重复finish_guidance无效。” |
| handoff_budget9 | 本轮真实交还后observation，remaining9；reverse仅反转22 candidates列表 |
| handoff_counterfactual8 | 对上一arm仅把remaining_decisions的9改8；非真实observation |

旧D5机器人finish消耗一次决策，remaining8、history15；伙伴交还不消耗机器人决策，新实际remaining9、history13。新/旧语义文字、事件数量、长度、终止主体和预算均不同，不能称严格单因素主体对照。预算8干预明确标counterfactual，绝不篡改真实轨迹。一般防重复提醒对照在任何新模型输出前将原192预算预先修订为256，保留原计划及修订原因；没有按结果挑提示。

模型freeze SHA：`d4a41e349764ab88aa3845820cddfbdc0075e3fd830a155e9a8563066add7e66`。greedy一次、seed0、BF16、SDPA、batch1、max_new_tokens96；全部本地纯文本，无state query、无下载权重、无外部API、无模型动作执行。14B用旧4.49环境，8B用隔离4.57.1环境。官方权重/环境核验复用v4/v14回执，固定revision分别`cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8`、`0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`。两模型最长2099 tokens，单卡估需31244/19795 MiB，每次启动前GPU2 free48494 MiB。未量化、offload或多卡。

## 实际结果

每格分母32；推进是未执行候选的协议评分，绝不是整段任务成功率。

| 模型/arm | 推进 | 重复finish | 错blue目标 | 已完成物品 |
| --- | ---: | ---: | ---: | ---: |
| 14B old | 4 | 24 | 4 | 0 |
| 14B reminder | 8 | 20 | 4 | 0 |
| 14B handoff9 | 6 | 24 | 2 | 0 |
| 14B handoff8 | 6 | 24 | 2 | 0 |
| 8B old | 5 | 13 | 5 | 9 |
| 8B reminder | 5 | 13 | 4 | 10 |
| 8B handoff9 | 10 | 18 | 4 | 0 |
| 8B handoff8 | 10 | 20 | 2 | 0 |

64个旧锚点的response、choice、score均32/32逐字复现各模型旧输出。14B old→reminder有4错转对、0对转错；old→handoff9与8各2错转对、0对转错。8B old→reminder有1错转对、1对转错，总计数相同但逐例不同；old→handoff9与8各5错转对、0对转错。所有逐例四格、原输出一致性、错误分类和timing/acceptance/目标/menu分项均保留，未过滤错误。

14B handoff9/8全部32个response/choice/score相同。8B仅30/32相同；两处变化都是during_child/rejected/initial_left/normal、seed60与61：预算9选place_blue_right（未接受的right提议，wrong_target），预算8选finish_guidance（重复终止）。两者推进都错误。因此同为10/32不表示预算字段无影响。新交还后的8B重复finish分别为handoff9的18/32与handoff8的20/32；14B两者均24/32，不能称交还已消除该失败。

两模型256输出无parse错误、截断或未授权help；全部候选仍是22。实际峰值allocated显存14B为30,377,657,344 bytes，8B为18,095,191,552 bytes。最长2099 tokens，旧arm2089–2090、提醒2098–2099、两个交还arm2092–2093；对应字符4330/4354/4290。它们不等长度，不能把结果变化仅归于交还主体。

## 测量与边界

评分只从公开历史ledger和实际区域归约。每例允许有效blue目标的place/careful两种推进意图；reference_action命中另报。yield/request为合法no-op，重复finish、已完成物品、wrong target、未授权assisted、parse及截断各自保留；未执行动作不标物理成功。

结果及逐例四arm配对见[model_summary](../../results/structure_handoff_v15/model_summary.json)，原messages/response和所有非推进输出见[model_failure_audit](../../results/structure_handoff_v15/model_failure_audit.json)。同seed/同模板不是独立结构样本；不作显著性推断。不将固定检查点选择率叫episode success。一般提醒、预算、文本长度/显著性和公开协议变化都有替代解释，也不能将一次状态/动作输出当内部知识机制证据。

## 验证与复现

14项focused通过：8项FactsWorld协议替身（含green前合法交还、未检查/未撤离/重复拒绝、保留进度）、1项实际contact schema容器比较回归、5项离线模型source/输入/评分回归。它们不是真实物理错误恢复。全套87项一次通过。物理证据另来自16条实际rollout和204480 tick审计。原失败日志、冻结源、独立派生审计sha、输入来源sha、真实PID/句柄退出、显存峰值/清理均见execution_receipt。

```bash
.venv-llm/bin/python -m unittest tests.test_structure_handoff_v15 tests.test_handoff_model_v15
.venv-llm/bin/python -m unittest discover -s tests
.venv-llm/bin/python -m experiments.structure_handoff_v15.reference_audit
.venv-llm/bin/python -m experiments.structure_handoff_v15.model_audit
```

原reference_run/evaluate禁止覆盖已开始的冻结及输出；这些命令仅用于只读复核已有结果。全部raw通过项目软链存放于`/data1/sieniwgroup/sieniw/HRC-Bench/results/structure_handoff_v15`，不存在配对manifest；按seed/timing/acceptance/initial/menu确定性匹配。
