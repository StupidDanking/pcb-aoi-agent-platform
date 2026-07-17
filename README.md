# PCB AOI Agent Platform

## 项目简介

PCB AOI Agent Platform 是一个面向印制电路板（PCB）表面缺陷检测场景的智能检测与质量评估平台。系统以 YOLOv11 为核心检测模型，结合 FastAPI 后端、Vue3 前端、PostgreSQL 数据库、MinIO 对象存储以及大模型智能问答能力，实现 PCB 缺陷图像检测、批量检测、视频检测、训练评估、模型版本管理和检测结果智能分析。

本项目面向工业质检场景，支持对 PCB 表面常见缺陷进行自动识别、可视化标注、历史追踪和辅助分析，可用于课程设计、实习项目展示、算法验证以及后续工程化扩展。

## 核心功能

### 1. PCB 缺陷智能检测

系统支持以下 PCB 表面缺陷类别：

| 类别编号 | 英文名称 | 中文含义 |
| --- | --- | --- |
| 0 | mouse_bite | 鼠咬 |
| 1 | spur | 毛刺 |
| 2 | missing_hole | 缺孔 |
| 3 | short | 短路 |
| 4 | open_circuit | 开路 |
| 5 | spurious_copper | 多余铜 |

支持的检测模式包括：

- 单张图片检测
- 多图片批量检测
- ZIP 压缩包检测
- PCB 缺陷视频检测
- 检测结果可视化标注
- 检测类别统计与置信度展示

### 2. 智能问答 Agent

平台集成 Qwen 大模型能力，支持围绕检测结果进行智能分析，例如：

- 缺陷类型解释
- 检测结果总结
- PCB 缺陷风险说明
- 质量评估建议
- 检测图片或视频的自然语言问答

智能问答模块支持上传图片、视频和 ZIP 文件，并可自动调用对应检测工具完成分析。

### 3. 模型训练与评估

平台提供 YOLOv11 模型训练与评估能力，支持：

- 自定义 epoch、batch size、image size
- GPU 训练
- 训练任务状态查询
- 训练指标可视化
- Precision、Recall、mAP50、mAP50-95 指标展示
- 训练结果导出

### 4. 模型版本管理

系统支持多模型版本管理，包括：

- 模型版本列表
- 当前启用模型切换
- 模型指标展示
- 训练曲线查看
- 混淆矩阵查看
- 不同版本模型对比

当前项目包含两个模型版本：

| 模型版本 | 说明 |
| --- | --- |
| pcb_aoi_v1.0.0 | 本地 1 epoch baseline 模型 |
| pcb_aoi_v1.1.0 | AutoDL 训练得到的 50 epoch 高性能模型 |

### 5. 历史记录管理

系统支持检测和问答历史记录管理，包括：

- 最近检测记录
- 最近对话记录
- 历史搜索
- 对话恢复
- 检测结果回看
- 历史记录删除

### 6. 权限与用户系统

平台包含基础用户认证能力，支持：

- 用户注册
- 用户登录
- JWT Token 鉴权
- 用户角色管理
- 开发者测试账号初始化

## 技术架构

```text
PCB AOI Agent Platform
├── Frontend: Vue3 + Vite + Element Plus
├── Backend: FastAPI + SQLAlchemy + Alembic
├── Database: PostgreSQL
├── Cache: Redis
├── Object Storage: MinIO
├── Detection Model: YOLOv11
├── LLM: Qwen / DashScope OpenAI Compatible API
└── Deployment: Docker Compose + Local GPU Runtime

技术栈
前端
Vue 3
Vite
Vue Router
Pinia
Element Plus
Axios
ECharts
Markdown-it
后端
Python 3.10+
FastAPI
SQLAlchemy
Alembic
Pydantic
Uvicorn
PostgreSQL
Redis
MinIO
Ultralytics YOLO
OpenAI SDK compatible client
算法与模型
YOLOv11n
PCB defect detection dataset
Object detection
Image annotation visualization
Video frame sampling detection
Model evaluation metrics

项目结构
rsod-agent-platform
├── backend
│   ├── app
│   │   ├── agent                 # 智能体工具选择与检测调用
│   │   ├── api                   # FastAPI 路由接口
│   │   ├── config                # 系统配置
│   │   ├── db                    # 数据库连接与 ORM
│   │   ├── llm                   # Qwen 大模型客户端
│   │   ├── models                # 数据库模型
│   │   ├── schemas               # Pydantic 数据结构
│   │   ├── services              # 检测、训练等核心服务
│   │   └── training              # 模型训练服务
│   ├── models                    # 已注册 YOLO 模型版本
│   │   ├── pcb_aoi_v1.0.0
│   │   └── pcb_aoi_v1.1.0
│   ├── scripts                   # 初始化脚本
│   ├── tools                     # 数据集和评估工具
│   ├── requirements.txt
│   └── main.py
├── frontend
│   ├── src
│   │   ├── api                   # 前端 API 封装
│   │   ├── components            # 通用组件
│   │   ├── layout                # 页面布局
│   │   ├── router                # 前端路由
│   │   ├── stores                # Pinia 状态管理
│   │   ├── utils                 # 工具函数
│   │   └── views                 # 页面视图
│   ├── package.json
│   └── vite.config.js
├── datasets
│   └── pcb_defect                # PCB 缺陷数据集
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md

环境要求
基础环境
Windows 10 / Windows 11
Python 3.10 或更高版本
Node.js 18 或更高版本
Docker Desktop
NVIDIA GPU 与 CUDA 环境
推荐环境
Python 3.10 / 3.12
Node.js 20+
CUDA 12.x
NVIDIA RTX 4060 Laptop GPU 或更高
PostgreSQL 15+
Redis 7+
MinIO

快速启动
1. 克隆项目
git clone <your-repository-url>
cd pcb-aoi-agent-platform
2. 启动基础服务
docker compose up -d postgres redis minio
3. 下载模型权重与示例数据集（首次）

```bash
python scripts/download_models.py
python scripts/prepare_sample_dataset.py
python scripts/check_yolo_dataset.py
```

说明：
- `download_models.py` 会检查/下载 `backend/models/*/best.pt`
- `prepare_sample_dataset.py` 会生成小型 YOLO 示例集到 `datasets/pcb_defect/`
- `data.yaml` 已使用相对路径 `path: .`，不依赖本机绝对路径

4. 配置后端环境变量

复制环境变量模板：

copy .env.example backend\.env

然后根据本地情况修改 backend/.env。

示例配置：

APP_NAME=PCB AOI Agent Platform
APP_VERSION=0.1.0
DEBUG=True

DB_HOST=localhost
DB_PORT=5432
DB_NAME=pcb_aoi_agent
DB_USER=pcb_aoi_admin
DB_PASSWORD=pcb_aoi_password

REDIS_HOST=localhost
REDIS_PORT=6379

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=pcb-aoi-images
MINIO_SECURE=False

QWEN_API_KEY=your_qwen_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus

JWT_SECRET_KEY=pcb-aoi-dev-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080

注意：.env 文件包含 API Key 和数据库密码，不应提交到 Git 仓库。

5. 安装后端依赖
cd backend
pip install -r requirements.txt
6. 初始化数据库
alembic upgrade head

如需初始化测试账号：

python scripts/init_users_roles.py

默认开发者账号：

用户名	密码	角色
limuhang	123456	developer
wanshaokun	123456	developer
zhouyuhan	123456	developer
lixiang	123456	developer
deming	123456	developer

7. 启动后端
python main.py

后端默认运行在：

http://localhost:8000

API 文档地址：

http://localhost:8000/docs
8. 安装前端依赖

新开一个终端：

cd frontend
npm install
9. 启动前端
npm run dev

前端默认运行在：

http://localhost:5173
模型文件说明

模型版本位于：

backend/models/

当前项目支持以下模型目录：

backend/models/pcb_aoi_v1.0.0
backend/models/pcb_aoi_v1.1.0

每个模型目录建议包含：

best.pt
model_meta.json
results.csv
results.png
confusion_matrix.png
confusion_matrix_normalized.png
BoxPR_curve.png
BoxF1_curve.png
BoxP_curve.png
BoxR_curve.png
args.yaml

模型切换通过后端接口维护：

GET  /api/models
GET  /api/models/active
POST /api/models/active

当前启用模型状态保存在：

backend/models/active_model.json

该文件属于本地运行状态文件，不建议提交到 Git。

数据集说明

PCB 缺陷数据集目录结构如下：

datasets/pcb_defect
├── train
│   ├── images
│   └── labels
├── val
│   ├── images
│   └── labels
├── test
│   ├── images
│   └── labels
└── data.yaml

data.yaml 示例：

path: .
train: train/images
val: val/images
test: test/images

names:
  0: mouse_bite
  1: spur
  2: missing_hole
  3: short
  4: open_circuit
  5: spurious_copper
主要接口
认证接口
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
检测接口
POST /api/detection/single
POST /api/detection/batch
POST /api/detection/zip
POST /api/detection/video
智能问答接口
POST /api/chat/stream
训练接口
POST /api/training/start
GET  /api/training/status/{task_id}
GET  /api/training/metrics/{task_id}
POST /api/training/stop/{task_id}
GET  /api/training/results/{task_id}
POST /api/training/predict
历史记录接口
GET    /api/history/recent
GET    /api/history/search
POST   /api/history/chat/session
POST   /api/history/chat/message
GET    /api/history/chat/session/{session_id}
POST   /api/history/detection/task
GET    /api/history/detection/task/{task_id}
DELETE /api/history/{record_id}
模型管理接口
GET  /api/models
GET  /api/models/active
POST /api/models/active
GET  /api/models/{version}
GET  /api/models/{version}/metrics
GET  /api/models/{version}/artifact/{filename}
前端页面
页面	路由	功能
智能问答	/chat	上传图片、视频、ZIP 并进行检测分析和大模型问答
图片检测	/detection	单图 / 批量 / ZIP / 视频检测、模型选择、结果展示与历史保存
缺陷复核	/review	确认缺陷 / 标记误检、填写备注并关联检测任务
模型训练	/training	启动训练、查看训练状态和指标
模型管理	/models	查看模型版本、切换当前检测模型
登录	/login	用户登录
注册	/register	用户注册
协作开发说明
权限说明

后端接口权限规则：

- `/api/training/*`：需要登录，且角色为 `developer` 或 `admin`
- `/api/models/*`：需要登录（切换当前模型允许普通用户，便于检测页使用）
- `/api/detection/*`、`/api/chat/*`、`/api/history/*`：需要登录

前端路由仍会按角色隐藏“模型训练 / 模型管理”菜单。
前端开发

如果只进行前端页面开发：

cd frontend
npm install
npm run dev

如果前端需要访问本地后端，请确保后端运行在：

http://localhost:8000

也可以在前端配置接口地址：

VITE_API_BASE_URL=http://localhost:8000
后端开发
cd backend
pip install -r requirements.txt
python main.py
Git 提交规范

建议提交信息采用以下格式：

feat: add model version management
fix: resolve detection service cache issue
refactor: optimize chat page layout
docs: update enterprise README
不应提交的文件

以下文件不应提交到 Git：

.env
backend/.env
frontend/.env
backend/runs/
runs/
tmp_autodl_result/
server_smoke_test-*.zip
backend/models/active_model.json
backend/models/**/last.pt
backend/yolo*.pt
*.bak

如果后续模型权重大于 GitHub 单文件限制，建议使用 Git LFS 或 GitHub Release 管理模型文件。

项目特点
面向 PCB AOI 工业质检场景
支持图片、批量、ZIP 和视频检测
支持 YOLOv11 模型训练、评估和版本管理
集成 Qwen 大模型进行智能分析
前后端分离架构，便于协作开发
支持历史记录、检测回看和对话恢复
具备进一步扩展为工业质检平台的基础
后续扩展方向
增加检测任务队列和异步调度
支持更多模型结构和模型导出格式
接入真实 AOI 设备图像流
增加企业用户、权限和审计日志
增加缺陷严重等级评估
增加报表导出功能
增加模型自动评估与自动部署流程