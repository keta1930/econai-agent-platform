# 环境变量

所有配置集中在 `.env` 文件中，参考 `.env.example`。

## 核心配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `25002` | 后端监听端口 |
| `ENV` | `development` | 环境标识（`development` / `production`） |
| `SECRET_KEY` | *(需修改)* | JWT 签名密钥，production 必须设置 |

## 数据库

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_HOST` | `localhost` | PostgreSQL 地址 |
| `DB_PORT` | `25001` | PostgreSQL 端口 |
| `POSTGRES_USER` | `postgres` | 数据库用户 |
| `POSTGRES_PASSWORD` | `postgres` | 数据库密码 |
| `POSTGRES_DB` | `homework` | 数据库名称 |

## 对象存储（MinIO）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MINIO_ENDPOINT` | `localhost:25003` | MinIO API 地址 |
| `MINIO_ROOT_USER` | `minioadmin` | MinIO 认证用户 |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO 认证密码 |
| `MINIO_BUCKET` | `homework` | 提交文件 bucket 名称 |
| `MINIO_API_PORT` | `25003` | MinIO API 端口映射 |
| `MINIO_CONSOLE_PORT` | `25004` | MinIO 控制台端口映射 |

## 初始化账号

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_ADMIN_ID` | `admin` | 超级管理员用户名 |
| `DEFAULT_ADMIN_PASSWORD` | `changeme` | 超级管理员密码 |

## AI 模型

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_MODEL_*` | — | 默认 AI 模型配置（可在管理界面动态配置） |
| `TAVILY_API_KEY` | *(空)* | Tavily 搜索 API Key（评分标准生成用） |

## 上传限制

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MAX_TEXT_SIZE` | `2MB` | 文本提交大小上限 |
| `MAX_IMAGE_SIZE` | `5MB` | 单张图片大小上限 |
| `MAX_IMAGES_PER_SUBMISSION` | `10` | 单次提交最大图片数 |
| `MAX_IMAGE_TOTAL_SIZE` | `50MB` | 单次提交图片总大小上限 |

## 备份

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BACKUP_RETENTION_DAYS` | `30` | 备份保留天数 |
