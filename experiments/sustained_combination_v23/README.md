# 同一持续活动中的检查与最新交付职责（v23）

本轮将v21检查服务与v22循环运输放入同一Episode、一个World、持续公共历史与同一真实物理时钟。检查贡献、red-left、green-right、载台当前远端稳定和最新blue职责同时验收。只有规则控制/保守公开账本参考，没有模型/GPU/下载，也不据此声称组合泛化或完整六结构；仍先仿真再真机。

## 协议和执行

初始blue由机器人按公开left/right整理。第一次request_check实际接受、child已开放后，伙伴脚本提议改为partner_return，绑定accept/reject；接受只改变blue职责，拒绝保留原机器人目标，检查义务和red/green进度都保留。回复是脚本事务，12菜单不包含自主accept/reject；机器人实际请求与由实际前提触发的响应另记，不能称模型自主协商。

新CombinationWorld恢复v20真实presence运动，并保持v22循环编号/全部旧行程事件；载台0.04m/s/0.5s、presence0.08m/s/0.5s，几何/重装姿态不变。每step先电机/动力学、真实presence到位与循环事件，再写完整物理轨迹；随后同tick检查服务采样，独立service轨迹保存。服务只能影响下一tick的运动目标，不移动物品或伪造历史物理状态。唯一初始化后无reset/attachment，夹取是真实Panda动力学和摩擦抓放。

检查仍要求实际检查台支撑/位置速度、近端稳定presence且无机器人接触blue，累计240合格tick；retain/withdraw在60tick后真实离开，远端实际到位停480tick再回来。retain承诺和累计保留，返近继续；withdraw公开撤销承诺但保累计，返近必须新请求。不在场/来源不满足时拒绝且不排队。移动blue暂停合格采样但不按错误职责/检查完成阻止安全物理动作。实际贡献达到240后伙伴交还，不使用机器人finish。

所有条件12候选固定：v21原11加reload_blue。request_transport/return通过v22当前端点和活动运动接受/拒绝，重复不重启、反向不排队；载台与载荷到位分别按当前事实判断。blue抓放保留明确稳定来源与无活动载台前提，reload额外要求近端稳定，不按角色或检查评分筛选。错误目标/提前返程可真实执行并显式循环恢复。原历史delivery/return不替代当前支撑或本次行程。

policy只读已发生publichistory和当前physical，公开workspace含轨道/支撑/盘尺寸与扫掠限制；原系统没有免费currentgoal/scope/score标签。32例全部使用同一菜单和48决策预算；yield至下一条新公共里程碑或1920tick，旧事件不会重复零tick触发。请求/拒绝/重复/声明各耗一步但不模拟说话时间。技能期间伙伴逐tick推进，高层边界观察；反馈只报实际物理区域/公开响应，不指正目标。

declare_done随时真实终止且后续act不再推进物理/history/service/cost；末态私有评分绝不进入策略。最新partner职责须本行程实际带blue返远且当前far支持/速度满足，最新robot须blue在原公开LR；两支都要求当前far稳定、检查实际完成及red/green。过去一次返回之后再次前送会令当前far不满足，不能靠旧成功事件宣告履责。

## 固定控制与参考

control8先运行及独立审计，再reference24冻结/运行。完整source/依赖/资产/消息/配置/序列见control/reference_freeze_dev0.json，结果和终态句柄见项目results/sustained_combination_v23各summary/audit与execution_receipt。

C0两seed固定retain/accept：检查开放后等待实际presencefar、累计60，再reload、带blue返far、green-right、declare。预期检查未完且child仍活动，但redgreen/载荷职责已完成。stay不能用于这个负例：240检查会在抓放实际搬离前完成，所以没有调阈值制造失败。

C1两seedstay/accept：真实检查交还240后reload但不返程，再green-right/declare。检查和整理完成，但载台/载荷仍近端，实际任务失败。C0/C1的四次提前声明是真实终止，不是安全或基础技能失败，不混称32任务全成功。

R2/R3两seed：首次交付后、尚未请求检查即带blue返far；显式再次forward恢复近端，再暂存检查、开放child并接受/拒绝role提议，最后分别完成partner或robot-left。早返发生在职责提议之前，不能写成受已接受的新职责驱动；额外两次运输/成本真实保留，不称自主恢复或最优参考。

reference24=初始LR×roleaccept/reject×stay/retain/withdraw×seed120/121，单个保守公开账本策略。先运输请求、red-first与实际运输重叠；近端交付→blueinspection→request_check→role脚本→等实际交还。partner则reload/loaded return；robot保持blue检查台，empty return后再blueLR；两支green最后再declare。green最后是公开简单调度，避免已知right扫掠，不能据此主张复杂上下文规划必要。职责分支实际工作不同，不称严格操作匹配、结构因果、留出或最优。

## 实际结果

| 阶段 | 严格预期及安全通过 | 实际任务完成 | 审计tick |
| --- | --- | --- | --- |
| C0/C1/R2/R3控制 | 8/8 | 4/8 | 161658 |
| 公开账本参考 | 24/24 | 24/24 | 476760 |
| 合计 | 32/32 | 28/32 | 638418 |

9类禁止接触记录全部为0；载荷运动支撑208364/208364tick（参考133952/133952）。非目标持续区间最大位移0.000106875m，小于独立审计1cm保持阈值。必要blue–载台、blue–检查支撑及夹爪–当前目标接触正常保留，不能称全部接触为零。C0两条实际检查60tick而未完成；C1两条已检查240tick但载台和载荷未返回，四条声明立即终止后没有补救。

12组相同初始目标、presence和seed的接受/拒绝配对，从初始物理tick到实际检查交还的完整规范物理前缀逐字段精确相同；消息职责分支不同。每组的handoff tick、完整前缀SHA与逐项成本见final_summary.json。配对检验没有以gzip压缩字节替代内容，没有去掉接触或精度。两分支参考均实际4次抓放，但轨迹和职责不同，不由此声称完整操作匹配。

| presence | partner职责完成tick | robot职责完成tick | 决策数 | 检查请求数 |
| --- | --- | --- | --- | --- |
| stay | 16741–16742 | 16741 | 12 | 1 |
| retain | 21067 | 21066 | 18 | 1 |
| withdraw | 21067–21068 | 21067 | 19 | 2 |

这些时间从共同t0到声明，包含最终停车；两seed只是实例复现。C0终止18485tick、C1终止13021tick属于失败到终止时长，不是完成效率。提前载荷返回后恢复的R2/R3分别24182/24181tick，额外循环真实保留。

control运行97658及审计66015、reference运行64743及审计7452、派生汇总34914均已真实退出0。控制freeze SHA为`0dcd2b24b935264f5eb37c4c5ed9559be944477695a8f5cdd5253bef80b50ece`，参考为`2931a7ccd01a259c69b733cb1d659efe67abeaa968fc0a1f2924c01dd2cf0fec`；回执核对冻结源码/资产未变。raw数据盘约526MB，具体字节与各源/产物SHA见execution_receipt.json；report_terminal.json另记录汇总实际终态。无活实验句柄，也未使用模型、GPU或下载。

原始关键帧可查看`results/sustained_combination_v23/raw/dev0/control/C0_120/frames/`和`C1_120/frames/`；参考`raw/dev0/reference/ref_left_accepted_stay_120/frames/00006.png`为检查交还，后续00007/00010/00011对应重装、返回和green整理。`ref_right_rejected_stay_120/frames/00010.png`及00011显示blue与green分别放入同右盘。图像仅补充全tick证据，没有替代接触审计。

## 证据和复现

独立audit逐tick复算当前支撑/端点、循环请求及事件、两套平滑命令、presence运动/到位和检查累计/撤销/恢复。请求/同tick回应按决策序列重建，不用tick去重；原messages/budget/menu/history前缀/实际位置检查未来事件和别名污染。完整规范物理投影复用v22/v20canonical，保留全部接触/精度，只规范tuple/list，不比较gzip文件字节。独立numpy/Python范数复算标量允许1e-12舍入差，完整物理、事件/请求及布尔判据精确。

必要blue-carrier、blue-inspection、目标指爪和物品支撑分列；9类禁止接触均按完整接触字段/距离/力审计，非目标持续区间1cm保持，实际抓放核目的地/指爪接触/抬升。12项focused实际exit0；最终全套70520实际exit0，192/192。测试日志是协议/纯事实替身回归，不代替真实安全、检查或恢复证据。

```bash
.venv-qwen3-v14/bin/python -m unittest discover -s tests -v
.venv-qwen3-v14/bin/python -m experiments.sustained_combination_v23.audit control
.venv-qwen3-v14/bin/python -m experiments.sustained_combination_v23.audit reference
.venv-qwen3-v14/bin/python -m experiments.sustained_combination_v23.report
```

原run禁止覆写既有dev0目录；若物理/协议失败，必须保存版本后另冻，不能同目录重试到成功。完整physics/service gzip、决策原messages/前后状态及frames通过results/raw指向数据盘。回执保存真实handle/PID/exit、source/资产/原始审计源/报告SHA、包版本和数据量。makespan是t0=240至真实声明，含技能停车/等待；高层计算不推进物理，不比较并行CPU实现/审计墙钟，也不把失败早终止当完成效率。

本轮仍是指定开发组合可行性；没有单独组成/串接/依赖的受控对照、信息距离/绑定交叉、结构留出、模型策略或自然人/真机证据。两seed只是实例复现。允许公开账本、简单等待/暂存/red-first安全方法，后续主研究不能用工程模块增加替代这些比较。
