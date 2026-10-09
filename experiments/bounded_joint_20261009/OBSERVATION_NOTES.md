# 原始行为观察

本页记录本方法自己的完整Sim行为。当前没有已核验新结果；一次离线／接口重放不计本批运行。

独立8767服务的首次准备在模型初始化阶段退出：启动PYTHONPATH未含现有OpenPI Transformers适配路径。未开始仿真实验、未产生动作；原日志`/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/bounded_pi05_8767_20261009.log`保留。核对正常8766服务的实际环境后，新增显式启动脚本继承该路径；原GPU1无残留进程，显存17MiB背景占用。不是实验失败后重新挑选样本。
