# rsod-agent-platform

基于 YOLOv11 的目标检测智能体平台。

本项目采用前后端分离架构：

- 后端：FastAPI + SQLAlchemy + Alembic + JWT
- 前端：Vue 3 + Vite + Element Plus + Pinia + Vue Router
- 基础设施：PostgreSQL + Redis + MinIO + Docker Compose
- 模型方向：YOLOv11 目标检测

---

## 项目结构

```text
rsod-agent-platform/
├── backend/              # 后端服务，FastAPI
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── config/       # 全局配置
│   │   ├── core/         # 安全、JWT、日志、异常处理、中间件等核心工具
│   │   ├── database/     # 数据库连接
│   │   ├── entity/       # SQLAlchemy 模型与 Pydantic Schema
│   │   ├── services/     # 业务逻辑
│   │   └── storage/      # MinIO 文件存储客户端
│   ├── alembic/          # 数据库迁移脚本
│   ├── logs/             # 后端日志目录
│   ├── tests/            # 后端 pytest 测试
│   ├── main.py           # FastAPI 入口
│   ├── pytest.ini        # pytest 配置
│   └── requirements.txt  # Python 依赖
├── frontend/             # 前端服务，Vue3 + Vite
│   ├── src/
│   │   ├── api/          # 前端 API 封装
│   │   ├── assets/       # 静态资源与全局样式
│   │   ├── components/   # 公共组件
│   │   ├── router/       # Vue Router 路由
│   │   ├── stores/       # Pinia 状态管理
│   │   ├── utils/        # Axios、Markdown、错误监控等工具
│   │   └── views/        # 页面组件
│   ├── tests/            # 前端 Vitest 测试
│   ├── vite.config.js    # Vite 配置
│   └── package.json      # 前端依赖
├── models/               # YOLOv11 模型文件
├── datasets/             # 数据集目录
├── docs/                 # 项目文档
├── docker-compose.yml    # Docker Compose 基础设施编排
├── .env.example          # 环境变量示例
├── .gitignore            # Git 忽略配置
└── README.md             # 项目说明
```

---

## Day1 完成内容

Day1 主要完成项目初始化和基础环境验证。

已完成：

- 创建 GitHub 仓库
- 初始化项目目录结构
- 创建后端 FastAPI 最小应用
- 创建前端 Vue3 + Vite 项目
- 配置基础 Docker Compose 文件
- 验证后端 `/docs` 和 `/api/health` 可访问

Day1 验证结果：

```text
FastAPI Swagger：http://localhost:8000/docs
健康检查：http://localhost:8000/api/health
```

---

## Day2 完成内容

Day2 主要完成后端项目初始化、数据库建模、基础设施和认证模块。

已完成：

- 后端目录分层：
  - `config`
  - `database`
  - `entity`
  - `storage`
  - `services`
  - `core`
  - `api`
- 编写全局配置模块 `settings.py`
- 编写数据库连接模块 `session.py`
- 定义 SQLAlchemy 数据模型
- 定义 Pydantic 请求/响应模型
- 使用 Alembic 生成并执行数据库迁移
- 启动 PostgreSQL、Redis、MinIO
- 封装 MinIO 文件存储客户端
- 实现用户注册接口
- 实现用户登录接口
- 实现 JWT Token 生成与校验
- 实现获取当前用户接口 `/api/auth/me`
- 在 Swagger 中完成注册、登录、Token 授权和当前用户验证

Day2 核心接口：

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
GET  /api/health
```

Day2 核心文件：

```text
backend/app/config/settings.py
backend/app/database/session.py
backend/app/entity/db_models.py
backend/app/entity/schemas.py
backend/app/storage/minio_client.py
backend/app/core/security.py
backend/app/services/user_service.py
backend/app/api/auth.py
backend/alembic/
backend/main.py
```

---

## Day3 完成内容

Day3 主要完成前端项目初始化、页面路由、登录注册页面和前后端联调。

已完成：

- 安装前端核心依赖：
  - Element Plus
  - Vue Router
  - Pinia
  - Axios
  - Markdown-it
  - Sass
- 配置 Vite：
  - `@` 路径别名
  - `/api` 代理到后端 `http://localhost:8000`
  - SCSS 全局变量
- 创建全局样式：
  - `variables.scss`
  - `reset.scss`
  - `global.scss`
- 封装 Axios 请求工具 `request.js`
- 封装认证 API：
  - 注册
  - 登录
  - 获取当前用户
  - 退出登录
- 创建 Pinia 用户状态管理：
  - 保存 Token
  - 保存用户名
  - 获取当前用户信息
  - 退出登录
- 配置 Vue Router：
  - `/login`
  - `/register`
  - `/dashboard`
  - `/chat`
  - `/detection`
  - `/training`
  - `/history`
- 实现路由守卫：
  - 未登录访问主页面会跳转到 `/login`
  - 已登录访问 `/login` 会跳转到 `/dashboard`
- 实现主布局组件：
  - `AppHeader`
  - `AppSidebar`
  - `MainLayout`
- 实现登录页面
- 实现注册页面
- 完成前后端联调：
  - 前端注册用户
  - 前端登录获取 Token
  - 登录后进入主页面
  - 侧边栏页面切换
  - 退出登录返回登录页

Day3 核心前端页面：

```text
/login
/register
/dashboard
/chat
/detection
/training
/history
```

Day3 核心文件：

```text
frontend/src/api/auth.js
frontend/src/utils/request.js
frontend/src/utils/markdown.js
frontend/src/stores/user.js
frontend/src/router/index.js
frontend/src/components/layout/AppHeader.vue
frontend/src/components/layout/AppSidebar.vue
frontend/src/components/layout/MainLayout.vue
frontend/src/views/LoginPage.vue
frontend/src/views/RegisterPage.vue
frontend/src/main.js
frontend/src/App.vue
frontend/vite.config.js
```

---

## Day4 完成内容

Day4 主要完成日志监控、异常处理、健康检查增强、测试框架和前后端联调验证。

已完成：

- 后端日志系统：
  - 创建 `app/core/logger.py`
  - 支持控制台日志输出
  - 支持文件日志输出 `backend/logs/app.log`
  - 支持日志文件轮转
  - 区分 `INFO`、`WARNING`、`ERROR` 等日志级别

- 后端全局异常处理：
  - 创建 `app/core/exceptions.py`
  - 统一处理 `HTTPException`
  - 统一处理请求参数校验错误
  - 统一处理未知异常
  - 异常返回统一 JSON 格式

- API 请求日志中间件：
  - 创建 `app/core/middleware.py`
  - 自动记录请求方法、路径、状态码、耗时、客户端 IP
  - 响应头增加 `X-Process-Time`

- 健康检查接口增强：
  - 创建 `app/api/health.py`
  - 实现基础健康检查 `/api/health`
  - 实现详细健康检查 `/api/health/detail`
  - 分别检查 PostgreSQL、Redis、MinIO 状态

- 前端错误监控：
  - 创建 `src/utils/errorReporter.js`
  - 捕获 JavaScript 运行时错误
  - 捕获 Promise 未处理异常
  - 捕获 Vue 组件错误
  - 捕获资源加载错误
  - 将错误记录保存到 `localStorage`

- 后端测试框架：
  - 搭建 `pytest` 测试框架
  - 创建 `backend/tests/`
  - 编写健康检查接口测试
  - 编写认证接口测试
  - 支持测试环境 SQLite 数据库

- 前端测试框架：
  - 安装并配置 Vitest
  - 创建前端测试目录
  - 编写错误监控模块测试
  - 编写 Axios 请求封装测试
  - 编写布局组件导入测试

- Docker 日志管理：
  - 掌握 `docker compose logs`
  - 可分别查看 PostgreSQL、Redis、MinIO 日志
  - 可使用 `--tail`、`--since`、`-f`、`-t` 查看日志

- 完整联调验证：
  - Docker 基础设施正常启动
  - 后端健康检查接口正常
  - 后端请求日志正常
  - 前端注册 / 登录 / 进入主界面正常
  - 前端错误监控正常
  - 后端 `pytest` 测试通过
  - 前端 `npm run test:run` 测试通过
  - 前端 `npm run build` 构建通过

Day4 新增核心接口：

```text
GET /api/health
GET /api/health/detail
```

Day4 新增核心文件：

```text
backend/app/core/logger.py
backend/app/core/exceptions.py
backend/app/core/middleware.py
backend/app/api/health.py
backend/tests/conftest.py
backend/tests/test_health.py
backend/tests/test_auth.py
frontend/src/utils/errorReporter.js
frontend/tests/
```

---

## 后端启动方式

### 1. 启动基础设施

在项目根目录执行：

```bash
docker compose up -d postgres redis minio
```

查看容器状态：

```bash
docker compose ps
```

正常应看到：

```text
postgres   Up
redis      Up
minio      Up
```

### 2. 启动后端服务

进入后端目录：

```bash
cd backend
```

激活虚拟环境：

```bash
../.venv/Scripts/activate
```

启动 FastAPI：

```bash
python main.py
```

后端访问地址：

```text
FastAPI Swagger：http://localhost:8000/docs
基础健康检查：http://localhost:8000/api/health
详细健康检查：http://localhost:8000/api/health/detail
```

---

## 前端启动方式

进入前端目录：

```bash
cd frontend
```

安装依赖：

```bash
npm install
```

启动开发服务器：

```bash
npm run dev
```

前端访问地址：

```text
前端首页：http://localhost:5173
登录页：http://localhost:5173/login
注册页：http://localhost:5173/register
数据看板：http://localhost:5173/dashboard
```

---

## 基础设施访问地址

```text
PostgreSQL：localhost:5432
Redis：localhost:6379
MinIO API：http://localhost:9000
MinIO Console：http://localhost:9001
```

MinIO 默认账号密码：

```text
minioadmin / minioadmin
```

---

## 常用接口

### 认证接口

```text
POST /api/auth/register    用户注册
POST /api/auth/login       用户登录
GET  /api/auth/me          获取当前用户
```

### 健康检查接口

```text
GET /api/health            基础健康检查
GET /api/health/detail     详细健康检查
```

---

## 测试命令

### 后端测试

进入后端目录：

```bash
cd backend
```

激活虚拟环境：

```bash
../.venv/Scripts/activate
```

运行 pytest：

```bash
python -m pytest
```

预期结果：

```text
tests/test_health.py 通过
tests/test_auth.py   通过
```

### 前端测试

进入前端目录：

```bash
cd frontend
```

运行 Vitest：

```bash
npm run test:run
```

### 前端构建

```bash
npm run build
```

构建成功后会生成：

```text
frontend/dist/
```

注意：`dist/` 是构建产物，不需要提交到 Git。

---

## 日志查看

### 后端应用日志

后端日志文件位置：

```text
backend/logs/app.log
```

查看最近日志：

```powershell
Get-Content logs/app.log -Encoding UTF8 -Tail 30
```

实时查看日志：

```powershell
Get-Content logs/app.log -Encoding UTF8 -Wait
```

### Docker 容器日志

查看所有服务日志：

```bash
docker compose logs --tail=50
```

查看 PostgreSQL 日志：

```bash
docker compose logs --tail=50 postgres
```

查看 Redis 日志：

```bash
docker compose logs --tail=50 redis
```

查看 MinIO 日志：

```bash
docker compose logs --tail=50 minio
```

实时查看日志：

```bash
docker compose logs -f
```

---

## 当前项目状态

截至 Day4，项目已经完成：

```text
后端基础架构
数据库表结构
数据库迁移
MinIO 存储客户端
JWT 用户认证
统一日志系统
全局异常处理
API 请求日志中间件
健康检查接口增强
后端 pytest 测试框架
Vue3 前端基础架构
登录 / 注册页面
前后端认证联调
主界面布局和侧边栏导航
前端错误监控
前端 Vitest 测试框架
前端构建验证
```

后续 Day5 将继续完善业务页面、检测任务、模型训练或智能体相关功能。