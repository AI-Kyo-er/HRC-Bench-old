# 完整人物与离返协作阶段

[打开最新报告](index.html)，包括8段真实Sim视频。完整人物来自已有VICO资产，
骨骼、贴图、idle/walk动作与伸手IK接入原生MuJoCo；不再使用胶囊作为默认外观。
身体仍为运动学显示、操作仍为受力指尖代理，不是完整人体或手掌动力学。

已完成：

- 校正后人物操作参照3/3；显示和实际接触点误差约3mm。
- 完整人物动态接收盘三场景：机器人3/3、人0/3、共同0/3，Qwen均持续观察。
- 退离、返回与等待任务：Qwen发出away/return，但中途observe停在Y约0.704m，
  返回与移盘未完成。机器人也未拿碗，没有提前放置；不能据此证明理解等待。
- 脚本运动检查完成退离与返回，8秒录像，单独标注为执行器验证，不计人策略成绩。

人物与物理运动资格、像素/动作/ctrl链路、完整视频/时间轴都独立检查。
本轮未下载新模型或数据集。源资产位于数据盘，转换后按内容摘要保存，旧资产保留。

入口：`scripts/export_vico_mujoco_skin.py`、`scripts/run_libero_native_reference.py`
（`--human-visualization vico_skin`）、`scripts/run_native_body_motion_demo.py`。
新任务选项`--task-family clearance_return`。该任务公开要求先退离/再返回准备盘子，
机器人放置须发生在人返回与盘子准备好之后；评分不让提前放置自动事后获得贡献。
具体行动时机来自模型，不由任务评分路由。

核查：`scripts/verify_native_avatar.py`和`scripts/verify_native_libero_run.py`。
重建报告：`python experiments/avatar_dynamic_hrc_20261006/build_report.py`。

完整目标继续active；下一阶段应解决人代理的目标执行可靠性，扩展真实协调关系
与算法覆盖，并完善手部/身体接触和持续世界，不能只扩大当前代理的计数。
