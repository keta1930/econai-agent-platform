# 架构说明

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn（全异步） |
| ORM | SQLAlchemy Async |
| 数据库 | PostgreSQL 17（pgvector 镜像） |
| 对象存储 | MinIO |
| 迁移 | Alembic |
| 认证 | JWT + bcrypt |
| AI | OpenAI / Anthropic 双适配器 + Tavily 搜索 |
| 前端 | React 19 + TypeScript 5.9 + Vite 8 |
| UI | shadcn/ui + Tailwind CSS 4 |

## 后端分层

```
routers/    → 路由与请求处理（thin layer）
schemas/    → Pydantic 请求/响应模型
models/     → SQLAlchemy ORM 模型
services/   → 业务逻辑
auth/       → JWT + 依赖注入
```

## 多租户模型

三级角色体系：

```
super_admin → 管理所有教师账号
    └── admin → 创建和管理自己的班级
            └── student → 通过凭证加入班级
```

数据隔离通过 `class_id` 外键实现，所有查询自动按当前用户的班级过滤。

## 数据库

8 张表，核心关系：

- `classes` — 所有业务数据的隔离边界
- `users`（三种角色）→ `submissions`、`topic_votes`、`sharing_topics`
- `tasks`（按 class_id 隔离）→ `submissions`（支持多版本提交）
- `model_configs`（按 admin_id 隔离）

## 前后端集成

- **开发**：Vite 代理 `/api` → `http://localhost:25002`
- **生产**：Dockerfile 多阶段构建 — Node.js 编译前端，Python 打包后端，最终镜像包含完整应用

## 基础设施

Docker Compose 管理所有服务：

| 服务 | 镜像 | 用途 |
|------|------|------|
| postgres | `pgvector/pgvector:pg17` | 业务数据存储 |
| minio | `minio/minio` | 文件上传 + 数据库备份 |
| web | `keta1933/econai-agent-platform` | 全栈应用 |
