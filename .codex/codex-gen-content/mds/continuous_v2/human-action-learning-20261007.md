# 真实接触数据与神经伙伴动作学习

本Goal turn为progress：完成实际数据、模型参数训练、3神经资格检查与1原生π共同活动，20完整真实Sim视频。完整成熟Benchmark目标仍active；不是完成或blocked。

8e5ffc4：LearnedArticulatedHuman保持Deliberative单次thinking输出目标与动作，自由合法JSON，没有教师、目标满足路由或自动计划队列。compact_measured_world_v1投影真实物体／区域、当前原语／握持、物体接触实体、公开消息与自己的意图，去掉重复的长执行历史／geom列表、过去reason。原始约4500-10800token，训练样本含回答最大3076token。输入投影与权重适配共同变化，不作单因素改善归因。学习高层意图／动作选择，未训练人体／五指运动网络。

数据generate_human_contact_training.py：GPU1单卡≥4GB先NV检查，16轨迹food_into_bowl／drawer_access×init0-3×orders0/1，80步真实泊车＋1200步60秒，20fps三机位。黑碗／酒瓶、奶酪／酒瓶两种组合，教师ContactDemonstrationTeacher只用于Data generation。实际神经调用0，不计HRC成绩。真实双指受力／支撑释放，pose写入0。全部16两物品释放稳定、运动资格通过；16视频各1281帧／64.05s／896×512完整核验。

数据datasets/human_contact_teacher_20261007软链data1：480对.source.json／.target.json同stem。episode从stem的__step前缀匹配，metadata episode_id仅核对，没有manifest。init0-2训练360、init3 dev120，整episode分组；loader核查独立training_data_verification并排除失败／运动不合格，本批无需排除。首帧在loader清空旧意图，物理测量与教师标签不变，以匹配NN首次生成目标。

6ced141：独立从raw trace／contacts／control重建教师释放稳定与运动，视频及source冻结通过；不能以教师dwell值自己认证。PEFT0.17.1经清华镜像uv安装在data1环境，没有新模型或数据下载。

训练GPU0先NV≥45GB检查，实际BF16 Qwen3-14B＋LoRA q_proj/v_proj rank8 alpha16 dropout.05，160优化步、batch1／累积4、4096最大序列、seed31、lr1e-4、SDPA／checkpointing。仅监督回答及短教师依据；logits_keep=answer_len+1损失与完整answer-only loss和所有参数梯度在小Qwen3独立测试一致。训练基础参数冻结，5,242,880 LoRA参数更新，变化范数6.665169，峰值30574MiB。dev 1.2241916→0.00040165。训练source变化[]，实际曲线training.jsonl与独立Matplotlib SVG／PNG保存。每40步权重保存，但最终配置固定160；40步实测不用于择优调参。

权重共享models/Qwen/Qwen3-14B-HRC-contact-lora-20261007；训练记录results/human_contact_lora_train_20261007为data1软链。闭环确实载入PeftModelForCausalLM，provenance保存adapter config／safetensors哈希及运行中变化[]。资格源包含learned_human.py；未训练init4／seed4，3场各30NN／1200控制步、机器人NN0／不计HRC。

- learned_human_step40_qualification_20261007：阶段权重仍反复处理黑碗，首次黑碗关系54.45，期末黑碗true，酒瓶无人接触，整体false。运动通过，真实失败完整保存。
- learned_human_qualification_20261007：最终160权重、food/init4。黑碗16.45秒、酒瓶31.75秒首次释放稳定，两项期末true，整体human_goal_success=true，首次实际学习模型多物品推进。所有目标由NN选择，没有教师调用；仅单次狭窄资格，不能称通用伙伴。
- learned_human_drawer_qualification_20261007：最终160权重、drawer/init4，偏好酒瓶／餐盘。酒瓶15.85秒稳定、期末true；未训练餐盘组合无人接触，整体false，运动通过。真实新组合泛化未通过。
- learned_hrc_food_20261007：GPU0人／Sim、GPU3π服务，init5／seed5。真正task_only语言，原任务put cream cheese in bowl，不附人消息或私人目标；无视觉协调器。120π模型调用／1200原生OSC，人30NN。NN先grasp wine而非独立资格的black，但没有任何目标物品操作接触，后续observe，个人false／变化0。机器人严格目标累计27.85秒、9次失效，期末false；共同0。手／robot几何接触33.10秒；运动通过，重启缓存place见证0。

关键下一步：本批compact投影丢弃了直接hand_contact_report（包括contact_with_other_agent）及测量短历史，只保留每对象接触。HRC独立审计decision_count_with_direct_hand_contact_feedback=0，而真实手／robot接触33.10秒。因此不可断言NN已经看到阻挡却不愿协调；需要恢复紧凑真实接触提示与短测量历史，并扩展含真实移动robot、阻挡、失败恢复及更多物品组合的训练范例。当前仅静止robot教师数据，不能简单加训练步数或继续小提示版本。正式Benchmark必须仍是实际学习／生成模型，教师只数据生成；控制原语FSM不能成为高层策略路由。

1e37e85／27c5437：独立反馈验证按compact声明字段核对实际位置／EEF速度／对象接触，不要求未公开的body_target或robot_action，旧契约分支仍保留。private targets/raw生成、实际请求身份、力／运动／时钟、avatar、相对支撑CPU重建、场景完整性、视频均核查通过。通过工程链路不是认知、心理或HRC能力证明。

报告experiments/human_action_learning_20261007/index.html：数据／训练／闭环清楚分开，3代表教师视频＋全部4神经实验，保留失败与参数来源。NN视频37.2seek同步（3资格模拟33.2，HRC37.2），7视频实际播放、21local链接、loss SVG、Range206、375px无溢出、无JS错误。全部16教师视频原始保留。大截图data1软链。225passed／2optional skip，compile／diff通过。

只停止本轮π／报告服务，不动其他进程；用户COOPERA PDF未跟踪不提交，无临时smoke。

重要行为要求：主模型本轮再次有大量无意义内部分析，尤其随机下划线元数据／类名、重复未来幻想；它们不是实现，不要继承或重复。下一turn应一两句分析就调用工具，优先实际机器人条件的训练数据／观察契约和完整场景效果，不再十几分钟空想。所有进程本轮结束，下一次以git与实际文件／NV重新核查；不要无故复跑旧阶段。完整人体／五指、WLA、更广任务与重复初始化统计、真实心理／cobalance效度仍未完成。
