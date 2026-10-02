# v17：固定Qwen3-14B两模式基础参照

当前为准备阶段，已完成固定官方revision、80条原封输入冻结及永久测试，权重仍在同一进程下载；尚无模型生成或成绩。准备回执中的live状态是所列采样时刻的实查，不保证未来仍活。

模型为官方文本`Qwen/Qwen3-14B`，固定revision `40c069824f4251a91eefaf281ebe4c544efd3e18`，8片共29,536,665,640bytes。官方逐LFS SHA记录在model_spec，完整下载后必须全部大小/SHA一致才可生成；不能将当前partial视为完整验证。权重/缓存在数据盘，通过`models/Qwen3-14B`引用，不升级旧环境。复用`.venv-qwen3-v14`的transformers4.57.1。

## 固定设计

每个模式完整使用旧v4全部40条：单动作16、多物品full_history12、public_progress_aid12。messages、候选、允许动作和原评分逐条完整保留；`prepared_input_audit.json`80/80核对通过。每模式只采样一次，每原case index固定seed17000+index，batch1 BF16 SDPA，max_new_tokens8192，无预跑/重抽/加预算。

| 模式 | enable_thinking | temperature | top_p | top_k | min_p |
|---|---|---|---|---|---|
| thinking | true | 0.6 | 0.95 | 20 | 0 |
| nonthinking | false | 0.7 | 0.8 | 20 | 0 |

采用固定revision本地[官方模型卡](https://huggingface.co/Qwen/Qwen3-14B/blob/40c069824f4251a91eefaf281ebe4c544efd3e18/README.md)和chat template。thinking输入只开assistant，模型自行生成think块；nonthinking输入明确闭合空think，输出不要求再次闭合。thinking按官方最后一个`</think>`（151668）之后解析；没有结束标记直接格式失败，绝不从reasoning找choice。多个marker保留计数，以最后边界为准。最终仍交原strict候选JSON parser，不修格式/Markdown/答案、不重试。完整文本、生成token IDs、输入模板/IDs与仅最终答复均存盘；截断单列。

原门槛仍为单动作16/16且full_history12/12，aid不代替full。旧模型成绩保持；本轮不同采样/模板/输出额度不是纯thinking或模型规模的因果比较。即使通过，也只覆盖该旧小集接口，request_transport等新组成能力另需验证；不启动组合闭环。

## 冻结、资源和失败记录

实际执行版本为`cases/freeze_v1.json`，SHA `a6bad34bef9eb7ea9f47d89350f3debd1ce0d158735a58575a32c76298eecb7a`。最长输入1157，输入+输出上限9349。BF16权重29,536,665,640bytes，KV上界1,531,740,160bytes，额外3GiB工作区/上下文裕量，要求单卡free至少32702MiB。生成入口每次加载前实时nvidia-smi并拒绝不足显存，不量化/多卡/offload。

首次CPUfreeze误断言thinking模板会在输入打开think，实际官方模板只开assistant，因而exit1；失败源/log存`raw/prefreeze_failed`，没有模型调用。纠正后形成未执行v0 freeze SHA `5252b7e29b0d178028052354c32f24b17ea5f21c5570aa043b105aa016f58c3d`。随后主控在生成前按官方最后边界规则修订解析，旧freeze及精确旧源/测试保留在`raw/unexecuted_v0_sources`，新v1独立冻结，80原始输入/参数未变。

6项固定人工适配测试通过；新隔离环境一次全套永久tests实跑110项、exit0（句柄50033）。人工测试检查0/1/多think边界、缺结束标记时不取reasoning答案、nonthinking空think输入约定、原strict parser与80来源/seed；CPU模板assert失败另列，不算人工测试失败。

```bash
.venv-qwen3-v14/bin/python -m unittest discover -s tests
CUDA_VISIBLE_DEVICES=2 .venv-qwen3-v14/bin/python -m experiments.reasoning_baseline_v17.run evaluate --mode thinking
CUDA_VISIBLE_DEVICES=2 .venv-qwen3-v14/bin/python -m experiments.reasoning_baseline_v17.run evaluate --mode nonthinking
.venv-qwen3-v14/bin/python -m experiments.reasoning_baseline_v17.audit
```

示例GPU编号需按启动时足够free的卡选择，两模式顺序单卡运行；不得直接照编号占用已不足的卡。入口拒绝覆写已有mode输出。`assets.py`固定revision下载，缓存锁/partial保留，不因观察超时重启。原始轨迹、完整生成及下载日志通过`results/reasoning_baseline_v17/raw`软链存数据盘。当前真实下载句柄71063/PID82422，后续须以write_stdin/PID实查续接；最终退出/完整SHA/GPU峰值/成绩另写执行回执，准备阶段不预写结果。
