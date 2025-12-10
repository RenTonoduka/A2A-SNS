#!/bin/bash
# A2A統合システム停止スクリプト

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛑 Stopping A2A Integrated System"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# PIDファイルからプロセスを停止
AGENTS=(
    "master_coordinator"
    "channel_monitor"
    "video_collector"
    "trend_analyzer"
    "self_analyzer"
    "marketing_analytics"
    "style_learner"
    "research"
    "hook"
    "concept"
    "script_writer"
    "reviewer"
    "improver"
)

for agent in "${AGENTS[@]}"; do
    pid_file="logs/${agent}.pid"
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Stopping $agent (PID: $pid)..."
            kill "$pid" 2>/dev/null
        fi
        rm -f "$pid_file"
    fi
done

# 残留プロセスを確認
sleep 1
remaining=$(pgrep -f "agents/.*/server.py" || true)
if [ -n "$remaining" ]; then
    echo ""
    echo "⚠️ Killing remaining processes..."
    pkill -f "agents/.*/server.py" 2>/dev/null || true
fi

echo ""
echo "✅ All A2A agents stopped."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
