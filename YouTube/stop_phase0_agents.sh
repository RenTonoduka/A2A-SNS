#!/bin/bash
# Phase 0 エージェント停止スクリプト

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🛑 Stopping Phase 0 Agents..."

# PIDファイルからプロセス停止
for agent in channel_monitor video_collector trend_analyzer self_analyzer marketing_analytics style_learner scheduler; do
    if [ -f "logs/${agent}.pid" ]; then
        PID=$(cat "logs/${agent}.pid")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            echo "  ✓ Stopped ${agent} (PID: $PID)"
        fi
        rm "logs/${agent}.pid"
    fi
done

# 残留プロセスも停止
pkill -f "agents/channel_monitor/server.py" 2>/dev/null
pkill -f "agents/video_collector/server.py" 2>/dev/null
pkill -f "agents/trend_analyzer/server.py" 2>/dev/null
pkill -f "agents/self_analyzer/server.py" 2>/dev/null
pkill -f "agents/marketing_analytics/server.py" 2>/dev/null
pkill -f "agents/style_learner/server.py" 2>/dev/null
pkill -f "auto_scheduler.py" 2>/dev/null

echo "✅ All Phase 0 agents stopped."
