# 第四轮更强本地模型基础参照

本轮先建立更强同系列本地模型的基础动作/进度参照，再决定是否值得做连续物理诊断。40条已有冻结原始输入直接复制，不改system、用户消息、菜单、评分集合：v3.1单动作16条；v3.2多物品full_history12条、公开进度辅助12条。旧3B对应15/16、4/12、6/12，仅作描述参照，不宣称重新复现或模型规模单因素因果。

推理前门槛固定为单动作16/16且多物品full_history12/12。辅助view不替代裸完整历史门槛。通过也只是小集工程检查，不是统计能力或结构组合证明；未通过先分类诊断，不扩formal、不改冻结提示追高分。

## 模型与下载状态

官方[Qwen2.5-14B-Instruct固定版本](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct/tree/cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8)，revision `cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8`，8个BF16分片共29,540,134,000bytes（约27.51GiB）。规格与官方config在 `results/model_scale_v4/model_spec.json`。通过用户clashon后启动唯一snapshot下载句柄61969；权重在 `/data1/sieniwgroup/sieniw/HRC-Bench/models/Qwen2.5-14B-Instruct`，项目模型链接访问，HF缓存同在数据盘。不读取HF token，不调用外部推理API。

本次提交时下载仍在进行，**14B尚未加载、40次更强模型基础推理尚未执行，没有更强模型成绩或实测显存峰值**。61969保持正常运行，不因观察超时重启。`download_rate_samples.json`记录实测90.86秒增加115,343,360bytes，约1.21MiB/s；采样时累计954,204,160bytes，线性剩余时间估计可能数小时，不是下载完成保证。最终receipt只在全部分片下载、大小和官方LFS SHA逐文件核验后生成，不能用部分文件提前推理。

## 单卡资源前检与适配器

旧输入最长1153 tokens，14B配置48层、8 KV heads，短上下文KV约0.22GiB。前检要求官方BF16权重字节数再加3GiB用于KV、prefill、CUDA上下文及裕量，约31,244MiB free。最初GPU2 free32,298MiB足够该估计；后续已降为30,412MiB，说明启动前必须重查，不能沿用早期快照。若单卡无法满足则另立7B模型版本，不自动量化、分卡或CPUoffload。

新 `ConfigurableLocalModel`继承原真实BF16/greedy预测实现，保留推理路径并覆盖旧metadata中硬编码GPU3；记录真实模型ID/revision/参数数/精度/路径/物理GPU和logical cuda0。模型加载只接收本地文件，保持torch2.6.0+cu124、transformers4.49.0。GPU前检保存UTC时间与free/required值，只有唯一CUDA_VISIBLE_DEVICES且显存足够才加载。

```bash
# 已在运行的61969不用再次启动download。
# 下载完成并核验receipt、重查显存后再执行：
nvidia-smi --query-gpu=index,memory.free --format=csv
CUDA_VISIBLE_DEVICES=2 .venv-llm/bin/python -m experiments.model_scale_v4.run evaluate
```

`cases/freeze.json`已冻结40条原始messages、评分、旧3B描述结果、模型规格、源代码/旧文件校验和预定门槛。默认结果在 `raw/basic`，非空时拒绝覆盖；每调用存盘。后台下载可用同句柄61969续接，日志在 `raw/download.log`，不能假报完成。

19项永久测试已通过，包含40输入数量和原评分、只改锚定一行、显存不足拒绝及模型/GPU元数据。当前冻结原system仍含具体green/right示例；其独立事后敏感性诊断见 `experiments/interface_anchor_v4/README.md`，不用于修改本轮14B原prompt。
