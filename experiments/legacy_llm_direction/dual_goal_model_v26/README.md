# 双目标持续活动的神经闭环比较（v26）

复用第25轮已独立验收的World/12菜单与公开事务，固定16局部闭环在前、64完整闭环在后；目前先准备代码、CPU冻结和独立非任务显存预检，正式任务必须待探针回收验收。先仿真、后真机。不回改第25轮源码/输入/成绩，不根据本轮部分输出挑条件或重新采样。

## 输入与完整条件

完整条件I×acceptreject×sameopposite×确认beforecheck/afterhandoff形成16组，每组直接/关系×fullhistory/publicledger四臂。第g组将四臂基础顺序[direct-full,direct-aid,relation-full,relation-aid]左移g%4；模型每决策d的种子260000+100floor(g/2)+d。局部按F×G四组左移h，每决策270000+100h+d。物理seed120，完整48/局部12预算，yield1920，指定事实等待6000。80行与顺序/静态源/初始ids在freeze.json固定，没有依据局部结果删完整条件。

局部前缀由参考在新World真实前送/red-left/检查台/检查服务/空返far，保留全历史、时钟和总成本；模型从同一World的真实局部边界继续，prefix不消耗模型d/自主预算，不算局部自主完成。静态初始/局部消息来源于第25轮实际记录，正式执行逐字核对；后续分叉由实际动作产生，不用旧参考后续状态替换。

system继承v25公开规则无变动。只在独立新观测的workspace.notes澄清“运输循环”指载台前送/返程，不是整个活动；载台扫掠right区的风险公开，已far稳定无active时可整理green。两种表达/视图共同使用相同澄清，exact old/new保存在freeze。完整历史不截断。

aid额外归约当前有效blue/green目标及green表达、公开提议绑定/pending关闭状态、已公开scope/检查进度、由当前物理区域判断的done/remaining和公开载台义务/当前motion。只读history、physical_placements、当前carrier与motion，不读case的配对q/F/预定回应、私有score或未来。直接臂不暴露q，关系目标计算帮助和显式当前答案是额外辅助，不宣称两臂计算需求相同。

## 解析与实际终止

官方Qwen3-14B revision40c069824f4251a91eefaf281ebe4c544efd3e18，4.57.1环境、原生thinking、BF16单卡SDPA；temperature .6/top_p .95/top_k20/min_p0，max8192。沿v19最后think边界及原JSON/候选parser，缺边界或错误最终格式返回None，ep.act(None)实际耗1决策/0tick并公开未知候选，不找reasoning中的答案、不fallback或重抽。只有生成成功才产生动作，原始ids/输出在物理执行前先存calls.json。

安全但错误目标仍可真实执行，合法慢动作和暂存不自动记错；旧合法位置因更新失效不追溯违规。declare_done随时实际终止、不补救；预算失败、解析错误、输入容量、真实技能失败、全tick接触安全和最终任务不满足分开。失败终止耗时不作为成功完成效率。完整history超24576保存容量失败，不能删历史。仿真在推理期间暂停，model墙钟独立记录，不是人机实时流畅度。

## 非任务容量预检

CPU冻结单个非任务system/user及普通hello文本填充，官方thinking模板输入精确24576tokens、seed2699000。同一Backend.generate路径，输出8192；仅探针min_new_tokens8192防EOS提前终止，正式options不带。显式logits_to_keep1，return_dict=False、scores/logits/hidden/attentions不保存。没有任务World/候选/正确动作，输出不作能力评分。

总输入输出预算32768低于原生40960，KV纸面BF16 batch1=5GiB；权重29,536,665,640bytes+KV+3GiB工作区规划36361MiB，3GiB不是保证。实时选择free≥45000MiB的单卡；实测peak_reserved加2048MiB必须不高于启动free，探针结束free也至少2048MiB才合格。最终输出token通常不再forward，32768是保守KV上界；不通过开启return_dict测缓存伪称与正式完全相同。记录allocated/reserved真实峰值/加载信息、长度/输出ids/墙钟及前后nvidia。

## 测试与独立审计来源

CPU首次11focused通过；增加明确未来acceptreject不可见与handoff生成/晚观察反例后13focused与完整228通过。后来新增独立audit的4项反例，首次17项包括导入旧TestCase被重复收集的13项；1error为测试summary缺record_id。原失败log/源保留，仅补替身字段并改module导入，新增4/4通过；最终全套232（95774）真实exit0。不把替身单测当新真实物理证据。

freeze62996089023f72de804f31bf2fc64662a3cbfb11f59ce6ed8b1d9af61d597b4e保持不变。audit.py与新增audit tests在CPUfreeze之后写入，单独SHA/副本归档，不伪称原freeze已包含；它们不改变执行/输入/在线评分。独立全tick审计重算接触/支撑/持续非目标/服务/循环与事件，逐步重建消息/token/种子/parse/公开aid/成本。早声明可以尚无after事务，零tick请求必须按序列核对最后cycle注解；任务失败不自动当审计错误，真实禁止接触仍保留失败。

```bash
.venv-qwen3-v14/bin/python -m unittest tests.test_dual_goal_model_v26 -v
.venv-qwen3-v14/bin/python -m experiments.dual_goal_model_v26.run freeze
# probe/run均需先实时显存检查并设单卡CUDA_VISIBLE_DEVICES；probe完成验收前不run。
.venv-qwen3-v14/bin/python -m experiments.dual_goal_model_v26.audit
```

raw全部在数据盘软链。准备阶段回执与后续正式结果分开；单模板单物理seed不构成结构留出，shared seed不保证输入/轨迹相同。直接目标的额外信息、确认时机的提前工作/新近程度、可自主返工与失败等解释边界随结果保留；不将结果当完整六结构或HRI特有机制。

## 已完成准备证据

CPU冻结16231/PID247069、最终全套95774/PID251544及非任务容量探针92554/PID247870均真实exit0。探针在GPU3启动free48492MiB；输入精确24576、输出8192，实测peak_reserved36694MiB，相对启动free余量11798MiB、探针结束free11326MiB，四项检查均真。allocated/reserved与生成时长、完整原始ids见`results/dual_goal_model_v26/capacity_probe_receipt.json`及raw/probe/call.json，加载记录另存。探针进程已退出，不能把该终态句柄当作正式任务活句柄。

`preparation_receipt.json`记录80初始输入冻结、13定向/228早期全套/4新增审计/232最终全套的分阶段结果，全部冻结依赖与probe执行源副本未变，新audit源与测试单独SHA。准备提交时尚无正式任务生成或能力成绩；后续实际run须重新检查单卡资源，并沿冻结80表，不复用探针输出作为任务回答。

## 正式运行与派生准备

容量通过后重新检查GPU3空闲48492MiB，固定80正式运行已启动（7815/PID253762），按局部16、完整64顺序继续，尚无完整成绩。此段是运行中的阶段记录，旧准备回执的“尚未生成”对应其保存时点，不能将旧准备回执当现在状态。

第一局部已独立审计：两次生成选择blue-left及declare，真实安全与消息/物理/公开归约重建均通过，但green未达目标，因此任务失败；其2940tick为失败到终止耗时，不是成功效率。首派生入口6235/PID258008真实exit1，因直接启动数据盘脚本缺项目PYTHONPATH，在读取审计数据前失败；原日志/源保留。仅修进程包路径后49173/PID264345真实exit0，结果见`first_episode_preaudit.json`，没有重做物理/推理。

`stage_audit.py`在完整局部16终态齐后一次独立审计，原运行自然继续full64，不以局部表现调条件。`report.py`与`finalize.py`是运行开始后的事后派生源，独立SHA，不改freeze/在线评分。报告保留全部失败分母、表达/时机/视图配对及双方共同成功子集成本；前提拒绝/未执行动作、实际抓放失败、接触安全分别报告。成功恢复仍保留额外决策/真实抓放，非当前目标暂存不自动违规，也不能从一次动作推断模型内部状态。派生报告新增4项focused通过（早失败不混成功成本、单侧失败配对不删、局部成本保留prefix、拒绝reload无物理尝试），不将其写成原freeze的232测试。

局部阶段现已全部独立验收：审计78765/PID273826真实exit0，16/16重建与物理约束通过、14/16任务完成，272356个全轨迹tick、51次模型调用，无禁止接触/解析/容量失败。两例full_history（direct左/左、relation右/左）遗漏green后提前声明，失败终止时长单列。四格推进为direct-full3/4、direct-aid4/4、relation-full3/4、relation-aid4/4，单模板四目标条件的描述结果，不能当作自主局部能力充分证明。

`local_stage_summary.json`保留8组表达配对、8组视图配对、成功条件及共同成功子集成本、拒绝/多余等待/真实返工。完整阶段仍沿同一进程运行，尚无64回合终态成绩。派生源码稳定后已完成一次全套236项/2.273s/OK/exit0（包括新增报告4项）；此前容量阶段232仍对应其当时版本，未重复无改动测试或推理。局部归档源存raw/local_archive_source.py并单独SHA，原freeze/在线评分不变。

## 首完整四臂组阶段证据

按冻结顺序完成首组I=left/accepted/same/before_check的全部四臂后，复用现有episode_audit做一次整组CPU预审计，40557/PID295264真实exit0。原passed/strict为2/4、任务0/4、规定接触安全2/4，58923个trace tick、51次调用，parse/trunc均0；全部调用神经重建checks及contact字段完整性为真。该组不是完整64成绩，统一80终态审计仍全部覆盖，未依据阶段结果更改/重抽条件。

direct-full与relation-aid均提前声明，仍有检查和目标/载台义务未完成。direct-aid及relation-full因真实技能失败结束，并分别实际违反禁止接触+非目标保持、禁止接触+载荷连续支撑，保留原passed=false。首full单例预审计29833/PID289196也已真实exit0，只是此前通路核对，不能重复算新模型回合。

`first_full_group_preaudit.json`保留原checks/failed_checks/passed，`first_full_group_evidence.json`给两次执行失败的原lift/finger/EE误差、接触第一/峰值力与位置/距离、实际动作区间和载荷支持损失。direct-aid的green–carrier在yield内首接触16228、峰16835（108.538N），后抓取失败期间robot–carrier峰391.752N；relation-full的green–carrier首7280/峰7288（133.760N），robot–carrier峰338.549N，robot–blue保留记录7860、载荷支持首次丢失7863，返程支持2522/3180tick。正距离/零力保留记录、正距离有力记录和负距离接触均给模拟器原值，既定零记录标准不放宽；时序关联不单独证明全部因果，不从物品区域为空推断碰撞。

新增“reconstruction_consistent”仅为既有24项输入/事件/成本/服务/规范轨迹的一致性分项，明确排除successful_grasp_places_verified、all_forbidden_zero、loaded_support_all、non_target_preserved、contact_fields_complete五项，定义完整列于`first_group_reconstruction_definition.json`。它不是原整体审计通过、安全或任务完成；原passed/strict和五项逐例值不变。successful_grasp_places_verified仅核对声称成功的动作，不能因该项true就把另存的失败抓取说成成功。所有派生入口/source SHA单独保存，不改冻结评分、原auditor或运行源码。

## 第二完整组与前八例时机配对

第二组I=left/accepted/same/after_handoff四臂终态后，新增只读入口`timing_stage_audit.py`复用同一episode_audit，72534/PID485881真实exit0。115089个trace tick、85次模型调用；原strict/passed与规定接触安全均3/4，任务0/4，四例输入/事件/成本重建和全部神经核验为真，parse/trunc均0。完整80仍在原7815/PID253762运行，阶段结果没有改变条件、采样或评分。

direct-aid在48预算耗尽后结束，保留25次yield、45967等待tick、14次前提拒绝；4次物理尝试均未报技能失败，但全轨迹实际存在green–carrier禁止接触和持续非目标位移，原passed=false，不能把“无技能失败”说成安全。该接触首tick18354、峰tick18882（107.456N），3737条记录/1598tick，非目标最大位移0.24468358m；首/峰分别发生于序列22/23的yield期间。三个其他臂安全却提前声明，均未使载台实际返远；检查、确认和目标缺项逐例保留于原报告。

`first_two_groups_timing_preaudit.json`仅复用已保存首组结果，不重复首组全trace审计；四对的任务均未完成，规定接触安全分别为direct-full真/真、direct-aid假/假、relation-full假/真、relation-aid真/真（检查前/交还后）。终止原因分别为声明/声明、技能失败/预算耗尽、技能失败/声明、声明/声明。每例失败到终止耗时完整保留，不作为成功完成效率，也不从这八个固定模板条件推断总体时机效应。原passed、全部failed_checks、五项物理契约、检查累计、载荷连续支持和全部神经检查均未覆盖或放宽。

新增入口源码及audit/report执行副本单独归档于raw/second_full_group_audit_sources，SHA和真实退出码见`second_group_execution_receipt.json`；freeze保持62996089023f72de804f31bf2fc64662a3cbfb11f59ce6ed8b1d9af61d597b4e。原auditor/report/运行源未改，无新增模型调用、物理重试或无改动重复测试。
