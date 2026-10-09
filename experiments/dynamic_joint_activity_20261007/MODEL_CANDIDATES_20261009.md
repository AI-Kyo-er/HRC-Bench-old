# 保留模型边界，扩展真实具身策略候选

## 当前已运行的系统

同版32B人策略／v5／有限文本方法已有理想测量32B协调＋π0.5完整抽屉结果，视觉8B协调＋π0.5批已启动。它们是两个明确不同的感知／协调系统，底层VLA相同。原OpenVLA空间检查点不能改名为Goal检查点；若测试跨套件，需要明确零样本边界并先核对实际操作，不能用旧空间成绩认证本次Goal任务。

## 国内可访问的World Action Model候选

[OpenMOSS官方EasyWAM仓库](https://github.com/OpenMOSS/EasyWAM)描述MoT为视频／动作专家混合注意力的action-only模型；[魔搭发布页](https://modelscope.cn/models/openmoss/EasyWAM-MoT-Wan22)提供LIBERO全参数检查点及配套统计。这里只核对候选，不引用作者成功率作为本平台表现，也不预设它具备动态HRC能力。

实际直连ModelScope取得两仓库文件元数据，禁止环境代理，下载重定向沿用项目China域名检查。EAM发布目录含约12.04GB全参数PT、约2.69GB LoRA及统计；Wan2.2-TI2V-5B目录约31.85GiB，含DiT、VAE、文本编码器和tokenizer。[元数据快照](../../results/joint_evaluation_preparation_20261008/world_action_model_metadata_20261009.json)明确标记metadata_only，不表示权重已下载。

已取得小型模型配置／统计及官方代码文档，固定官方commit `b80cff9ce881c51843481bcc21bc05057de6a7dc`，保存在data1的`cache/easywam-inspection`。统计中state为8维、action为7维并含32步统计；这只说明维度候选吻合，尚需核对坐标／姿态、图像处理、归一化和夹爪符号。官方[LIBERO评测代码](https://github.com/OpenMOSS/EasyWAM/blob/b80cff9ce881c51843481bcc21bc05057de6a7dc/experiments/libero/eval_libero_single.py)与[主干说明](https://github.com/OpenMOSS/EasyWAM/blob/b80cff9ce881c51843481bcc21bc05057de6a7dc/docs/instructions/backbone/wan22.md)是后续适配依据。

## 接入与任务资格必须完成的工作

1. 在独立模型环境中按冻结配置准备必要资产，确认全参数检查点加载是否仍需要ActionDiT初始化文件及哪些主干文件；避免先下载不需要的额外权重。不改正在运行的Human／π／视觉环境。
2. 按官方处理核对双相机、8维末端状态和7维动作；32步输出与实际执行／重新观察频率分别记录。不能仅凭形状把另一动作编码当OSC，不能用手写目标轨迹替代模型输出。
3. 在本项目同版初态、可见／可用资源及固定人参考下完成三活动关键操作资格，再进入动态伙伴闭环。参考清场与外部协调贡献分开；初态通过不保证更新后态可恢复。
4. 保留真实Sim视频、实际输入／输出与动作、模型来源及随机性记录。模型预测的视频若提供只能作为预测证据，不能替代真实环境视频。
5. 明确是裸WAM、HRC适配后WAM还是外部协调＋WAM。正式比较仍需可信伙伴、六类实际情境、结构对照、多初始化和预定统计；不以多下载一个模型缩小这些要求。

当前未下载大权重，未创建WAM推理服务、未产生新WAM动作／视频、未完成操作资格。它保留为真实模型家族扩展候选，不占正式样本。正在运行的同版两个系统继续原冻结条件，所有失败保留。
