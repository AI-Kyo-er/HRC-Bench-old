# 第十二轮：v11全部条件的14B离线检查点诊断

128/128真实模型调用已完成，句柄5426已续接确认exit0。D4 full协议推进28/32、公开辅助30/32；D5分别4/32、21/32。既有作用域终止后重复finish，也有活动child时提前选择外层投递和跟随已拒绝提议的方向错误；不能直接沿用旧v9错误归因。

这是已有规则轨迹条件下的独立单决策，不是模型闭环episode。模型动作从未执行，新物理动作0、新下载0。旧v7–v11及模型实验冻结保持原样，14B旧基础gate仍false；本轮不设新门槛、不追分、不追加调用，不声称组合泛化。

## 128输入和公开辅助

取v11全部16条真实规则轨迹的D4/D5，各点normal/reverse菜单 × full_history/public_scope_aid，合计32来源检查点、128输入。条件为两seed × 更新在child前/期间 × 接受/拒绝 × 初始blue left/right，全保留，不仅选择旧snapshot策略失败组。

32个normal full逐字使用v11规范messages（同一个新system）；reverse只替换原user JSON中的22项candidates列表片段为完整逆序，其余原字节/system不变。它是离线菜单变体，没有新物理轨迹。candidate集合固定包含错误或不可执行动作，不按答案筛选。case/seed/timing/acceptance/initial/effective目标只在评分元数据，目标与回应/timing从公开历史归约，不额外传入模型。

aid在各自full user尾部只追加external_public_scope_aid，原system/history/候选/预算/物理字段保持原样。独立辅助复用v11公开dual-ledger与physical_placements，给出current_goals_from_public_history、scope(active/ended/local_check_passed)、done_under_current_goals、remaining_items、obligations、accepted_clearance_help和来源说明，不重复placements、不提供action。它不读case/score/referenceaction/未来/隐藏目标，是显式额外公开帮助，不能算裸模型能力或单因素作用域改善。

D4 child仍活动，当前blue目标neutral且实际已满足，剩余物品列表为空，但终止义务仍活动；唯一协议推进finish。D5 child已结束，blue仍neutral，需按最新有效outer目标place/careful。green/red实际进度保留，当前有效目标由公开接受/拒绝记录决定。脚本接受/拒绝不是模型亲自协商。

## 结果、方向口径与错误

|检查点/视图|协议推进/参照命中|重复finish|blue抓放选择|当前方向正确/错误|
|---|---:|---:|---:|---:|
|D4 full|28/32|0|4|0 / 4|
|D4 aid|30/32|0|2|0 / 2|
|D5 full|4/32|24|8|4 / 4|
|D5 aid|21/32|7|25|21 / 4|

全128无解析失败、截断、合法no-op或未授权help选择；模型只选finish和place_blue_left/right。careful等多解候选未被选，不证明它们已掌握。协议推进与参照命中分别评分，此次恰同计数；不把尚未执行的选择称物理成功，所有score标physical_execution=false、physical_success=null。

冻结blue_direction_correct按**当前活动目标**：D4为neutral，不因left/right匹配outer就算当前方向正确或推进；D5才按有效outer投递方向。六个D4错放全在during_child normal：full四次、aid两次。五次恰匹配outer却违反活动child，另一次连outer也不匹配。六项单列表位于direction_error_audit.json，不混入D5目标恢复错误。

D5八个方向错误均选择了**被拒绝的提议**，而非当前有效目标：

|视图/条件|seed与timing|初始/有效|提议/选择|数量|
|---|---|---|---|---:|
|full rejected_right normal|60/61 × before/during|right|left|4|
|aid rejected_right normal|60/61，during|right|left|2|
|aid rejected_left reverse|60/61，during|left|right|2|

accepted条件没有D5方向错误；这不代表accepted条件全推进，因为仍有重复finish。31次D5重复finish不是blue方向尝试，不能称31个目标记忆错误。全部45个非推进原messages、response、parse及score完整保存在raw/nonprogress_calls.json；八方向错误与六活动child错放的公开事件比对及稳定ID保存在direction_error_audit.json。

## 全条件与配对

|阶段/视图|before /16|during /16|accepted /16|rejected /16|normal /16|reverse /16|
|---|---:|---:|---:|---:|---:|---:|
|D4 full|16|12|13|15|12|16|
|D4 aid|16|14|14|16|14|16|
|D5 full|2|2|4|0|4|0|
|D5 aid|9|12|12|9|14|7|

D5 full在两timing同为2/16，aid during为12/16、高于before9/16；结果不支持“指导期间更新更难”的预期，但低分地板和小集不能证明等价。D4错误全during是描述线索；事件位置同时改变新近程度，显式finish接口、提议目标显著性、菜单顺序等替代解释仍在。新system和历史都区别于旧v9，不作跨轮提示或结构单因素因果比较。

每行下面有16个实际配对，计数顺序为two/one/none正确：

|阶段/视图|timing配对|接受拒绝配对|
|---|---|---|
|D4 full|12 / 4 / 0|13 / 2 / 1|
|D4 aid|14 / 2 / 0|14 / 2 / 0|
|D5 full|2 / 0 / 14|0 / 4 / 12|
|D5 aid|7 / 7 / 2|8 / 5 / 3|

timing对正确目标相同，接受拒绝对D5正确目标相反。64个full→aid转变为32 correct→correct、19 incorrect→correct、13 incorrect→incorrect，无correct→incorrect。summary.json另含stage/view/timing/acceptance/initialblue/effectiveblue/menu的完整64条件组，以及128个配对明细。两seed、同模板、菜单变体/辅助视图是相关观察，不是独立结构样本；不做显著性检验。

## 冻结、模型与审计

- 来源freeze：experiments/structure_v11/cases/reference_freeze.json，SHA256 `3449cd36abb8a9d07b3534fd8e045a27c7c08fd2fe5d1c3ffa27919896570be5`。
- 本轮freeze：cases/freeze.json，SHA256 `eef5663d8e8d036f43184208184d50ca3a3fb20473daa10af0dfac4f8316b9ab`。
- 128输入SHA256：`6f34a939ebf801a6c2c84860c485de3414db040c96999c45d8ddef4a47a83339`。

冻结绑定16来源决策文件、源freeze、运行/评分/公开归约依赖源码hash、model spec/download receipt和全部token长度。使用既有本地官方Qwen/Qwen2.5-14B-Instruct revision `cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8`，八分片LFS SHA核验沿用，配置/tokenizer SHA重核一致；无下载。torch2.6.0+cu124、transformers4.49.0，BF16/SDPA、greedy seed0、batch1、max96，一点一次。

最大输入2234tokens，含96输出的KV估436.875MiB；BF16权重字节+3GiB要求free31244MiB。实际启动实时GPU2 free32278MiB，单卡满足预算，无量化/offload/多卡。没有操作其他进程。原SDPA sliding-window提示保留日志，未改注意力或生成参数。

五项永久输入/协议测试：128来源及32原normal full、反序/辅助唯一差异、公开aid忽略私有字段且正确处理两timing、接受拒绝方向平衡、D4正对照/D5多解与no-op/重复finish/help/parse。focused5/5、一次full57/57通过，均不调用模型或物理。

独立后审计检查128实际输入/输出、token/parse/评分/截断/summary及128timing/接受拒绝配对，全部通过；后补方向分项只重派生审计，无评分或调用变化。audit.py/receipt.py是冻结后新增只读派生程序，单列hash；不能用其事后hash冒充运行版本。模型5426 exit0、CPU freeze83444/fulltest2466 exit0；后审计同步exit0，无持续句柄。自有PID23429不在ps/GPU进程，无活任务。完整metadata/峰值/资源和全部产物hash见execution_receipt。

```bash
# 已执行；freeze/evaluate禁止原地覆盖。
.venv-llm/bin/python -m unittest tests.test_structure_diagnostic_v12
.venv-llm/bin/python -m unittest discover -s tests
.venv-llm/bin/python -m experiments.structure_diagnostic_v12.run freeze
CUDA_VISIBLE_DEVICES=2 .venv-llm/bin/python -m experiments.structure_diagnostic_v12.run evaluate
.venv-llm/bin/python -m experiments.structure_diagnostic_v12.audit
```

完整输入/输出/日志在results/structure_diagnostic_v12/raw数据盘软链接；薄summary/audit/failure/direction/receipt和源码提交git。后续复现另建版本目录，保留本轮全部原始错误，不再追加尝试改善分数。
