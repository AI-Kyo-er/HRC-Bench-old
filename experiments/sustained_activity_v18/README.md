# 第十八轮：一次持续共同活动的闭环物理基础

本轮在一个World、一条物理时钟及持续公开历史中完成请求运输、red整理、blue接手和机器人明确声明结束。初始化不预执行red；伙伴只有接受request_transport才启动真实摩擦载台。blue错误方向照常真实执行，反馈仅报告实际区域；过早或错误declare_done立即结束，事后评分不返回策略。六个固定候选不按目标过滤。

三个冻结阶段及独立全tick审计均真实exit 0：恢复4例、负面完成4例、参考48例。56/56是预设控制与审计通过，目标符合为52/56（恢复4、参考48）；负面4故意不符合目标，不算任务成功。恢复实际覆盖错误放盘→同盘重复零tick→跨盘真实抓回，声明后再次动作被拒绝且物理/历史不变。负面覆盖初始就声明、仅red后声明及两方向错放后声明。

|阶段|freeze SHA256|实际tick|目标符合|
|---|---|---:|---:|
|恢复|a6db9accae1d94d5b414378fb794f2d743522812803107aca8eab4154be7c51d|39100|4/4|
|负面|90d13fcd5afa8c7c8a38585e91672363f7281e1a99cfbcb172ae0b0b5880a7fc|17210|0/4|
|参考|264e92148d9ba81998f35fe2c846bcebf6ba9c17e4a9fa181d7458cac6ba8735|427440|48/48|

合计483750tick。独立审计核对全部接触、载台同tick FK与joint、交付支持和事件、输入快照与不可变历史、零tick事件顺序、实际区域、终止后不推进。robot–carrier、其他物品–carrier、carrier–static及非目标robot接触记录均0；运输中的必要blue–carrier支持覆盖1.0。这是限定几何代理的接触审计，不是真人人身安全验证。完整物理比较复用规范容器投影，不比较gzip文件头。16个同seed/资源/策略/有效目标的三种历史组全轨迹物理精确相同。

48参考为seed100/101×初始blue左右×无更新/接受相反提议/拒绝相反提议×ready/busy×两种公开历史策略。public_ledger_parallel请求后与red重叠；conservative_serial先red再请求。两者只读公开观察，不称全局最优。ready共同活动时长分别6655/9835tick，busy分别8575/9835tick；相同方向的两seed和不同约定历史复现一致。时长从共同运输/活动起点到明确声明终止，含最后技能停车；物理目标首次满足另外记录，不能混用。

参考共252决策、96物理抓放、48接受、0拒绝、60yield、48声明、0技能失败。合法但慢的等待和零tick操作计成本，不能一概判成语义错误。参考策略都等公开ready后请求，因此拒绝分支未在本轮48参考中暴露；真实拒绝控制证据来自原v16，新的永久协议回归也涵盖拒绝/再请求及red进度保留。busy为资源状态代理，不是人体暂离/重返。早期约定/回应是脚本共同背景，不是自然协商。

验证为11项新focused事实替身测试、完整121项永久tests，实际exit 0。首轮两个测试错误来自旧替身objects为字符串/None，补position/velocity schema后通过；失败源和日志保留，不能算真实物理失败或错误恢复证据。没有为测试重跑已冻结物理。

执行句柄：恢复7895/审计88556；负面58754/审计68313；参考90454/PID113917及审计49509/PID118364，全部真实exit 0。运行源及资产与三个freeze一致。恢复CPU工作与v17 GPU评测末段重叠，负面审计与参考CPU短暂重叠，墙钟不用于性能比较；仿真在高层计算时暂停。

可复核产物：`results/sustained_activity_v18/{final_summary,execution_receipt,recovery_audit,negative_audit,reference_audit}.json`。原始tick、逐决策规范messages、结果、失败测试及帧全部在`results/sustained_activity_v18/raw`软链，实际数据盘路径为`/data1/sieniwgroup/sieniw/HRC-Bench/results/sustained_activity_v18`。代表帧为`raw/reference/Reference_left_accepted_ready_public_ledger_parallel_100/frames/`；所有评分仅在终止后归档，不进入观察。后续模型闭环须另冻输入构造、模型参数和协议条件，本轮规则成功只支持执行基础可行性，不证明组合泛化。
