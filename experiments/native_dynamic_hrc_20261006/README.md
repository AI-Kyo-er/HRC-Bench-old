# 原生学习模型与动态接收盘

[打开报告](index.html)：12段真实Sim视频，分别呈现原生操作、有人体场景、
生成式观察停滞与原生动作语义校准后的联合任务。

原生机器人3/3、静态有人场景3/3。最后联合运行原始结果：机器人2/3、
人的工作2/3、共同1/3。共同成功片段运动合格；另一失败片段指尖2.446m/s，
超0.65m/s资格门槛，排除有效完成。当前是一种HRC任务族的三个摆放变化，
只测试合作型persona和一个VLA，不是完整排名或真人研究。

两个策略都是真实模型。人的指尖通过限幅力推动盘子，身体只是非碰撞显示代理。
低层运动原语负责接近/下降/推进，人的时机和目标由Qwen决定，不由评分器路由。
推理期间暂停模拟时间，异步延迟和全身运动尚未验证。

使用现有本地OpenPI/LIBERO资产与中国源权重，无新模型或数据集下载。
隔离环境位于数据盘`envs/libero-native`，仓库`.venv-libero-native`为软链接。
依赖来自清华PyPI；其他环境不改动。本地Torch和客户端依赖作为后备路径，
原生环境自身的NumPy/MuJoCo/Robosuite包优先。

安装依赖后运行`python scripts/configure_native_libero_environment.py`。
依赖列表为`experiments/continuous_v2/libero_native_requirements.txt`；注意已复用本地
Torch，安装时不应从外部服务拉取新的模型权重。

复现入口：

- 模型：`scripts/serve_pi05_libero.py`，GPU3，使用已安装Transformers overlay。
- 原生机器人：`scripts/run_native_libero_reference.sh`，GPU0。
- 动态伙伴：`scripts/run_native_qwen_collaboration.sh`，GPU0，同时加载本地Qwen3-14B。
  该脚本指向已完成运行目录；复现请通过Python入口选择新目录。
- 核查：`scripts/verify_native_libero_run.py --input-dir <结果目录>`。
- 报告：`python experiments/native_dynamic_hrc_20261006/build_report.py`。

本机NVML GPU0对应EGL序号1，两个编号不同。运行器先查询PCI映射，再导入渲染器。
隔离环境中修正Robosuite1.4.1将EGL/CUDA序号强行相等的断言；物理PCI验证保留，
原始文件和修正哈希位于`cache/libero-native/environment_receipt.json`。
每次GPU运行前重新核对单卡空闲显存，Qwen与Sim需约36GiB。

完整目标仍active。下一步应扩展实际任务、人类偏好与算法，提升身体/动作真实性
和接触鲁棒性，并建立持续世界与统计协议；不得以这里的一条成功替代完成。
