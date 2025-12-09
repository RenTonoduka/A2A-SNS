#!/bin/bash
# YouTube A2A Agents Stopper

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛑 Stopping YouTube A2A Agents"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# PIDファイルから停止（Phase 1 + Phase 2）
for agent in channel_monitor video_collector trend_analyzer coordinator research hook concept reviewer improver script_writer; do
    if [ -f "logs/${agent}.pid" ]; then
        pid=$(cat "logs/${agent}.pid")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping $agent (PID: $pid)..."
            kill "$pid"
        fi
        rm -f "logs/${agent}.pid"
    fi
done

# 念のためプロセス名でも停止
# Phase 1
pkill -f "agents/channel_monitor/server.py" 2>/dev/null
pkill -f "agents/video_collector/server.py" 2>/dev/null
pkill -f "agents/trend_analyzer/server.py" 2>/dev/null
# Phase 2
pkill -f "agents/research/server.py" 2>/dev/null
pkill -f "agents/hook/server.py" 2>/dev/null
pkill -f "agents/concept/server.py" 2>/dev/null
pkill -f "agents/reviewer/server.py" 2>/dev/null
pkill -f "agents/improver/server.py" 2>/dev/null
pkill -f "agents/coordinator/server.py" 2>/dev/null
pkill -f "agents/script_writer/server.py" 2>/dev/null

echo ""
echo "✅ All agents stopped"
