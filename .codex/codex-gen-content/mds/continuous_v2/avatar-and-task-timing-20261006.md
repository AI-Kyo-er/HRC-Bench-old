# 2026-10-06：完整VICO人物、连续离返与协作时序

本轮是progress，完整goal继续active，不mark complete。

## 完成与真实结果

- 复用本地Alex Jefferson GLB：3042顶点、4152面、65关节（52有蒙皮权重）；
  贴图、idle/walk/reach资产导出MuJoCo SKN和rig.npz。内容摘要目录保证旧资产不覆盖。
  数据盘`assets/native_avatar/current`软链接指向当前导出；全部资产无新下载。
- 默认人物可视化vico_skin，身体为非碰撞骨骼蒙皮，物理操作仍为XYZ力驱动指尖。
  站姿/步行来自已有动作，伸手优先手臂，躯干有限补偿，关节变化限速。
  行走依据身体位移采样动作，连续插值，站/走过渡0.6秒；脚底接地。
  away/yield/return现在可以连续移动身体，推物时返回工作位；高层时机仍由Qwen决定。
- CPU核查蒙皮顶点与MuJoCo一致约微米级，骨骼长度不变，目标跟踪<15mm，
  步行变换连续性检查通过。首次真实渲染发现UV误翻和过度躯干折叠，已校正。
  `native_vico_skin_presence`保留作早期显示诊断（机器人3/3但外观不合格）。
- 校正后`native_vico_avatar_presence`机器人3/3，38次真实π调用，显示/物理运动3/3合格。
  对齐偏差最大2.997mm。
- `native_vico_qwen_collaboration`：18秒三场景；机器人3/3、人0/3、共同0/3，
  108次π调用、54次Qwen决定均为observe。物理和人物显示核查3/3合格。
  不将新的外观、运动库接通说成策略提升；真实人模型执行仍不可靠。
- `native_avatar_body_clearance`：脚本只给away/return，实际退离至Y0.941、返回0.600，
  8秒视频，指尖对齐2.911mm。trained_model=False，机器人no-op，纯执行器验证。
  首次落盘因numpy bool失败的临时`native_avatar_body_motion`已删除，正式片段保留。
- 新任务族`clearance_return`公开要求人退离共享区域、再回来准备盘子，机器人可以
  拿碗，但需等人回来并准备好后再放。只有新发生的合法放置获得贡献，不能事后
  retro-credit早放；这些是任务评估条件，不给模型私有成绩、不路由动作。
- 实际`native_avatar_clearance_return`：task2/init0/seed30/25秒，π50次/Qwen25次，
  away1/return1/observe23。人真正清离（1.8秒）但返回中途停止在Y0.704，未移盘；
  没有共同完成。机器人没拿碗（最大抬升约2.8e-7m），提前放置0，不能称为理解等待。
  身体/接触/视频/真实模型链路资格通过。

## 代码、验证、报告

关键代码5672ad6；新avatar/task模块及导出、执行器和真实模型入口已提交。
主回归129项通过、1项JAX依赖跳过；原生环境另3项人物几何/动作测试通过。
本次回归命令：`PYTHONPATH=src .venv-vc-pilot/bin/python -m pytest tests --ignore=tests/legacy_llm_direction -q`。
直接收集整个tests目录会因归档测试仍引用已迁移的旧模块而出现39项导入错误；
129项通过仅对应当前非归档测试，不表示归档套件通过。
显示审计`verify_native_avatar.py`检查接触点误差≤25mm、身体水平速度≤0.3m/s、
骨骼帧间位移≤80mm。旧无body_position记录使用根骨骼水平位移核查，明确来源。
它不证明自然动作、人体动力学或安全。接触指尖速度与实际ctrl另由原生模型verifier检查。
人物核查若任何片段不合格会保存failed状态并以非零状态退出。

最新报告`experiments/avatar_dynamic_hrc_20261006/index.html`，8段真实Sim视频。
两页浏览器起播、可见链接、375px宽度检查通过；截图存数据盘。
旧原生成功视频仍在上一阶段报告，不能把旧成功归因于本轮新人物。
COOPERA PDF继续未跟踪，不提交。模型服务和HTTP在汇报前停止自己启动的进程。

## 仍缺与下一步

本轮没有成熟Benchmark完成。人物外观已替换，但身体是运动学显示，手只是接触
代理；走动可能仍有脚步/姿态误差，不是人体动力学验证。更广泛的真实手部操作、
身体碰撞、多人格/多算法/多任务与统计协议仍不全。
人的目标执行严重停滞，不能不断换提示/小参数版本来回避，需要从任务目标、
实际执行反馈和COOPERA的持续意图/经历建模统筹解决，并扩展有实质协调关系的场景。
一条原生成功与人物画面改进都不能替代完整目标，goal保持active。
