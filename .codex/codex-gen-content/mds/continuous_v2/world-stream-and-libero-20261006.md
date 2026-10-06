# 2026-10-06：真实世界活动流与仿真预训练策略接口

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Verification Status: UNVERIFIED（完整研究效度；执行链路有核查）
- Version Label: world_stream_libero_v1

上轮属于progress。本轮也有实质进展，goal继续active，成熟Benchmark仍未完成。
不要在后续长分析中重复空转；优先读当前产物并实施下一项必要工作。

## 已完成

1. 可见区域96条采集全部完成且成功，22,768帧：train22,017 / dev751。
   dataset.json与96/96完整视频核验已生成，PID430271和handle56617退出0。
   这是几何教师数据，不是学习模型表现；源码在采集期间无变化。
2. π0.5-LIBERO已实际加载与推理。中国ModelScope权重813个key/shape严格匹配，
   通过去除model.前缀接到官方OpenPI Torch模型。独立Transformers4.53.2 overlay
   位于数据盘cache/openpi-torch-transformers，复制官方transformers_replace；
   JAX环境与VC人类模型环境未改动。无额外权重下载，使用已缓存PaliGemma tokenizer。
3. 正式6秒运行：`results/continuous_v2/pi05_libero_contact_formal`，20Hz、120动作、24调用。
   输入真实双相机，状态8D=TCP位置3/轴角3/有符号双指2，动作7D=位移3/旋转3/夹爪。
   输出位移和旋转经实际IK转成关节请求，关节限速仍生效。任务未完成。
   `verify_libero_run.py`独立核查像素、末端变换、关节请求与视频，全部通过。
   policy_frame_translation=(-0.56,0,0)，TCP offset=(0,0,0.1034)；坐标/相机域匹配
   尚未充分校准，不能作为模型能力/HRC排名。初始接口序列化失败目录已清除。
4. `activity_stream.py`只初始化一次世界；任务结束或到期后发布新分工，保持
   物体、机械臂、人体、全局时钟、双方策略及伙伴经历/当前目标。新活动只清空贡献账本。
   三活动：收纳接力→红蓝留用、机器人绿色收纳→交换角色整理。

## 实际无重置运行

目录 `results/continuous_v2/physical_activity_stream_v1`，一个连续episode/视频，seed23。
位置域π0.5+cooperative Qwen3-14B，15Hz，活动预算30秒。

- 总时长86.4秒，325模型调用、1296原生动作。
- 第一活动0–26.4秒完成：human:red:tray_red、human:blue:tray_blue。
- 第二活动26.4–56.4秒未完成，仅human:blue:keep_blue。
- 第三活动56.4–86.4秒未完成，无贡献；伙伴仍保持确认blue留用的旧目标。
- 三个发布点before/after物理状态相同；只有一次世界/策略/伙伴初始化。
- 视频与像素/动作/请求链路验证通过，src运行期间无改动。
- **运动核查failed，2处red持握速度超1.5m/s门槛**，最大逐物理帧位移30.738mm，
  峰值1.844m/s。不能纳入有效排名；保留原始结果与视频做诊断。物理转换点保持
  不等于整个运动过程通过。源码没有对象吸附/控制期坐标写入，但速度异常原因未定。
- 世界连续未自动解决目标更新和可靠操作，不能宣称记忆效用或真人规律。

## 代码与资源

代码提交792bcea，新增activity_stream、CartesianVLAAdapter、LiberoTorchPolicy及运行/核查脚本。
回归测试118项通过。重要报告在 `experiments/dynamic_contact_20261006/index.html`。
本轮没有新模型/数据下载，已使用上一轮中国源资产；软件依赖来自清华PyPI。

服务收尾前应停止自己启动的进程：LIBERO PID493852/GPU2（exec95618），
位置模型PID498918/GPU3（exec40280）。活动流PID501219/exec63682已结束。
不要杀其他用户进程。COOPERA PDF仍未跟踪，不提交。

## 下一步优先项

- 用完成的96条实际数据建立可靠的学习模型操作；训练末尾mask与32维padding的
  有效动作维度需审查，低loss已有事实不能替代闭环验证。
- 对无重置流持握速度异常检查接触和执行器；保留不合格结果，不放宽门槛伪造成功。
- 明确连续活动上下文与任务描述，验证模型能及时更新当前目标；目前初始任务板
  与经验保留不保证正确理解，合成人类模型仍需校准。
- 扩展双目标区域技能、多人格、开放任务与更多活动，完成LIBERO相机/坐标/控制校准。
- 高层人策略是神经生成，人体动作仍六DOF接触手+IK/动作库代理；完整人体动力学、
  真人效度、多模型HRC能力排序仍缺证据。同步推理暂停模拟时钟。
