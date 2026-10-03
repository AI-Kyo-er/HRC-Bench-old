# 公开双目标依赖与确认时机的执行前提（v25）

本轮独立Episode将green固定目标或same/opposite(当前有效blue约定)要求置于同一持续World、检查服务和循环历史中。固定8更新控制、32完整矩阵规则参考、8真实前缀后的局部放置参考，没有模型/GPU/下载。协议与指定参考可执行不等于结构泛化、纯结构因果或人类协作机制；仍先仿真再真机。

## 公开协议与事件时间

red-left、实际240合格tick检查贡献、当前载台最终far稳定及blue/green要求同时验收。blue只由公开初始I和已发生的绑定提议/acceptreject回应求值。初始明确有一次pending确认，拒绝也关闭确认但保留目标；未回应不得更新，声明不触发未来回应。全部回应是脚本初始/事务，12菜单没有机器人自主acceptreject动作；request/check/运输响应及抓放另列。

green直接臂公开固定G，蓝更新不联动，初始公共消息中没有配对q。关系臂公开same/opposite，按最新有效blue求值；不使用实验生成器预定F给在线policy或评分。目标更新可能使此前合法green位置失效，须真实返工，但不追溯称先前违规。暂存到非当前目标盘只记可观察放置描述，不自动当禁令违约；错误声明与安全接触违规分别度量。

before_check在第一观察前追加提议/回应；after_handoff由服务emit钩子在实际贡献完成同tick生成并加入公共待观察队列。sync仅在下一高层边界补observed_tick，长技能不会被偷偷打断/重定向。每步保存发起时已经可见账本以及技能内发生更新，不能把未看到的新约定当作起始决策信息。declaredone只同步已发生事件，不step、不构造未来确认，终止后动作不再改变时钟/历史/成本/服务。

World、Panda摩擦抓放、支撑几何、载台曲线完全复用v23/v24。presence固定stay，检查请求受真实检查台支撑/速度、near稳定presence和机器人已离开blue的当前前提约束；检查与目标更新不清进度。物理抓放不按正确目标过滤，blue仍保留真实稳定来源和无active载台的已验证前提；原right扫掠范围公开，参考采用red-first、暂存、空载返回后放blue/green。全部条件12菜单一致，完整活动48步、yield1920上限，指定事实等待6000上限。

## 三阶段与局部边界

control8=I左右×U1–U4，seed120。先真实前送/red/检查台/空返far/greenI，再检查请求与真实交还触发更新。U1关系same接受后真实blueopp/greenopp返工；U2关系same拒绝只blueI；U3直接G=I接受只blueopp；U4关系same接受只blueopp直接声明，预设任务负例仅green旧要求未满足。严格8通过对应任务6成功，负例不事后恢复。

reference32=I×acceptreject×q×directrelation×beforeafter，完整各两值交叉，单seed120。生成器离线计算配对G=q(F)只用于公开直接目标构造，在线参考仅公开history/currentphysical。同一保守顺序先完成检查及事务，再实际空载返far、blue当前盘、green当前盘、声明。两臂的完整物理/动作/参数逐对核对；相同参考工作不等于输入或推理需求完全相同，直接目标是额外信息/计算帮助。时间条件也改变不确定状态持续时间，不能单独称纯记忆距离效果。

local8=F×G×表达，seed120。目标确认在检查前拒绝相反提议，blue保持F。前缀由实验参考在本World真实执行运输/red/检查台/检查/空返，未瞬移；begin_local保留整个历史、总成本/时钟/服务，记录prefix_decisions作为budget_origin，后续12步另列。公开local_measurement_start重复已经有效blue和green表达，不读私有目标；不把前缀动作计作局部策略自主工作。只有规则放置参考，没有神经局部能力成绩。

## 冻结、审计和测试

分阶段冻结，control严格审计通过才冻结reference，reference通过才冻结local。每份freeze记录8/32/8条件、配置/完整system/12候选/workspace、依赖源/测试/资产/版本及第一messages。初始物理snapshot复用v24 A120实际初始化状态与原文件SHA，没有复用旧任务目标或事务消息：新messages由本轮源构造，正式新World第一输入逐字断言。未来历史和局部起点不能预知，只冻结构造源，实际每一步事后重建。

独立审计重建循环/profile/支撑、presence与检查每tick、同tick事务和可见性，公开目标归约另有独立实现，不读case预定F。检查每次真实抬升/指爪接触/目的盘支撑、9禁止接触类别、持续非目标1cm保持、完整规范物理SHA与全部边界输入；不比gzip字节或用末态代替全轨迹。浮点范数只容1e-12独立舍入，接触/成功阈值不放宽。局部检查真实前缀与12步边界、prefix/local成本、消息和历史不可变。

新增15永久测试是FakeWorld/publicfacts/service反例，不能冒称物理：未回应/拒绝、直接不联动/关系反平衡、缺绑定拒绝、pending无未来泄漏、handoff实际tick和晚观察、不可打断技能中更新、声明不生成未来、非法耗步、局部成本不重置。首次focused15的1error为替身缺carrier_facts接口，源和失败日志保留raw；仅补替身API，不弱化begin_local真实far检查。修复后focused15 exit0；完整215项5353真实exit0。尚未有业务源或物理修订，同版不重试覆盖。

```bash
.venv-qwen3-v14/bin/python -m unittest discover -s tests -v
.venv-qwen3-v14/bin/python -m experiments.dual_goal_v25.run control --freeze
.venv-qwen3-v14/bin/python -m experiments.dual_goal_v25.run control
.venv-qwen3-v14/bin/python -m experiments.dual_goal_v25.audit control
# reference/local按同样顺序，仅在前一阶段审计通过后冻结执行。
```

raw完整物理/service gzip、原messages/动作/状态/frames与失败源存数据盘软链。最终句柄/PID/真实exit、源码/资产/派生审计版本、成本和严格/任务/安全分项见汇总回执。makespan包含停车及等待，从共同t0=240到声明，初始化另在完整trace计数；预设U4失败到终止时长不是完成效率，不比较CPU运行/审计墙钟速度。

## 后续容量的只读准备

`control_input_token_stats.json`仅对98条已经发生的控制输入用v19同官方Qwen3 tokenizer/启用thinking模板计数，没有加载权重。最大4585tokens来自U1_right第12序号的声明输入（零起始序号）；U1_left最大4582。控制的短历史不能证明任意48决策都在给定输入界以内。

`context_memory_readonly.json`记录本地原生context40960；候选24576输入+8192生成=32768，BF16 batch1 KV按40层×8KV头×128维计算为5GiB，权重29,536,665,640bytes加3GiB工作区的规划需求36361MiB。工作区不是峰值保证。`generation_memory_readonly.json`保存准确包源码SHA：4.57.1标准generate自动设置Qwen3支持的logits_to_keep=1，prefill仅末token lm_head logits；v19未开启全步scores/logits/hidden/attention保存。裸forward默认0与这一路径不同。仍需未来正式预检和实际峰值核验MLP/SDPA、动态KV及显存碎片；这些只读统计不构成新模型实验或显存充分证明。

## 正式结果与成本

| 阶段 | 严格符合预设 | 任务成功 | 物理安全检查 | 全量tick |
|---|---:|---:|---:|---:|
| 更新控制 | 8/8 | 6/8 | 8/8 | 142208 |
| 完整参考 | 32/32 | 32/32 | 32/32 | 543392 |
| 真实前缀局部参考 | 8/8 | 8/8 | 8/8 | 135848 |
| 合计 | 48/48 | 46/48 | 48/48 | 821448 |

总578决策、194真实抓放，物理技能失败0；九类禁止接触记录全部0，必要载台负载支撑178608/178608tick，最大连续非目标位移7.75769e-09m。必要承载、指爪抓物及物品支撑接触各独立统计，不能写成所有接触为0或真人安全验证。

U1两方向均在检查交还后真实移动green到新目标，13决策/5抓放、makespan19921tick。U2/U3与负例U4各12决策/4抓放、16741tick；U4独立确认仅green当前目标为假，其余条件真，声明后世界/历史/成本完全不变。U4较短是失败终止，不能作为完成效率。32完整参考每例12决策/4抓放、16741tick。8局部参考的整个前缀+局部仍同12决策/4抓放：参考前缀9决策/2抓放、10621tick，局部3决策/2抓放、6120tick；前缀不计作局部策略自主能力。

新增独立`report.py`在全部原audit通过后核验16表达配对、16时机配对及4局部表达配对：完整规范物理SHA/逐决策tick/动作/成本/终态均精确相同，局部实际checkpoint和前缀成本也相同。它还直接流式检查service日志中pending队列：检查后提议/回应首次出现就在实际服务完成tick，内容与后来公开history完全一致；检查前事务在第一真实输入已公开，物理service队列没有重新生成。48条全部通过。此派生源独立SHA，不改冻结runtime/audit/scoring或重跑；完整记录见`results/dual_goal_v25/final_summary.json`，各阶段原审计保持独立。

冻结SHA256：control `a7f35f0947153e2abc2a41ae58ed16f2c1177c44ecb4d41f1e16c16144b32f03`；reference `21d3681862ba39187692ae5a1ac813e4078cb98c98fa36023505ecb5bd41440f`；local `a348eedf3e9aea7333b205d18aa5bc22c648749852404792e3648a27a752df9c`。六个运行/原审计句柄40242/75686、17998/58296、44691/45843均真实exit0，派生report26879也exit0。`execution_receipt.json`核验冻结依赖/资产未变、执行源副本准确、全部PID退出与完整日志SHA；`finalize.py`在report已退出后归档，避免把写入中的日志前缀当完整hash。无物理同版重试、无神经调用。

原始关键帧（项目raw是数据盘软链）：`results/dual_goal_v25/raw/dev0/control/U1_left/frames/00008.png`为旧合法green；`00010.png`为检查/更新后；`00012.png`为真实返工后。负例终态见`control/U4_left/frames/00012.png`。完整参考见`reference/ref_left_accepted_same_relation_after_handoff/frames/00012.png`；局部真实前缀与完成见`local/local_left_left_relation/frames/00009.png`及`00012.png`。图片仅辅助，接触和时序结论依据全量轨迹。

单seed、确定性公开账本参考不代表模型能力或结构留出；直接臂提供额外目标信息，时机同时改变新近程度/pending持续时间，两者不能作纯结构机制因果解释。当前workspace沿旧源说明green保持到运输控制循环结束，本轮参考确实均在载台far后整理；未来神经输入应在新版本澄清运输循环与整段活动的区别，当前冻结措辞未改。
