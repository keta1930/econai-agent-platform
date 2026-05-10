# 快速开始

::: tip 不想自己部署？先在线试试
访问 [econai-agent.com](https://econai-agent.com)，用教师邀请码 `1FWFifvwFyMqVZ_ZIWQLSA` 注册体验。
:::

## 准备工作

你需要一台安装了 [Docker](https://docs.docker.com/get-docker/) 的服务器或电脑。不需要安装数据库、Python 或 Node.js — Docker 会帮你搞定一切。

## 第一步：下载项目

```bash
git clone https://github.com/keta1930/econai-agent-platform.git
cd econai-agent-platform
```

## 第二步：配置环境变量

```bash
cp .env.example .env
```

打开 `.env` 文件，至少修改这几项：

| 必须修改 | 为什么 |
|---------|--------|
| `SECRET_KEY` | 用于加密登录凭证，默认值不安全 |
| `POSTGRES_PASSWORD` | 数据库密码，默认值不安全 |
| `DEFAULT_ADMIN_PASSWORD` | 超级管理员密码，默认是 `changeme` |

如果需要 AI 批改功能，还需要配置 AI 模型的 API Key（可以登录后在管理界面配置）。

完整的环境变量说明请看 [环境变量参考](/guide/configuration)。

## 第三步：启动

```bash
docker compose up -d
```

等待约 30 秒，访问 `http://你的服务器IP:25002`。

::: tip 首次启动会做什么？
平台会自动创建数据库表、初始化存储空间、创建超级管理员账号。你不需要手动执行任何初始化操作。
:::

## 第四步：登录

使用超级管理员账号登录：

- **用户名**：`admin`（或你在 `.env` 中设置的 `DEFAULT_ADMIN_ID`）
- **密码**：`changeme`（或你在 `.env` 中设置的 `DEFAULT_ADMIN_PASSWORD`）

## 接下来做什么

1. **创建邀请码** — 在超级管理员页面生成邀请码，发给教师
2. **教师注册** — 教师用邀请码注册账号
3. **创建班级** — 教师登录后创建班级，把加入凭证发给学生
4. **发布作业** — 教师创建作业、设定评分标准
5. **学生提交** — 学生加入班级、提交作业、等待 AI 批改

详细的使用流程请看 [教师使用指南](/guide/for-teachers) 和 [学生使用指南](/guide/for-students)。

## 更新平台

```bash
docker compose pull   # 拉取最新镜像
docker compose up -d  # 重启
```

数据库迁移会在启动时自动执行，你不需要手动操作。
