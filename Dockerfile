FROM python:3.11-slim

WORKDIR /app

# Claude Code CLIのインストール（npm経由）
RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    && npm install -g @anthropic-ai/claude-code \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係
COPY _shared/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコード
COPY . .

# PYTHONPATHを設定（_sharedモジュールを見つけられるように）
ENV PYTHONPATH=/app

# デフォルトポート
EXPOSE 8080

CMD ["python", "orchestrator/server.py"]
