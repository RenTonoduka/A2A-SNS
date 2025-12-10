# YouTube A2A Agents Dockerfile
FROM python:3.11-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI インストール
RUN npm install -g @anthropic-ai/claude-code

# Python依存関係インストール
COPY _shared/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir apscheduler

# 作業ディレクトリ
WORKDIR /app/YouTube

# デフォルトコマンド（オーバーライド前提）
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
