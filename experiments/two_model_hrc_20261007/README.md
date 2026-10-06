# 两种学习机器人与动态人类协作实测

[打开报告](index.html)。本阶段将第二种模型的官方图像流程对齐后，分三层实测：

1. 无人基础参照：π0.5/OpenVLA各2任务×2初始状态，严格释放稳定完成。
2. 人物在场但不行动：各1条，检查人物、标记和场景接入的影响。
3. 生成式动态伙伴：两种机器人×三类协调关系，各1条，保留全过程视频与实际结果。

三类关系分别是可同时推进的移动接收盘、先准备接收盘再放置、分别操作邻近物体。
机器人一直使用真实学习模型的原生7维动作，Qwen自主决定人的意图和计划；
计划不会由运行时自动路由。人体骨骼蒙皮仍为非碰撞运动学显示，操作为受力指尖。
本报告共16段真实Sim视频，基础参照8段收在可展开区域。

## 固定设置

基础参照task0/2、init0/1；人物/动态条件task2/init0；env seed0，20Hz，最多20秒。
合作型合成伙伴，episode记忆，Human Torch seed=seed+1000*task_id+init_id。
π0.5执行块10，OpenVLA执行块1，按模型动作形式使用；不是同等推理调用次数。
机器人采样状态未逐条件重置，所有任务不作严格配对因果比较或公开LIBERO成绩复现。
人在坐标/执行反馈条件下决策，机器人从实际相机输入决策；推理时暂停模拟时间。

模型/数据没有本轮新下载。TF CPU及依赖来自清华PyPI，隔离在项目数据盘overlay，
没有改已有π0.5或Qwen模型环境。OpenVLA图像流程使用官方固定版本
`c8f03f48af692657d3060c19588038c7220e9af9`的JPEG往返、TF Lanczos3缩放、
0.9面积中心裁剪，已与官方函数逐像素相等；每次模型真正消费的图像另存
`observation_<step>_model.png`，与原始外部/腕部帧按stem匹配，不用配对manifest。

## 运行与审计

先检查nvidia-smi，按单卡显存足够的设备启动。当前脚本固定模型GPU2/3，
参照Sim GPU1，动态Qwen/Sim GPU0；Sim通过PCI绑定正确EGL设备。

```bash
bash scripts/run_native_libero_server.sh
bash scripts/run_openvla_native_server.sh
bash scripts/run_native_protocol_references.sh
bash scripts/run_native_presence_references.sh
bash scripts/run_native_model_hrc.sh
```

输出都在数据盘`results/continuous_v2/`，由仓库软链接访问。旧输出不能覆写，
重新运行时需要选择新的结果根目录。两种服务对兼容的共同机器人接口提供原生动作；
OpenVLA只消费外部相机和语言，π0.5消费双相机和末端状态。

独立审计入口：`verify_native_libero_run.py`（像素、状态、动作与ctrl、时钟、视频），
`verify_native_placement.py`（接触、释放、稳定时间重建）、`verify_native_avatar.py`
（显示对齐与离散运动）、`verify_native_dynamic_feedback.py`（公开反馈与模型命令）。
OpenVLA还使用`verify_openvla_preprocessing.py`重建真实模型图像；CPU运行需清空CUDA_VISIBLE_DEVICES，
PYTHONPATH首项为数据盘`cache/openvla-transformers`。报告从审计产物生成，不补写成功。

```bash
python experiments/two_model_hrc_20261007/build_report.py
```

## 解释边界

无人的4/4基础参照不能推广到人物在场。尤其OpenVLA在静态人物条件失败，
其后续动态条件包含视觉/场景接入问题，不能直接判断是否理解动态人。
π0.5静态人物通过，动态条件中的语言、物体运动与人的计划又共同变化，
同样不能仅归因为某个单一因素。输入budget检查显示π0.5三个动态条件最大92/114/105 tokens，
未超过200；不能把这批失败解释为状态token被截掉。

此阶段仍是一个取放技能上的小样本系统评测。开放目标、持续世界、角色协商、
更多技能、完整手/身体接触、多人格验证与统计协议仍未完成；不合成cobalance排名。
