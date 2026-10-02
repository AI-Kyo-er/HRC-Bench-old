# v17：固定Qwen3-14B两模式基础参照

本轮固定80调用已全部结束并独立审计：thinking单动作16/16、完整历史12/12、进度辅助12/12，原工程门槛通过；nonthinking单动作15/16、完整历史12/12、辅助12/12，门槛未通过。无格式错误或截断。旧模型与旧结果保持。

模型为官方文本`Qwen/Qwen3-14B`，固定revision `40c069824f4251a91eefaf281ebe4c544efd3e18`，8片共29,536,665,640bytes。官方逐LFS SHA记录在model_spec；8片完整大小/SHA及metadata均已通过，真实下载句柄71063 exit0，全程保持同一下载进程，无重启。权重/缓存在数据盘，通过`models/Qwen3-14B`引用，不升级旧环境。复用`.venv-qwen3-v14`的transformers4.57.1。

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

示例GPU编号需按启动时足够free的卡选择，两模式顺序单卡运行；不得直接照编号占用已不足的卡。入口拒绝覆写已有mode输出。`assets.py`固定revision下载，缓存锁/partial保留，不因观察超时重启。原始轨迹、完整生成及下载日志通过`results/reasoning_baseline_v17/raw`软链存数据盘。准备回执保留当时下载中的真实采样；最终`execution_receipt.json`记录71063、thinking83074/PID101226、nonthinking14588/PID111387、audit42752均真实exit0，GPU和下载进程已退出、显存已释放。

## 最终结果与限制

| 模式 | 单动作 | full_history | public_progress_aid | 原gate |
|---|---:|---:|---:|---|
| thinking | 16/16 | 12/12 | 12/12 | true |
| nonthinking | 15/16 | 12/12 | 12/12 | false |

唯一失败是nonthinking `single_dev_yield_left_1`：公开输入要求下一步先yield，生成`{"choice":"careful_blue_left"}`，allowed仅yield；thinking对应为yield。原始输入、两模式原输出/最终答复/seed存`mode_failure_pairs.json`，错误分类为yield_requirement_ignored。没有因格式或截断造成失败；thinking累计27028输出tokens，nonthinking348，全部保留。

独立`model_audit.json`80/80检查：原40输入/候选/labels、渲染模板/IDs、完整输出IDs解码、官方最后token边界、原评分、每例seed与额度全部一致。CPU准备阶段110项全套通过；没有为成绩新增测试变体或生成。两模式每次启动都在GPU2实查free48494MiB≥32702要求；实际peak allocated分别29,990,195,200与29,905,044,992bytes，metadata另存reserved峰值。

这是更强本地文本模型在旧接口有限fixture的基础参照，修正了“旧模型全历史总失败必然是交互结构困难”的预期，不能证明六结构能力或闭环泛化。thinking/nonthinking的采样参数和模板不同、旧模型参数亦不同，不能将成绩差归因某单个因素。v18 CPU实现/恢复控制与thinking末段及nonthinking加载/生成重叠，模型墙钟不能作速度比较。本轮不执行模型动作、不追加旧v9–v15探针或新组合模型调用。
