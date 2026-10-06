# 动态人类执行反馈与协调关系

[打开报告](index.html)。本批以当前物理状态替代人的固定“机器人正在放碗”输入，并增加实际身体/手部/
推物进展。Qwen自行生成多步计划、当前动作与等待条件，运行时只执行本次动作；
不会沿着模型计划自动切换策略。observe可以中断动作，模型文字经历不是执行证明。

三种协调关系：并行移动接收盘、先准备盘子再放置、分别整理共享空间中的邻近物体。
合作/主动表达两个合成倾向；task2/init0/seed41，每片段20秒，独立episode记忆。
这些是同布局、小样本系统行为实测，不是完整任务多样性、人格效度或算法排名。
前两个移动盘子片段暴露物体名/区域名混淆，保留为旧接口诊断；在这两个片段完成后
增加动作拒绝反馈与双方公开分工，后四个片段使用新接口。不是固定配置六条件比较。

启动前检查单卡显存；脚本本身也核对显存并按PCI绑定EGL。

```bash
bash scripts/run_native_libero_server.sh
bash scripts/run_native_dynamic_suite.sh
```

每个条件结果在数据盘`results/continuous_v2/native_dynamic_feedback/<family>_<persona>`，
通过仓库软链接访问。每条保存真实Sim视频、双相机、完整模型动作、人的模型输入输出、
实际执行反馈和控制记录。动态伙伴片段复用此前中国源权重与本地资产。
本轮另从直连中国ModelScope获取OpenVLA-LIBERO模型，16个文件、约15.1GB，逐文件SHA256核验。

后四个条件实际使用`scripts/run_native_coordination_tasks.sh`启动。完成后对每个条件运行：

```bash
PYTHONPATH=src .venv-vc-pilot/bin/python scripts/verify_native_libero_run.py --input-dir results/continuous_v2/native_dynamic_feedback/moving_receptacle_cooperative
PYTHONPATH=src .venv-vc-pilot/bin/python scripts/verify_native_avatar.py --input-dir results/continuous_v2/native_dynamic_feedback/moving_receptacle_cooperative
PYTHONPATH=src .venv-vc-pilot/bin/python scripts/verify_native_dynamic_feedback.py --input-dir results/continuous_v2/native_dynamic_feedback/moving_receptacle_cooperative
```

对另外五个条件同样执行后，`python experiments/native_dynamic_feedback/build_report.py`生成报告。
视频下方决策与实测反馈随播放同步，保留成功/失败与资格状态。人体仍为运动学蒙皮，
实际操作是受力指尖代理；人使用理想坐标，推理时暂停模拟时间。

参考COOPERA的[论文对应官方仓库](https://github.com/dannymcy/coopera_code)和
[固定版本人类意图、任务与历史反思代码](https://github.com/dannymcy/habitat-lab/blob/d837540/coopera_main/human_sim/human_sim.py)。
目前未复现其跨日框架、Big5建模和人类效度，完整研究目标仍未完成。

## 物理完成与第二种机器人架构

旧几何判据给出一条8.5秒原始共同成功，但独立接触审计发现末帧仍夹持碗。
原始分数保持，不把它升级为物理完成；另外的运动/显示资格通过不能证明物体已经释放。
`scripts/verify_native_placement.py`保存旧片段的接触诊断，不能事后从缺失的几何时间序列证明完成。

当前原生入口默认`--completion-criterion released_stable`：公开On关系成立，实际接收盘接触，
无夹爪接触且开度至少40mm，物体和接收盘均低于0.08m/s持续0.2秒。
单独`native_released_collaboration`真实模型运行保存逐控制步`placement_evidence.jsonl`，
独立重建该物理判据。这只改变评估/终止条件，不改变模型输出或替它释放物体。

`native_openvla_reference`是真实第二种模型的接入诊断：220次推理、11秒Sim，原始任务未完成。
只使用外部相机与语言，兼容的腕部和末端状态不进入模型。
尚未匹配官方默认0.9面积中心裁剪，不作为算法/HRC比较；报告单独说明这一限制。
官方代码固定在`c8f03f48af692657d3060c19588038c7220e9af9`，隔离依赖位于数据盘，
严格载入无缺失/意外/形状不匹配，使用SDPA，不改已有Qwen/π0.5环境。
