# 第四轮更强本地模型基础参照

第六轮已实际完成官方14B全部权重核验和原冻结40调用：**单动作16/16、全历史9/12、公开进度辅助12/12，预定门槛未通过**。解析错误0、输出截断0。没有改旧提示/候选/评分，未启动v5神经。真实结果见`results/model_scale_v4/basic_summary.json`，40条messages/outputs在`raw/basic/calls.json`，失败与辅助审计在`error_and_aid_audit_v6.json`。

本轮先建立更强同系列本地模型的基础动作/进度参照，再决定是否值得做连续物理诊断。40条已有冻结原始输入直接复制，不改system、用户消息、菜单、评分集合：v3.1单动作16条；v3.2多物品full_history12条、公开进度辅助12条。旧3B对应15/16、4/12、6/12，仅作描述参照，不宣称重新复现或模型规模单因素因果。

推理前门槛固定为单动作16/16且多物品full_history12/12。辅助view不替代裸完整历史门槛。通过也只是小集工程检查，不是统计能力或结构组合证明；未通过先分类诊断，不扩formal、不改冻结提示追高分。

## 模型与下载状态

官方[Qwen2.5-14B-Instruct固定版本](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct/tree/cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8)，revision `cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8`，8个BF16分片共29,540,134,000bytes（约27.51GiB）。规格与官方config在 `results/model_scale_v4/model_spec.json`。通过用户clashon后启动唯一snapshot下载句柄61969；权重在 `/data1/sieniwgroup/sieniw/HRC-Bench/models/Qwen2.5-14B-Instruct`，项目模型链接访问，HF缓存同在数据盘。不读取HF token，不调用外部推理API。

第四轮首次提交0231b7b的历史状态是下载进行中，当时尚无14B加载/成绩/显存峰值。`download_rate_samples.json`记录当时90.86秒增加115,343,360bytes，约1.21MiB/s；采样累计954,204,160bytes。之后的失败与恢复证据保留在下面补充，不能把旧running快照当作当前状态。第六轮恢复下载7241已exit0，8分片大小和官方LFS SHA均一致，`download_receipt.json`才在完整核验后产生。

## 单卡资源前检与适配器

旧输入最长1153 tokens，14B配置48层、8 KV heads，短上下文KV约0.22GiB。前检要求官方BF16权重字节数再加3GiB用于KV、prefill、CUDA上下文及裕量，约31,244MiB free。最初GPU2 free32,298MiB足够该估计；后续已降为30,412MiB，说明启动前必须重查，不能沿用早期快照。若单卡无法满足则另立7B模型版本，不自动量化、分卡或CPUoffload。

新 `ConfigurableLocalModel`继承原真实BF16/greedy预测实现，保留推理路径并覆盖旧metadata中硬编码GPU3；记录真实模型ID/revision/参数数/精度/路径/物理GPU和logical cuda0。模型加载只接收本地文件，保持torch2.6.0+cu124、transformers4.49.0。GPU前检保存UTC时间与free/required值，只有唯一CUDA_VISIBLE_DEVICES且显存足够才加载。

```bash
# 原始/恢复下载均已终止，不重复启动；复现须使用新的非空保护输出目录。
nvidia-smi --query-gpu=index,memory.free --format=csv
CUDA_VISIBLE_DEVICES=2 .venv-llm/bin/python -m experiments.model_scale_v4.run evaluate --output-dir results/model_scale_v4/raw/independent_repeat
```

`cases/freeze.json`已冻结40条原始messages、评分、旧3B描述结果、模型规格、源代码/旧文件校验和预定门槛。默认结果在 `raw/basic`，非空时拒绝覆盖；每调用存盘。原日志`raw/download.log`及恢复日志`raw/recovery_attempt_002/download.log`保持，没有覆写历史失败。

19项永久测试已通过，包含40输入数量和原评分、只改锚定一行、显存不足拒绝及模型/GPU元数据。当前冻结原system仍含具体green/right示例；其独立事后敏感性诊断见 `experiments/interface_anchor_v4/README.md`，不用于修改本轮14B原prompt。
# 本地缓存与并发下载补充

仅在用户自己的惯用models/cache目录核验，发现完整Qwen2.5-VL-7B-Instruct约15.45GiB及Qwen3-VL-8B-Instruct约16.33GiB；后者当前transformers4.49不支持，不升级环境试跑。VL7B通过独立`local_vl_v4`纯文本基线复用，不修改本目录冻结输入/代码或替换14B模型身份。本地搜索记录见`results/model_scale_v4/local_model_search.json`。

原14B下载61969保持正常，新增73855一个辅助进程最多4线程，只选尚未存在partial的官方分片5–8；同local_dir、官方固定revision、`force_download=False`，复用HF逐文件锁，原下载后续命中已完成文件。122.43秒总吞吐实测6.70MiB/s，比此前两worker测量1.21MiB/s提高5.53倍，因此按预先条件保留辅助。结果是短时间网络测量，不保证后续恒定。`helper_rate_start.json`、`helper_rate_result.json`、`helper_receipt.json`保留证据；两个活进程均未重启。14B完整权重与官方哈希全部通过前不会启动推理。

后续状态勘误：61969和73855实际均因`requests.ChunkedEncodingError / IncompleteRead`退出1，没有被代理终止；之前running回执仅表示其采样时刻状态。退出审计`download_failure_receipt.json`记录保留8,472,494,080字节、6个partial、0个完整分片及原日志SHA。本轮收到一次恢复授权后确认旧PID消失、调用clashon并核验同官方revision，使用`raw/recovery_attempt_002`独立日志恢复原2worker（7241）和仅分片5–8的4worker（2960），未删除partial、未覆写原日志。`resume_helper.py`专用于继续已有partial，与原snapshot共用文件锁和`force_download=False`；HF按incomplete字节偏移发Range请求。新状态与实测字节增长见`recovery_attempt_002_status.json`；未把旧句柄当作仍活，也不无上限自动重启。

第六轮7241与2960均exit0；推理48231也exit0。GPU2加载前free32,278MiB，高于冻结估计31,244MiB；真实14,770,033,664参数，BF16/SDPA/greedy、batch1、seed0、96新token，无量化/分卡/CPUoffload。峰值allocated30,081,220,608字节（28.02GiB），退出后GPU2 free恢复32,278MiB。torch2.6.0+cu124、transformers4.49.0，完整元数据和配置/tokenizer SHA见`execution_receipt_v6.json`。模型自带sampling字段触发HF警告，但`do_sample=False`始终固定，temperature/top_p/top_k未用于采样。

全历史三失败全部在反序菜单（正常6/6、反序3/6，仅描述，不作因果归因）：

| fixture | 原full_history选择 | 错误 | 同fixture aid选择 |
| --- | --- | --- | --- |
| after_blue_0_1 | careful_green_right | green应left，blue已在right | careful_green_left，通过 |
| after_green_0_1 | careful_green_right | green已在left且目标left，red/blue待整理 | careful_red_left，通过 |
| after_green_1_1 | assisted_green_right | green已在right，未接受协助，red/blue待整理 | careful_red_right，通过 |

三个公开输入均明确未接受green换边建议，通道清空，无已接受清道帮助；规范原始history/poses/区域/可接受集合与输出保存在失败审计。旧system的具体green/right样例、菜单顺序和语言表达仍属接口替代解释，本轮没有新增调用隔离它们，不能只凭相关归因模型规模或结构。

`public_progress_aid`仅从公开history解析初始目标/blue修正/让行与协助事件，结合公开`physical_placements`添加目标、完成、剩余、must_yield、已接受帮助及source六字段。没有读取case隐藏目标/评分集合/完成标签；12对输入验证除这一额外字段外精确相等，归约摘要一致，公开fixture区域与位姿/速度的几何检测一致。不过把目标/已完成/剩余显式提供确实是额外计算帮助，12/12不能替代9/12全历史门槛，也不称新方法。fixture是人工接口状态，不是物理轨迹。

单动作实际输出place6、assisted2、careful4、yield4，request0；16/16不代表所有动作类别都曾被触发。25项已有与新增诊断测试通过，新增只检验统一策略的历史盲性，不再重跑旧正式数据。当前停止扩大模型调用，21候选/finish仍需另立原子能力诊断，完整B历史恢复应属于研究测试而非整套门槛预筛。
