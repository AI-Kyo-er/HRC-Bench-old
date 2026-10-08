# 已保存真实输入的有限文本接口检查

使用candidate_drink_correction_symbolic_20261009中36秒人贡献层的实际输入，原私人意图和历史保持。原输出反复生成communication.text，用完4096 token后JSON未闭合，未产生公开纠正或pause_current动作。本检查使用相同冻结Qwen3-32B-AWQ、FP16非量化层，单次真实贡献生成；不重跑意图层，不初始化／执行Sim。

改变工具声明和输出语法中自由文本的长度上限：公开消息512、理由512、意图256、参与128、记忆256字符。保留所有原动作／对象／目标选项，不从任务进度挑选答案，不修复旧JSON。seed14136；继承原伙伴轨迹和意图，因此不是新方法自己的持续历史。原输出之后的失败历史摘要尚不涉及这个输入，也不能据此认证其效果。

在空闲显存检查后，以GPU0单卡运行，独立于GPU2/3的三活动Sim批。source_nonempty_row及行文本SHA、实际输入／输出token、原生思考、模型精度及脚本SHA均保存。此单次采样的输出、格式有效性和语义合理性分开评价；不同采样和输入工具声明变化不能作单因素因果结论。

本页不计完整伙伴资格或正式样本。语法成功后仍须用完整Sim检验动态意图、公开纠正与实际贡献的闭环，重要Sim实验继续提供完整运行视频。这里没有新Sim动作，不把原场景视频当新方法动作证据。

运行：`bash scripts/run_bounded_human_interface.sh`。独立重建：`PYTHONPATH=src .venv-libero-native/bin/python scripts/verify_bounded_human_interface.py --input-dir results/bounded_human_interface_20261009 --source-dir results/continuous_v2/candidate_drink_correction_symbolic_20261009`。输出在data1，通过repo软链访问；原失败与正在进行的Sim设置不覆盖。

后续已准备[持续活动运行接入](RUNTIME_INTEGRATION.md)：两个策略层均得到实际生成失败反馈，贡献层声明长度并做有效性检查；尚未启动新完整Sim，不计新的行为证据。
