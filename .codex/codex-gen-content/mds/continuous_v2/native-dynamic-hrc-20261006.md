# 2026-10-06：原生学习模型、动态接收盘与合格联合成功

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Verification Status: UNVERIFIED（完整研究效度）；执行与视频子项已独立核查
- Version Label: native_dynamic_hrc

本轮为progress，完整goal继续active。不是成熟Benchmark完成，也不是阻塞。

## 新的重要证据

此前Genesis位置适配0/6，故不再重复同一小规模训练。复用已有本地官方OpenPI
配套LIBERO代码、资产和初始状态，切到原生MuJoCo/OSC控制，不需下载新模型或数据。
模型仍是已有中国ModelScope的lerobot/pi05-libero，严格813键结构加载。

1. `pi05_libero_native_reference`：Spatial任务0/1/2、init0、seed30、20Hz、h10、
   280步预算，3/3，29次真实调用。完成时间3.8/5.4/5.0秒。
2. `native_human_presence_reference`：加入显示人体和力驱动指尖但保持观察，3/3，
   48次真实调用。不是人与机器人能力配对贡献，只检查新增场景没有使机器人失效。
3. `native_qwen_moving_plate`：第一批Qwen合作型伙伴，18秒、三场景。
   机器人3/3，人0/3，共同0/3；54次人决定，均持续observe，108次机器人调用。
   GPU绑定已正确后完成这批；三条全部链路/运动核查通过。
4. `native_qwen_grounded_activity`：原生支持动作与较长期工作目标的接口语义校准后。
   机器人原始2/3、人原始2/3、共同1/3，87次π调用，44次Qwen决定，解析错误0。
   task0观察18次、机器人完成/人未完成；task1观察1+push17、人完成/机器人未完成；
   task2观察1+push7、双方完成，7.3秒、146动作、15次π调用/8次人决定。

成功片段：`native_qwen_grounded_activity/task_02/init_000/demo.mp4`，7.35秒。
人的指尖峰值0.615m/s、盘子峰值0.386m/s，资格通过。
保存接触证据显示机器人双指夹持、碗抬升14.36cm，末帧双指打开、手指无接触。
`physical_operation_evidence.json`是轨迹读取，不改写结果。
task1指尖峰值2.446m/s，超过0.65m/s门槛，只保留诊断，排除人的有效完成；
不放宽阈值、不重写原始结果。机器人采样末端速度均通过1.5m/s门槛。
超速窗口位于retreat，峰值时无接触；来源机制未分离。
`human_motion_diagnosis.json`保存逐物理步窗口，不能单凭该窗口归因于机器人或执行器。
最后一批运动合格2/3，合格共同成功仍为1条。

## 系统与资格

- 高层人决策来自本地Qwen3-14B，公开坐标/任务板、自身目标与生成经验进入模型。
  NativeQwenHuman使用独立原生动作语义：push/observe/清离；没有抓持与走动。
  外观是非碰撞运动学胶囊，接触指尖是XYZ关节力驱动，不是完整人体动力学。
- 人移动盘子，机器人根据实际双相机、原生8维末端状态与公开任务/人消息继续放碗。
  低层阶段是接近、下降、推进、清离，不选择人的协作意图。物体控制期不写坐标，
  不吸附、不用教师接管机器人的模型动作。
- 人任务为盘子中心到可见绿色圆点附近：XY25mm、近初始支撑高度25mm、
  速度低于0.08m/s持续0.2秒、实际指尖接触。人的私有目标/评分不进入机器人输入。
- 早期指尖校准`native_human_push_calibration`/`native_contact_human_formal`失败保留，
  暴露用placement半径与物体根节点高度替代碰撞范围的问题。原生控制使用实际碰撞
  支撑范围和桌面高度；后续实际Qwen运行显示接触任务有成功也有碰撞速度失败。
- 早期与校准后提示、场景细节、模型采样不同，不是因果消融或人格效应。
  只有一种HRC关系的三个摆放变化、单persona、单VLA、单initial-state，统计效度不足。
  同步推理暂停模拟时间；跨场景经验保留不等于世界无重置流或跨天效度。

## 单卡绑定事故及修复

GPU0 PCI23:00对应NVIDIA EGL序号1，序号0实际是GPU1。首次生成式进程590500
计算GPU0/渲染GPU1，发现后立即停止并归档为`native_qwen_interrupted_gpu_mapping`。
该批只作中断诊断，不纳入成绩。此前只用渲染的参照实际是单张GPU1，环境声明为0，
物理结果仍保留，不声称旧硬件声明已准确。

`probe_egl_devices.py`用EGL_NV_device_cuda+CUDA PCI查询，运行器依据NVML PCI选择，
并设置CUDA_DEVICE_ORDER=PCI_BUS_ID。Robosuite1.4.1的旧断言错误要求CUDA/EGL序号
相同，在隔离环境做最小修正，物理PCI验证更严格。原始文件/修正哈希保存在cache。
正确正式进程595099及601341均由nvidia-smi核查为GPU0 C+G；模型服务571444单独GPU3。

环境`.venv-libero-native`在数据盘，NumPy1.26.4、MuJoCo3.2.3、Robosuite1.4.1；
本地OpenPI Torch依赖与客户端作为后备路径。库来自清华PyPI，安装禁用代理。
首次缺accelerate及空目录重启问题发生在实验前，已修复；无新模型/数据下载。

## 报告与提交

最新主报告`experiments/native_dynamic_hrc_20261006/index.html`，12段真实视频；
两页浏览器起播、链接与375px宽度通过。旧Genesis报告18段视频继续保留。
四批共12条视频全部解码/时间轴核验，像素、原始动作和实际ctrl链路独立核查。
最早机器人参照未保存原生四元数，核查位置和有符号双指，轴角源转换有单元测试；
后续完整8维状态重建通过。最后一批执行期间六份源码无变化。

主回归124项通过/1项JAX缺依赖跳过。代码提交d51c641、7216846、b0d36c7，
报告收尾另提交。服务在汇报前停止自己启动的PID571444与HTTP进程；不杀他人任务。
COOPERA PDF未跟踪不提交，模型/结果/截图/环境均在data1。

## 下一步

保持真实模型操作参照，扩大实际动态任务关系、人类偏好与算法覆盖，建设持续世界
任务流和数据评测协议。继续改进人体外观/身体动作及接触稳定性，并校准人类行为。
胶囊显示和XYZ指尖只是本轮接口/接触代理，不能成为用户最终要求的HumanAgent。
应优先结合已有VICO人物外观/动作资产与新物理场景，建设可信的身体与手部操作，
而非只扩大这个简化代理的任务计数来宣称成熟。
不回到手写高层政策或任意加权cobalance总分，也不无期限微调同一示范/提示。
一条成功是可观看的系统效果，不能替代用户要求的完整成熟Benchmark。
