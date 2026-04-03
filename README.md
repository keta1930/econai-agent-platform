# 经济金融AI智能体设计课程平台

多租户课程作业平台：支持多班级、多管理员，教师发布任务与评分标准，学生在线提交作业（文本粘贴、文件上传、图片），系统调用可配置的大模型进行异步批改。附带课程分享投票和数据库备份管理。

## 特性

- **多租户隔离**：班级为数据边界，任务、提交、分享、模型配置均按班级隔离
- **三级角色**：超级管理员管理管理员账号，管理员管理班级，学生注册到班级
- **多类型提交**：文本粘贴（自动保存为 .md）、文本文件（.md/.txt/.json/.py/.yaml/.jsonl）、图片
- **AI 自动批改**：OpenAI / Anthropic 双适配器，Prompt 内置注入检测与安全隔离
- **AI 评分标准生成**：ReAct 架构 + Tavily 搜索，自动生成结构化评分标准
- **课程分享与投票**：学生提交分享主题、投票，管理员排期管理
- **数据库备份**：pg_dump 备份到 MinIO，支持管理端一键备份与恢复

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy Async + PostgreSQL 17 |
| 存储 | MinIO（对象存储） |
| 基础设施 | Docker Compose（PostgreSQL + MinIO） |
| 前端 | React 19 + TypeScript + Vite + shadcn/ui |
| AI | OpenAI / Anthropic 适配器 + Tavily 搜索 |

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写密钥、模型 API Key 等
```

### 2. 启动基础设施

```bash
docker compose up -d
```

启动 PostgreSQL 和 MinIO。MinIO 控制台：`http://localhost:25004`。

### 3. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port $(grep '^PORT' ../.env | cut -d= -f2)
```

首次启动自动执行数据库迁移并创建超级管理员账号（由 `.env` 中 `DEFAULT_ADMIN_ID` / `DEFAULT_ADMIN_PASSWORD` 决定）。

### 4. 启动前端

```bash
cd my-app
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，开发时通过 Vite 代理将 `/api` 转发到后端。

### 5. 生产构建

```bash
cd my-app && npm run build
```

构建结果输出到 `backend/dist/`，重启后端后由 FastAPI 同时提供 API 和前端页面。

## 使用流程

### 超级管理员

使用 `.env` 中配置的账号登录，进入超级管理员面板创建管理员账号。

### 管理员（教师）

1. **创建班级**：登录后进入班级管理页，创建课程班级
2. **维护学号名单**：在名单页添加允许注册的学号（支持批量导入）
3. **创建任务**：草稿管理页创建任务，支持 AI 生成评分标准，完善后发布
4. **配置模型**：模型管理页添加并激活 AI 批改模型
5. **查看提交**：仪表板查看提交率统计和 AI 评分结果
6. **备份管理**：一键备份数据库到 MinIO，支持恢复

### 学生

1. **注册**：使用已在名单中的学号注册，选择班级
2. **提交作业**：查看任务详情，通过文本粘贴、文件上传或图片提交
3. **查看成绩**：成绩页查看批改状态、分数和 AI 评语
4. **分享投票**：提交分享主题并为感兴趣的主题投票

## 环境变量

所有配置集中在 `.env` 文件中，参考 `.env.example`：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `PORT` | `25002` | 后端监听端口 |
| `SECRET_KEY` | *(需修改)* | JWT 签名密钥 |
| `DB_HOST` / `DB_PORT` | `localhost` / `25001` | PostgreSQL 地址 |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `postgres` / `postgres` / `homework` | PostgreSQL 认证 |
| `MINIO_ENDPOINT` | `localhost:25003` | MinIO API 地址 |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `minioadmin` / `minioadmin` | MinIO 认证 |
| `DEFAULT_ADMIN_ID` / `DEFAULT_ADMIN_PASSWORD` | `admin` / `changeme` | 首次启动创建的超级管理员 |
| `DEFAULT_MODEL_*` | DeepSeek | 默认 AI 模型配置 |
| `TAVILY_API_KEY` | *(空)* | Tavily 搜索 API Key |

> 管理员账号仅在数据库首次初始化时生效。

## 目录结构

```text
book-web/
├── docker-compose.yml          # PostgreSQL + MinIO
├── backend/
│   ├── auth/                   # JWT + 权限依赖注入
│   ├── models/                 # SQLAlchemy ORM（8 张表）
│   ├── routers/                # API 路由
│   ├── schemas/                # Pydantic 模型
│   ├── services/
│   │   ├── ai/                 # 适配器 + 共享 Prompt
│   │   ├── storage.py          # MinIO 对象存储服务
│   │   ├── backup_service.py   # pg_dump 备份与恢复
│   │   ├── criteria_generator.py
│   │   └── grading_service.py
│   ├── alembic/                # 数据库迁移
│   ├── config.py
│   ├── database.py
│   ├── init_db.py
│   ├── seed.py
│   └── main.py
├── my-app/
│   └── src/
│       ├── pages/
│       │   ├── admin/          # 管理端页面
│       │   ├── student/        # 学生端页面
│       │   ├── super-admin/    # 超级管理员页面
│       │   └── auth/           # 登录/注册
│       ├── contexts/           # Auth + Class 上下文
│       ├── api/                # API 客户端
│       └── components/         # UI 组件
└── .env.example
```
