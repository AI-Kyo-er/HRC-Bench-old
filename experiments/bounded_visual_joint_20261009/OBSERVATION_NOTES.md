# 同版视觉系统：实际行为记录

当前只有运行前条件，尚无新Sim结果；重要结果待完整输入／控制／视频核验后发布。本文不以原理想测量或旧版视觉轨迹作为本方法证据。

## 运行前服务与环境核对

已有视觉服务环境`.venv-qwen3-v14`为Transformers4.57.1，Qwen3VL类可导入；不能使用当前OpenPI的4.53.2环境代替它。GPU3先加载独立8768 π，再加载8783视觉服务，均实际返回metadata。视觉身份为Qwen3VLForConditionalGeneration／neural_visual_skill_bank_coordination，task_scores_available=False；π身份为pi05_libero／7D libero_osc_delta。未发送实际推理请求，尚无新Robot动作。

服务PID分别2838940／2840043，GPU3合计约25.7GiB使用、22.7GiB空闲；GPU2仍有约48.5GiB空闲，GPU0／1原批继续。启动前nvidia-smi及服务间余量检查已执行，未下载新资产或修改运行环境。385项回归通过、2项跳过，初始报告0视频／16链接浏览器通过；这些不计实验完成或动态协作成绩。
