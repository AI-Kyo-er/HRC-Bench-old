# v16：请求接受触发真实伙伴运输

本轮复用v8最终载台与Panda摩擦抓放，验证request_transport的接受/拒绝、资源状态和组织顺序如何改变真实贡献与共同时间。10控制及16闭环规则参考均通过；没有模型调用，不改变两模型旧工程gate false，不声称神经能力、六结构覆盖或组合泛化。

## 实现与公开边界

旧world_v2初始化只持载台在源位，自动运输原由旧Episode构造器调用start_delivery。新独立Episode不自动调用，只有当前ready且尚未启动时接受request_transport，才调用原start_delivery一次。world继承原simulate、电机、profile、交付判据和抓放，仅增加无缓存的当前可用性事实与wait_ready；没有运行中reset物品、attachment或写物理成功。

几何/曲线固定沿v8：载台(.65,.60,.045)→(.65,0,.045)，blue初始(.65,.60,.073)，无侧壁，重力/摩擦承载；速度.04m/s、加减速各.5秒。red-careful与blue-direct各策略相同。red/blue到left，green未分配。稳定交付首次由载台到位/速度、blue实际相对位置/速度与支持接触共同满足锁存，机器人取走后事件保留。

共同t0为180 tick初始化结束；DT=1/240。伙伴初始ready或temporarily_busy，busy在内部固定1920 tick（8秒）后ready。这是抽象资源占用，不模拟人体离开/返回。策略只读公开当前状态/真实物理时钟；未ready时ready_event为null，system、初始history和obs均不提供未来ready_tick、倒计时或8秒参数。已发生ready事件才公开availability_actual_tick，observed_tick另列。资源变化与策略/未来plan无关，也不保留被拒绝请求为pending自动执行。

21候选固定所有条件相同：v8全部20 ID＋request_transport。接受、拒绝、重复各消耗1决策、0物理tick，反馈不模拟说话时间。已启动后重复为合法no-op，不重复计接受或改变start_tick/曲线。request_clear不启动运输、不授予assisted。blue未交付时所有抓放均拒绝且不执行，green未分配动作拒绝。red可在尚未运输或运输中正常整理，跨拒绝/再请求保留其进度。

yield已启动时等待实际交付；未启动且busy时逐tick读取当前状态等公开ready；ready未启动时零tick合法no-op，不自动请求。沿用候选的通用yield短标签仍说让出通道，等待ready/交付的精确定义由本版本共同system明确；本轮规则按公开事实与ID运行，未校准神经模型对该文字接口的理解。

## 分阶段冻结与控制

首次生成但未执行的control_freeze.json及源保存，SHA `d0bead9d6bdb0d260914c9208eae3888e4f242f742588287e4ff1063b5e794f0`。在任何v16真实物理输出前，移除公开未来timer表述，并基于v8已知时长预先加入wait_ready（参考12→16），将adaptive改名availability_greedy，不暗示最优。原曲线、8秒内部条件、10控制时窗均不改。实际执行控制freeze为control_freeze_public_status.json，SHA `9c2ed2b27471038755eddd8b6b81ee17c2bdb2b657d5f4c7e22c6f7a7421cf83`。

每项seed80/81，10条控制只验证触发/承载机制，不以最终red/blue任务成功评分：

| 控制 | 请求/实际step | 实际结果（两seed一致） |
| --- | --- | --- |
| ready_no_request | 不请求，等4000tick | 不启动，不交付 |
| ready_accept | t0接受，等4000 | start180，交付3895 |
| busy_reject | t0拒绝，等4000 | 2100已ready、4180才被高层观察，仍不启动 |
| busy_retry | 拒绝→等1920→新请求→等4000 | start2100，交付5815 |
| ready_duplicate | 接受→等1000→重复→等3000 | 与ready_accept完整规范物理轨迹相同，不重启 |

busy_retry总5920 tick单列，不与前四项4000窗口混称相同。控制等待是明确记录的外部定长真实step，不冒称这些step是策略yield决策。真实yield新分支另由16参考中的wait_ready覆盖。

10/10控制通过、45640 tick。四禁止类别records均0（robot–carrier、red/green–carrier、carrier–静态物体、非当前目标的robot–物品）；必要blue–carrier接触另列。未启动阶段载台保持源位且blue真实支持；有运输时支持覆盖1.0。详细公开输入/时钟/请求因果审计见[control_audit](../../results/responsive_transport_v16/control_audit.json)。

## 16条真实参考与成本

参考freeze SHA `d2f14a1aa6aec75f005bd17560bc51a9ebe05cdf82ba71b9123f362f02ff919a`：seed80/81 × ready/busy × 四策略。算法只接收公开observation和独立固定算法名，不接收world、Episode、case、私有timer或未来计划。

- availability_greedy：当前ready则先请求并与red重叠；busy则先red后请求。
- serial：始终先red再请求。
- eager：先请求；拒绝后先red，再重新请求，不把拒绝当自动运输。
- wait_ready：busy先yield到当前公开ready，再请求并与red重叠；不读取未来deadline。

16/16实际闭环完成，138640 tick，68决策、32摩擦抓放、16接受/2拒绝、18次yield、0物理失败。两seed全部以下成本一致：

| 初始状态/策略 | 共同makespan ticks（秒） | 首次物理目标满足 ticks | 等ready/等交付 ticks | red与运输重叠 ticks | 决策 |
| --- | ---: | ---: | ---: | ---: | ---: |
| ready：greedy/eager/wait_ready | 6655（27.729） | 5445 | 0/535 | 3180 | 4 |
| ready：serial | 9835（40.979） | 8625 | 0/3715 | 0 | 4 |
| busy：greedy/serial | 9835（40.979） | 8625 | 0/3715 | 0 | 4 |
| busy：eager | 9835（40.979） | 8625 | 0/3715 | 0 | 5 |
| busy：wait_ready | 8575（35.729） | 7365 | 1920/535 | 3180 | 5 |

makespan从共同t0到blue完成抓放并最终停车，未从较晚的运输启动重算；首次目标满足是另一指标，二者相差1210 tick。重叠为red技能执行区间与实际运输区间交集，含技能停留/停车，不是人体流畅度。red实际技能3180 tick（13.25秒），稳定运输3715 tick（15.479秒），均未为收益调时长。

ready条件serial比重叠策略多3180 tick（13.25秒）。busy条件wait_ready比availability_greedy/serial/eager快1260 tick（5.25秒）；因此“busy先red”没有最优性。eager与greedy同busy完整物理轨迹，只多一个零tick拒绝决策，不人为加等待罚分。busy高层ready观察：greedy/serial/eager实际2100、观察3360；wait_ready实际/观察均2100。

16参考四禁止接触类别records均0，blue必要承载记录420160、运输支持覆盖1.0；green全tick最大漂移约1.12e-11m，取走blue后交付事件仍锁存。初始同状态不同策略messages逐字相同；同seed跨资源状态初始物理checkpoint及完整初始化prefix相同。ready greedy/eager/wait_ready规范完整物理轨迹相同，busy greedy/serial/eager也相同。比较使用明确物理投影保留关节、末端、全部物体状态、载台位姿/速度/命令、完整接触和真实tick；只排除已分类协议/审计注释，未知字段拒绝。tuple/list仅规范容器、无容差，不用gzip artifact SHA判物理等同。

所有成本/逐tick时钟与输入/支持/首次交付复算见[reference_audit](../../results/responsive_transport_v16/reference_audit.json)。两seed只是实例复现，不是结构留出或统计独立样本。简单当前状态规则与等待方式足以解释本轮机制；没有神经运行或新调度理论声称。

实际帧：`results/responsive_transport_v16/raw/reference/Transport_temporarily_busy_wait_ready_80/frames/00003.png`（red已整理、运输中）、`00005.png`（接手blue到left，green保留）；busy eager目录`00001.png`为拒绝后未运动证据。

## 验证、归档与复现

10项focused通过（9项FactsWorld协议/状态/策略替身＋1项已有真实contact schema规范比较），全套97项一次通过。替身证明逻辑边界，不当实际物理证据。第一次测试失败来自父FactsWorld pick自增1tick与替身额外3180叠加，得到3181；失败源/log保存，仅修替身后续simulate3179使总3180，业务未按失败改规则。真实物理无失败、无重跑。

10控制及16参考均实际exit0；独立两阶段audit也exit0。原control派生audit源快照SHA对应control_audit，随后只增加参考四策略成本/初始输入表，参考audit另绑自己的SHA；不覆盖reference freeze绑定的control文件或运行源。源码/原v8未变、包/资产、终态句柄/PID、各产物hash和存储见[execution_receipt](../../results/responsive_transport_v16/execution_receipt.json)。全部原始完整轨迹、输入输出、关键帧和失败记录存数据盘，通过raw软链引用；无manifest。

```bash
.venv-llm/bin/python -m unittest tests.test_responsive_transport_v16
.venv-llm/bin/python -m unittest discover -s tests
.venv-llm/bin/python -m experiments.responsive_transport_v16.audit reference
```

审计可只读重算；run/freeze禁止覆盖已冻结或已开始输出。当前控制审计文件保留其实际执行源版本，raw/postfreeze_audit_sources/controls_audit.py作为该版本证据；不以事后新audit源冒充旧版本或覆盖reference freeze已绑定的控制产物。
