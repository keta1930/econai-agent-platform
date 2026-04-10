# Stage 1 — Build frontend assets
FROM node:22-slim AS frontend-build

WORKDIR /app/my-app

# Install dependencies first (layer cache)
COPY my-app/package.json my-app/package-lock.json ./
RUN npm ci

# Copy frontend source and build
COPY my-app/ ./
RUN npm run build


# Stage 2 — Production image
FROM python:3.12-slim AS production

WORKDIR /app

# Install curl for Docker healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy frontend build output from Stage 1
COPY --from=frontend-build /app/backend/dist ./dist

# Create backups directory (named volume mount point)
RUN mkdir -p /app/backups

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
