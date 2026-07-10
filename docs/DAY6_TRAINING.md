Day6 完成了 PCB AOI 数据集可视化验证、YOLOv11 模型训练和训练日志监控功能。



首先完成了 PyTorch 与 CUDA 环境检查，当前环境可以正常使用 NVIDIA GeForce RTX 4060 Laptop GPU 进行训练。随后使用 YOLOv11n 预训练模型对 PCB AOI 数据集进行迁移学习训练，成功生成 results.csv、results.png、weights/best.pt 和 weights/last.pt。



数据验证方面，新增 visualize\_annotations.py 工具，可以随机抽样生成标注可视化图和网格概览图，用于检查 YOLO 标注框位置和类别是否正确。



后端新增 TrainingService 训练服务，支持启动训练任务、维护训练状态、解析训练日志、读取 results.csv 指标以及返回模型权重路径。新增 app/api/training.py，提供训练启动、任务列表、状态查询、指标查询、停止任务和结果下载接口。



前端 TrainingPage.vue 实现了训练监控页面，支持启动 YOLOv11 训练任务、查看任务列表，并通过 ECharts 展示 loss 曲线和 mAP 曲线。

