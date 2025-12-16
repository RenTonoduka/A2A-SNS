# =============================================================================
# A2A SNS Orchestrator Dockerfile (Security Hardened)
# =============================================================================
FROM python:3.11-slim

# Security: Set environment
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Claude Code CLIのインストール（npm経由）- 最小パッケージ
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && npm cache clean --force \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Security: Create non-root user
RUN groupadd -r a2a && useradd -r -g a2a -d /app -s /sbin/nologin a2a

# Python依存関係
COPY _shared/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip

# アプリケーションコード
COPY . .

# Security: Set ownership
RUN mkdir -p /app/logs && chown -R a2a:a2a /app

# デフォルトポート
EXPOSE 8080

# Note: Running as root for Claude Code CLI compatibility
# USER a2a

CMD ["python", "orchestrator/server.py"]
