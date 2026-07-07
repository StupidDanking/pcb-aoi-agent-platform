# rsod-agent-platform

基于 YOLOv11 的目标检测智能体平台。

## 项目结构

```text
rsod-agent-platform/
├── backend/              # 后端服务，FastAPI
├── frontend/             # 前端服务，Vue3 + Vite
├── models/               # YOLOv11 模型文件
├── datasets/             # 数据集目录
├── docs/                 # 项目文档
├── docker-compose.yml    # Docker Compose 基础设施编排
├── .env.example          # 环境变量示例
└── README.md             # 项目说明

后端启动方式：

```bash
cd backend
python main.py

访问地址：

FastAPI Swagger：http://localhost:8000/docs
健康检查：http://localhost:8000/api/health