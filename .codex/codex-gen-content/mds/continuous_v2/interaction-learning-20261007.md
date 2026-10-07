# 接触历史与机器人活动学习：正式完成记录

用户要求重要实验必须真实Sim视频、清楚HTML目的／设置／结果。当前已运行的工作收尾，不以小批完成冒充成熟Benchmark。工具get_goal实际返回paused，未更改Goal状态；继续不应无授权恢复整个长程Goal。

报告：experiments/interaction_learning_20261007/index.html、README.md、facts.json、report_verification.json。15段视频全部逐帧／时间轴核验及浏览器真实播放、37.2秒seek通过；模型3段NN状态同步、29本地链接200、视频Range206、375px无横溢出、JS错误0。报告主展示实际Sim，轨迹／NN记录用于审计。

新InteractiveArticulatedHuman实际Qwen3-14B＋LoRA：当前直接手接触、前2测量history、真实空间动作move_hand。move_hand保持夹持且通过力控移动，不执行任务计划、不吸附。原始NN手部目标与实际递送独立核查，接触从raw重建，测量history按真实决策时刻重建。

新增12条80秒数据教师轨迹：8条π0.5活动food／stove、4条parked餐盘酒瓶。只有stove4条完整目标和运动合格，food4条失败，plate4条未入选（1条两目标满足但峰速1.5704>1.5）。humanNN0，实际robotNN160/活动episode。与旧16合格范例合并640监督对train440/dev200，原始960对，init3整episodedev。数据路径datasets/interaction_contact_20261007指向data1；同stem配对，无manifest。

200固定step训练完成、process exit0：5,242,880参数更新，delta6.562392，loss1.220117→.001505086，base冻结，sourcechanges[]，GPU0单卡peak30989MiB。权重共享models/Qwen/Qwen3-14B-HRC-interaction-lora-20261007；记录results/interaction_contact_lora_train_20261007。不得以loss代表能力。

三正式60s测试init4／seed4，每场人NN30；非teacher benchmark。独立资格：碗16.45s首次稳定、期末true，wine未推进，humanfalse；robot0，video64.05s含4s真实泊车。food joint：30grasp wine，人目标false，robot期末true，joint0s，handrobot接触57.35s。stove joint：先plate后cream，30grasp，人目标false，robottrue，joint0s，接触1.2s。每jointrobot120NN/1200act、video60.05s。三场directcontact30/30但move_hand0、semanticgoalchanges0；不能称可靠恢复、动态意图或cobalance改善。

三场source／adapter changes[]；12项独立核查全部exit0，真实物理／输入／私有公开／控制／relativegeometry／人物显示／motion一致。人objectposewrites0，缓存place重启见证0，无桌下损失。全部运动合格，但只是执行资格。人理想几何、人体骨骼显示＋真实受力双指，不是完整人体／五指／真人心理效度。

有效测试命令：PYTHONPATH=src .venv-libero-native/bin/python -m pytest -q tests --ignore=tests/legacy_llm_direction，229passed2skip。不要直接pytest仓库root，会搜results历史源码和vendor（本次曾造成103collecterrors，非有效当前套件结果）。compile/diff通过；永久回归测试保留，无临时smoke产物。

后续完整Benchmark未完成；有效interaction／recovery数据覆盖窄，泛化仍失败，不能继续只迭代提示或容易单例。Goal暂停保持；训练及评测进程均结束。用户COOPERA PDF不提交。
