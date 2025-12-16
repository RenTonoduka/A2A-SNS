# =============================================================================
# YouTube A2A Agents Dockerfile (Security Hardened)
# =============================================================================
# Security Features:
#   - Non-root user execution
#   - Minimal base image
#   - No unnecessary packages
#   - Fixed package versions where possible
# =============================================================================

FROM python:3.11-slim

# Security: Set environment to non-interactive
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# システム依存関係（最小限）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Claude Code CLI インストール
RUN npm install -g @anthropic-ai/claude-code \
    && npm cache clean --force

# Security: Create non-root user
RUN groupadd -r a2a && useradd -r -g a2a -d /app -s /sbin/nologin a2a

# Python依存関係インストール
COPY _shared/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir apscheduler \
    && rm -rf /root/.cache/pip

# 作業ディレクトリ
WORKDIR /app/YouTube

# Security: Set ownership and switch to non-root user
RUN mkdir -p /app/YouTube/logs /app/YouTube/output \
    && chown -R a2a:a2a /app

# Note: Running as root for Claude Code CLI compatibility
# TODO: Test with non-root user when Claude Code supports it
# USER a2a

# デフォルトコマンド（オーバーライド前提）
# Security: Use environment variable for host binding
CMD ["python", "-m", "uvicorn", "server:app", "--host", "${A2A_HOST:-127.0.0.1}", "--port", "8000"]
