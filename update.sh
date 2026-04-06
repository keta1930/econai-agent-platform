#!/bin/bash
set -e

export PATH="/root/.local/bin:/root/.nvm/versions/node/v24.13.0/bin:$PATH"
export HOME=/root

cd /var/www/agentic-economics

echo "========== 拉取代码 =========="
git checkout -- .
git pull origin master

echo "========== 前端构建 =========="
cd my-app && npm install && npm run build
cd ..

echo "========== 后端依赖 =========="
uv pip install --python /var/www/agentic-economics/.venv/bin/python -r backend/requirements.txt

echo "========== 重启服务 =========="
systemctl restart agentic-economics

echo "更新完成: $(date)"
