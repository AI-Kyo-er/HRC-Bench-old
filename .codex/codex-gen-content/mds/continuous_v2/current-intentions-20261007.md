# 当前意图输入契约与真实共同活动

本轮收尾完成，完整成熟Benchmark目标仍active。用户明确要求每次重要实验提供真实Sim场景视频，报告优先展示运行时视频，轨迹用于审计。

f847f86：意图接受后再重建当前目标几何；明确self=human、other=robot与your_current_personal_targets，动作计划排除旧observed_changes／assumption_corrections而保留原始规划记录。没有分数路由、动作清单或自动切换目标。ccab5ca：三正式启动脚本与PLAN；5e54d93／8d40598报告；69f5d6a／3c66ed5：事后操作对象类别审计，不把其他物品操作自动判错。

正式单卡运行：GPU0伙伴资格、GPU1奶酪、GPU2抽屉，GPU3本地π服务；启动前NV检查显存够。本地中国源Qwen3-14B、π0.5-LIBERO，无新模型或数据下载。一世界／人初始化、init0／seed0、20Hz、60秒；每场10意图＋30动作NN调用。共同活动每场120次真实π推理、1200原生OSC动作，无协调保持／位移原语。

- current_intentions_qualification_20261007：泊车80真实控制步后机器人神经调用0。人碗／酒瓶私人目标；碗8.15秒双指接触抬升、16.25秒释放桌面支撑、16.40秒首次个人区域释放稳定；后续再次抓放、期末失效，酒瓶无人接触。个人目标false、变化0，手／机器人接触0，手峰速.196m/s、对象.198m/s，资格通过，不计HRC成绩。
- current_intentions_20261007/food_into_bowl：人私人碗／酒瓶，却30次grasp奶酪，选择个人目标操作0；没有完整双指抬升见证。机器人期末true，严格关系累计53.90秒、4次失效，个人false／共同0、变化0。接收碗最大位移8.46mm，选择操作碗0次，移动接收物条件未实现。手／机械臂接触57.00秒；物理对象峰速.610m/s，运动资格通过。
- current_intentions_20261007/drawer_access：人wine／plate，28次选择目标物操作但实际主要wine，未完成私人区域或操作第二plate；双指抬升8.35秒、14.4秒桌面支持，并非目标释放稳定。机器人抽屉关系累计37.40秒、期末true，人false／共同0、变化0。几何接触45.10秒；手.209m/s、选定酒瓶20Hz1.303m/s检查通过，但物理子步对象峰速1.596m/s>1.5阈值，整场诊断保留。

原始pixels/state/rawactions/ctrl/clock、私有公开边界、人两阶段输入来源、真实执行反馈、人物显示、相对支撑CPU重建、场景完整性、动作对象归属全部独立审计。无持续低于桌面10cm物品损失，不代表安全或完整质量资格。源运行中变化均为空。

三真实三机位视频896×51220fps，资格1281帧／64.05秒含4秒泊车，共同各1201帧／60.05秒。逐帧解码和timeline3/3通过；HTML三段实际播放、37.2秒seek同步（资格模拟33.2）、按钮、local links、Range206、375px无横溢出、无JS错误通过。大截图data1软链。报告experiments/current_intentions_20261007/index.html／README.md。

datasets/current_intentions_20261007：240观测2400学习动作，120／1200合格、120／1200诊断。独立NativeTrajectoryDataset按stem完整读取计数一致；无manifest，资格无VLA不混入。真实失败轨迹不当专家。

只读审查发现relative destination几何高度仍用receiver body点；三正式进程全部结束后未来契约v3改为当前support_xyz，新增支撑面与body不同、receiver移动及旧v2兼容测试。本批固定区域目标不受该relative路径影响，但没有真实相对目标行为复测，不回写原始v2。整套218passed／2可选依赖skip，compile／diff通过。

未验证：可靠自主生成式伙伴、多物品连续完成、真实目标变化、主动移动接收物、完整人体／五指、真人心理效度、跨任务统计与模型排名、cobalance构念。修正输入未能证明行为提升；前后非随机配对，不能作单因子因果归因。下一阶段应聚焦有效神经人策略与真正动态条件，不能再用微提示、更多对话或绿色工程核验代替核心效果。
