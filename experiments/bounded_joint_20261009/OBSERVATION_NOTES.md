# 原始行为观察

本页记录本方法自己的完整Sim行为。当前没有已核验新结果；一次离线／接口重放不计本批运行。

独立8767服务的首次准备在模型初始化阶段退出：启动PYTHONPATH未含现有OpenPI Transformers适配路径。未开始仿真实验、未产生动作；原日志`/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/bounded_pi05_8767_20261009.log`保留。核对正常8766服务的实际环境后，新增显式启动脚本继承该路径；原GPU1无残留进程，显存17MiB背景占用。不是实验失败后重新挑选样本。

## 完整开发批已启动，结果仍待生成与核验

中文提交ebdf067固定条件后，GPU1独立8767服务严格加载完成，WebSocket实际返回π0.5 7D OSC、双相机和公开指令接口。GPU0启动父进程2819573、首例子进程2819637；原GPU2／3批次和服务继续，未热改其策略。实际启动命令保存在data1的`bounded_joint_batch_20261009.log`，各例另有独立日志，不覆盖旧结果。

启动检查时首例刚建立episode文件，尚未写出决策；随后已经产生自己的真实决策与控制，见下节。尚无完整终态，不能宣称新方法已经形成有效协作。后两例按预定顺序尚未启动。385项回归通过、2项跳过；新入口报告0视频／15链接、全局报告84视频／804链接通过真实浏览器核查。页面检查只说明现有展示可用，不是新增实验成绩。formal_samples仍为0。

## 新方法初始真实链路

[0至3.95秒来源快照](../../results/candidate_joint_prefix_20261009/bounded_drawer_initial_4s.json)保存初始Human、Robot、VLA调用及轨迹的6条原始记录，重新读取与行SHA核对一致。人0秒真实工具输出选择wait并公开请求Robot开中抽屉，保存语法实际包含五类自由文本长度上限，初始JSON/schema核对通过。Robot0秒据已进入输入的公开请求自主选择open_middle_drawer，8次真实VLA调用／80条状态已保存。选择开门不是已经打开，其生成memory_note中的“executed”也不作为操作完成证据。

这是本方法自己的Sim行为，不是此前单帧重放或旧candidate视频。全程视频、输入／全部token／实际控制及暂停恢复等后续变化仍须完整核查。初始调用有效不证明长期稳定伙伴、离返覆盖或新协议提高协作能力。

## 4至20秒：协调器宣称已开与实际关闭相矛盾

[12条来源重读快照](../../results/candidate_joint_prefix_20261009/bounded_drawer_observed_closed_claimed_open_20s.json)保留Human、Robot实际输入输出和状态行SHA。Robot4秒输入drawer.opening_m=-0.00165997、placement_accessible=False，测量句明确“interior placement is not accessible”；self_execution实际只有前4秒的8次VLA／80控制步，夹爪接触Cab不表示已打开。其历史0秒memory_note说“executed”，4秒输出却将它解释成“successfully executed”，宣称已开并选择hold。

8/12/16秒Robot继续同样保持和已开声明；19.95秒实际开口仍为负值不可达。人4／8秒按实际closed选择等待且不重复话语，16秒公开要求确认可用性，没有将Robot的已开声明当实物事实。当前不能把此受阻归为Human解析失效、缺少公开通道或模型输入缺少抽屉测量。

该段只显示Robot过早停止及事实误判；不证明若继续执行VLA就必然开门，也不证明π0.5在正常条件下不能开门。原candidate成功与新方法同seed不匹配独立π采样随机流，不作协议改善／恶化的因果结论。后续私有联系及整个活动仍按原冻结条件继续，完整终态不预判。
