# 开发指南

## 数据库迁移

所有表结构变更必须通过 Alembic 迁移，禁止手动 ALTER TABLE。

```bash
cd backend

# 应用所有迁移
alembic upgrade head

# 生成新迁移
alembic revision --autogenerate -m "描述"

# 查看当前版本
alembic current

# 查看迁移历史
alembic history
```

### 迁移规范

- 新增字段必须 nullable 或有默认值
- 删字段分两步：先停止读写并部署，下个周期再删除
- 改字段类型走 expand-contract：加新字段 → 双写 → 回填 → 切读 → 删旧
- 每个迁移的 downgrade 必须能安全执行

## 前端构建

```bash
cd my-app

# 开发
npm run dev

# 类型检查
npx tsc --noEmit

# 生产构建（输出到 backend/dist/）
npm run build
```

## 编码约定

- **全量异步**：所有路由和服务使用 `async/await`
- **时间处理**：数据库用 `func.now()`，Python 用 `datetime.now(timezone.utc)`
- **类型安全**：前端 TypeScript strict 模式，后端 Pydantic Schema 使用 Literal 约束枚举

## 文档站开发

```bash
cd docs

# 本地预览
npm run dev

# 构建
npm run build
```
