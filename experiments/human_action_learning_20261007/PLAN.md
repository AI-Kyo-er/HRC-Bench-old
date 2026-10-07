# 真实接触范例与神经人策略学习

Material Passport：run／validate；用户Goal已授权实验，无新的权重或数据下载。仅安装PEFT0.17.1（清华镜像），使用已有中国源本地Qwen3-14B；权重共享models、数据／结果／环境data1。上一轮4真实运行完成，移除请求重启仍未得到第二物品推进。本轮进入实际动作学习，不继续提示微版本。

几何教师仅用于data generation：两场景food_into_bowl／drawer_access，init0-3，各两种偏好物品顺序，共16完整60秒接触轨迹、真实泊车4秒、20fps三机位视频。首场偏好黑碗／酒瓶、另一场奶酪／酒瓶；支持阶段和释放稳定检测只选择训练标签，不参与正式Benchmark决策。所有轨迹含实际双指受力、物品接触及控制，无吸附或物体pose写入。明确teacher_actual_neural_calls=0，不能当作人模型成绩。

训练样本同stem.source.json与.target.json，不用manifest。episode由stem在__step之前归组。init3全部为dev、init0-2训练，完整episode划分；未完成全部真实释放稳定目标的轨迹作为诊断保留，不进入该监督数据。首帧输入在loader中清空此前意图，以匹配NN首次生成目标的接口，物理测量与标签不变。

测量输入compact_measured_world_v1：当前物品／区域、握持、原语阶段和错误、接触实体、公开消息、上次自己的目标与过去动作；删除重复的长接触geom列表与重复执行历史。训练及正式推理使用同一投影，不以成绩或教师下一动作作为Benchmark输入。观察投影与权重学习同时成为新配置，不把前后变化归因于单因素。

Qwen3-14B BF16单卡LoRA：q_proj／v_proj、rank8／alpha16／dropout.05，160优化步、batch1／累积4、最大4096token、seed31、lr1e-4，checkpointing／SDPA。只监督目标回答及短教师依据；logits只保留回答长度+1，独立小Qwen测试与完整回答损失／梯度一致。全基础权重冻结，实际LoRA参数更新和dev loss保存；loss降低不当作闭环能力证明。

正式推理为实际Qwen＋适配权重生成个人目标与一个动作，仍自由选择／修改合法目标、等待、让行或活动安排；没有加载几何教师、目标完成自动路由或计划队列。初步资格使用训练未见init4；随后用原生task_only的π0.5共同活动检验真实动态条件，而不是将public_speech混杂称为原生VLA排名。

重要运行保存完整真实Sim视频及清楚HTML。代码／训练状态及实际结果分别报告，失败保留，不声明成熟Benchmark或真人心理效度；完整人体、五指、跨任务统计及cobalance构念仍需后续工作。

追加共同活动：160步训练完成后，init5／seed5、GPU0人模型／Sim、GPU3π服务，原生task_only输入120次真实VLA调用，固定60秒无成功早停。此运行不用于选择训练步数，也不回写独立资格结果。
