# 更大生成式伙伴候选：尚未取得策略资格

当前多轮伙伴仍有提前声明完成、把未来贡献记成已执行、误解谁应回答或接手等问题。已有执行、真实输入和视频证据使这些缺口可以具体检查。下一步独立考察更大生成式模型，而不是继续只改提示词或训练人抓放。模型大小和通用能力不能直接证明它适合模拟真人。

候选为Qwen3-32B-AWQ，官方配置为4bit AWQ/GEMM。权重只由现有直连下载器从中国ModelScope取得，15文件、19341526164字节，大小及SHA核对完成；配置与来源见[ModelScope配置](https://modelscope.cn/api/v1/models/Qwen/Qwen3-32B-AWQ/repo?Revision=master&FilePath=config.json)。共享模型位于data1指定models目录，仓库入口为`models/qwen3-32b-awq-human-candidate`。

AutoAWQ单独安装在data1的human-awq-candidate环境，只读复用原有Torch/Transformers路径，不修改当前批次环境。入口为`.venv-human-awq-candidate`。采用非量化层FP16；AWQ加载方法见[Transformers 4.53.2文档](https://huggingface.co/docs/transformers/v4.53.2/en/quantization/awq)。AutoAWQ已停止维护，当前组合的简单加载通过不代表完整策略接口已兼容。

[准备及有限检查记录](../../results/area_feedback_prefix_20261009/human_model_candidate_preparation.json)明确区分结果：GPU0上的实际加载、有限logits及简单生成已执行，峰值allocated约19.37GB；回复含正确JSON内容但带Markdown围栏，所以严格裸JSON检查失败。诊断保留原文，没有改成“格式通过”。未测试两阶段私人意图/贡献、思考过滤与工具JSON接口，更没有真实Sim闭环成绩。GPU进程已结束并核实释放；未保存临时smoke文件。

资格顺序是：完整策略接口及实际token可重建；保存场景中自己的持物、支撑、既有约定和新需要理解有依据；再完成真实Sim日常活动与双方交互。针对本批Drawer全程未打开，还要独立检查当前场景的机器人操作前提，不能用更大人模型掩盖基本操作失败。

此候选不替换本批Qwen3-14B，不算新增机器人模型覆盖，也不使正式样本从0增加。若以后使用共享候选权重的协调器，必须说明人和协调器同时变化，不能归为单因素人策略改善；正式两个机器人系统比较仍需保持可比的人策略条件。

复现下载：`.venv-libero-native/bin/python scripts/download_modelscope_policy.py --model Qwen/Qwen3-32B-AWQ`。下载器关闭环境代理并限制中国ModelScope/中国区OSS来源，已校验文件可复用；模型推理只从本地加载，未向外部服务发送项目私有输入。
