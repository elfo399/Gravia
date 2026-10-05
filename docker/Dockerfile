FROM node:22-bookworm-slim AS frontend-tools
RUN npm install -g pnpm@10.11.0
WORKDIR /frontend

FROM frontend-tools AS frontend-build
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim-bookworm AS backend-tools
WORKDIR /app
COPY backend/ ./
RUN pip install --no-cache-dir -c requirements.lock '.[dev]'

FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
COPY backend/ ./
RUN pip install --no-cache-dir -c requirements.lock . && mkdir -p /data /frontend/dist
COPY --from=frontend-build /frontend/dist /frontend/dist
ENV GRAVIA_FRONTEND_DIRECTORY=/frontend/dist
EXPOSE 8080
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8080"]
