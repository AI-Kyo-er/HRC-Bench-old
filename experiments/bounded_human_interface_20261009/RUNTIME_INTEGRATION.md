# 接入持续活动的独立入口：代码已接通，完整行为待验证

`scripts/run_bounded_joint_activity.py`在独立进程中接入有限文本和真实失败反馈，原三活动运行入口保持原协议。它复用同一个持续世界、人连续执行、公开交流及真实π0.5控制，不改变高层动作／对象／目标选项，不从需要、角色标签或评分选下一策略。

贡献层的自由消息、理由、意图、参与和记忆使用已验证的长度语法。最终有效调用仍需满足该语法；违反格式或长度时记录原输出和真实错误，执行原有wait回退，不修复为正确动作，不把回退当自主策略。

意图层和贡献层分别看到自己的实际生成状态。失败的助手文本替换为对应决定ID、时间、解析错误、实际wait回退和未公开消息的事实摘要；原失败保留在原始研究记录。当前世界、公开交流、既有有效选择及后续实际执行不删改。对原饮品64秒保存输入的重建，只替换一条失败助手消息，助手文本从13313变为289字符；这说明表示变化，不证明策略改善或推理提速。

新方法明确记录human_output_protocol、human_failed_history_encoding、各文字长度和新增源代码SHA。独立审计按对应版本重建意图输入、贡献输入、工具声明、实际token及解析；旧方法仍按旧语法核对，不能混用标记。整套回归385通过／2跳过，包括两阶段失败后再决策、实际选择保留、长度违规回退、错误标记和作用域恢复。

## 后续完整开发验证

先收齐当前候选三活动及伙伴／任务审阅。下一阶段使用本入口检查完整持续闭环，包含实际私人需要更新、有效公开纠正、对方回应及行为后果；保留所有失败与缺少变化的样本。接口通过不代替任务可执行性、合理分工、六类实际情境或正式双系统比较，不围绕单个字符串反复做孤立版本。

示例参数（准备配置，尚未启动；运行前检查GPU与本地π服务）：

```bash
CUDA_VISIBLE_DEVICES=0 \
PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/schema-decoding/python:src:scripts \
LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native \
HF_HUB_OFFLINE=1 \
.venv-human-awq-candidate/bin/python scripts/run_bounded_joint_activity.py \
  --activity drink_storage --situation correction --profile particular \
  --init-state-id 2 --seed 115 --steps 2400 --context-step 800 \
  --human-decision-steps 80 --coordinator-decision-steps 80 \
  --workspace-method --activity-specific-context --human-auto-buffer \
  --human-relational-targets --human-complete-observation --human-area-placement \
  --human-contribution-observations --human-carried-observation \
  --symbolic-coordinator --robot-skill-bank --interaction-contract \
  --initial-human-holding --human-model models/qwen3-32b-awq-human-candidate \
  --port 8766 --output-dir results/continuous_v2/bounded_drink_correction_dev_20261009
```

重要运行结束后仍需完整输入／控制／真实视频核查与行为审阅，再作为结果发布。新入口未产生完整Sim结果，正式样本0。原模型、布局、采样和工具表示等变化的影响按完整方法解释，不预设成功率或因果改善。
