# 家具面接口的真实Sim执行资格

40模拟秒、init2、seed115，固定参考人在饮品场景先将Wine提供到Cab，再请求Plate到同一已占用家具面；没有空位时保留拒绝，不选择替代目标。Robot由明确的reference_scheduler_hold保持，Human和Robot神经调用均为0，不计动态人／机器人协作或正式样本。

使用独立新入口`run_fixture_joint_activity.py`，神经模式复用有限文本／真实失败反馈，参考模式明确不使用人NN。新柜顶区域沿用真实碰撞面和原命名目标，解算空位或拒绝；不会挪动Wine、改放Plate到别处或改变Robot关节。独立审计根据声明协议重建接受点、拒绝及源物理帧；旧运行仍按原协议核对，不追溯改写。

运行前选择单卡有足够空闲显存的GPU1，仅渲染／物理资格。8767现有π服务只连接读取公开metadata，不发任何infer请求，不能改变当前点心运行的采样流。若出现实际VLA调用，本资格不按预定条件认证。现有GPU0／2／3实验保持原设置。

固定条件启动命令为`bash scripts/run_fixture_surface_qualification.sh`。保存完整真实Sim视频、实际动作、对象／Robot状态、拒绝回执及provenance。完成后检查800控制步／801视频帧、Wine保留在Cab、Plate未被强制压入；输入／执行／视频核查通过后才发布报告。失败全部保留，不自动重试。

这是执行接口资格，不能证明新神经伙伴会合理处理拒绝、实际任务得到重组、路径／全身安全或六类情境覆盖。之后仍需三活动完整生成式闭环、可执行更新分支和同版多条件评测。正式样本0。

## 实际结果与原导出失败

原40秒运行完成800控制与801帧，在报告导出时因固定参考类缺少finish_targets失败。原failure.json及日志保留，原provenance未生成；不重跑、不补造旧设置。`inspect_saved_fixture_qualification.py`只检查保存轨迹、实际零神经调用、家具面回执及完整视频，结果是saved_trace_and_video_checks_passed，不是标准interaction_verification。

实际两次放置均接受：Wine先位于柜顶边缘，Plate随后仍有安全点，最终均留在不同柜顶位置。原预期的“无空位拒绝”没有发生，不能按配置名计拒绝覆盖。真实中央占位帧的拒绝只在CPU重建／测试中验证，尚需完整神经反馈行为。

原失败暴露固定参考导出接口遗漏，现已为未来入口补齐finish_targets及接受后完成状态，增加两项参考状态回归测试。没有重新执行本条原条件。诊断视频及限制见[index.html](index.html)。真实模型、动态人及正式样本仍为0。
