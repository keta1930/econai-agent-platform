# 🤖 AI 作业批改平台

一个前后端分离的课程作业平台：教师发布任务与评分标准，学生在线提交 `.md` / `.txt` 作业，系统调用可配置的大模型进行异步批改，并向教师和学生分别展示提交状态、成绩与评语。

## ✨ 项目概览

- **后端**：FastAPI + SQLAlchemy + SQLite
- **前端**：Vite + React 19 + TypeScript + React Router
- **批改方式**：后台异步任务调用 OpenAI / Anthropic 兼容模型
- **用户角色**：管理员、学生
- **数据存储**：
  - 业务数据默认保存在 `backend/data.db`
  - 学生提交文件默认保存在 `backend/storage/submissions/`
  - 前端生产构建输出到 `backend/dist/`，由 FastAPI 统一托管

## 🧭 核心流程

### 管理员端

1. 初始化后自动创建默认管理员账号。
2. 在“学号名单”中维护允许注册的学生名单。
3. 在“发布任务”中创建作业标题、任务说明和打分标准。
4. 在“模型管理”中新增模型配置并激活当前用于批改的模型。
5. 在仪表板和任务详情页查看提交率、已交 / 未交学生、评分结果。

### 学生端

1. 只有在学号已进入名单后才能注册。
2. 登录后可查看任务列表和自己的成绩。
3. 在任务详情页上传 `.md` / `.txt` 作业文件。
4. 提交后系统异步批改，状态依次可能为 `pending`、`grading`、`completed`、`failed`。
5. 批改完成后可查看分数和 AI 建议。

## 🏗️ 架构与职责

### 后端 `backend/`

- `main.py`
  - 应用入口
  - 启动时创建提交目录并初始化数据库
  - 挂载 `backend/dist/` 作为前端静态资源
- `init_db.py`
  - 自动建表
  - 自动创建默认管理员
  - 自动插入默认模型配置
- `routers/`
  - `auth.py`：注册、登录
  - `roster.py`：管理员维护学号名单
  - `tasks.py`：任务创建、列表、详情、统计
  - `submissions.py`：学生提交、个人记录、管理员查看学生记录
  - `model_config.py`：模型新增与激活
- `services/grading_service.py`
  - 后台批改主流程
  - 读取作业文件、加载当前激活模型、生成评分结果并回写数据库
- `services/ai/`
  - `openai_adapter.py`：OpenAI 兼容接口
  - `anthropic_adapter.py`：Anthropic 接口
- `auth/`
  - JWT 生成与鉴权依赖

### 前端 `my-app/`

- `src/App.tsx`
  - 定义公开路由、学生路由、管理员路由
- `src/contexts/AuthContext.tsx`
  - 保存 token、角色、用户 ID
  - 自动处理 token 过期
- `src/pages/student/`
  - `TaskListPage.tsx`：任务列表
  - `TaskDetailPage.tsx`：任务详情、上传作业、查看批改结果
  - `GradesPage.tsx`：成绩汇总
- `src/pages/admin/`
  - `DashboardPage.tsx`：任务概览与提交率
  - `CreateTaskPage.tsx`：发布任务
  - `TaskDetailPage.tsx`：单任务统计
  - `RosterPage.tsx`：学号名单维护
  - `StudentDetailPage.tsx`：单个学生的提交历史
  - `ModelsPage.tsx`：模型配置与激活
- `vite.config.ts`
  - 开发环境把 `/api` 代理到 `http://localhost:8000`
  - 构建产物输出到 `../backend/dist`

## 📁 目录结构

```text
vibe-everything/
├── backend/
│   ├── auth/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   │   └── ai/
│   ├── config.py
│   ├── database.py
│   ├── init_db.py
│   ├── main.py
│   └── requirements.txt
├── my-app/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── hooks/
│   │   ├── pages/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 🚀 本地开发

### 0. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写端口、密钥、模型 API Key 等
```

`.env` 文件已加入 `.gitignore`，不会提交到仓库。

### 1. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port $(grep '^PORT' ../.env | cut -d= -f2)
```

后端端口由 `.env` 中的 `PORT` 决定（默认 `8000`）。

### 2. 启动前端

```bash
cd my-app
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，开发时通过 Vite 代理将 `/api` 转发到后端。代理目标地址在 `my-app/vite.config.ts` 中设置，需与 `PORT` 保持一致。

### 3. 生产构建

```bash
cd my-app
npm run build
```

构建结果会输出到 `backend/dist/`。此时重新启动 FastAPI 后，可由后端同时提供 API 和前端页面。

## ⚙️ 环境变量说明

所有配置集中在项目根目录的 `.env` 文件中，参考 `.env.example`：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PORT` | `8000` | 后端监听端口 |
| `SECRET_KEY` | `hw-grading-secret-key-change-in-production` | JWT 签名密钥 |
| `DATABASE_URL` | `sqlite:///./data.db` | 数据库连接串 |
| `STORAGE_DIR` | `./storage` | 文件存储目录 |
| `TOKEN_EXPIRE_HOURS` | `24` | 登录 token 有效期 |
| `DEFAULT_ADMIN_ID` | `admin` | 首次启动自动创建的管理员账号 |
| `DEFAULT_ADMIN_PASSWORD` | `changeme` | 首次启动自动创建的管理员密码 |
| `DEFAULT_MODEL_NAME` | `deepseek-chat` | 首次启动自动写入的模型名称 |
| `DEFAULT_MODEL_API_KEY` | *(空)* | 模型 API Key |
| `DEFAULT_MODEL_BASE_URL` | `https://api.deepseek.com/v1` | 模型 base URL（OpenAI 兼容接口）|
| `DEFAULT_MODEL_ADAPTER` | `openai` | 适配器类型：`openai` 或 `anthropic` |

> ⚠️ 管理员账号和模型配置仅在**数据库首次初始化时**生效。若数据库已存在，修改 `.env` 中对应变量不会覆盖已有记录。

## 🤖 模型批改机制

- 模型配置保存在 `model_configs` 表中。
- 每次只能激活一个模型。
- 当前支持两类适配器：
  - `openai`
  - `anthropic`
- 批改提示词由 `backend/services/grading_service.py` 中的 `GRADING_PROMPT_TEMPLATE` 统一生成。
- 模型需要返回 JSON：

```json
{
  "score": 92,
  "suggestion": "结构清晰，但案例分析还可以更具体。"
}
```

适配器内置了两层解析策略：

- 直接解析纯 JSON
- 从混合文本中提取 JSON 代码块

## 🔐 当前实现中的注意事项

这个仓库更接近课程内部工具或原型，直接用于生产前至少需要处理下面几项：

- 登录和注册目前没有限流、验证码、审计日志等安全措施。
- 数据库默认是 SQLite，适合单机和轻量使用，不适合高并发场景。
- 当前仓库未见自动化测试与 CI 配置。

## 🧪 适合继续演进的方向

- 为批改任务引入真正的异步队列，如 Celery / RQ
- 支持作业重提、教师重批、评分版本记录
- 增加文件大小限制、内容预览与更丰富的格式支持
- 增加测试、日志、错误监控与部署脚本

## 📌 快速判断这个项目是否适合你

如果你需要的是一个“教师发题 + 学生交作业 + 大模型自动评分”的教学原型，这个项目已经有完整主链路。如果你需要多课程、多教师、多班级、严格权限和可审计生产系统，还需要继续补安全、配置和运维能力。
