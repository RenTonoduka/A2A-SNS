#!/bin/bash
# Phase 0 エージェント起動スクリプト
# データ収集・監視・分析系エージェント + 自動スケジューラ

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# オプション解析
AUTO_SCHEDULER=true
SCHEDULER_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-scheduler)
            AUTO_SCHEDULER=false
            shift
            ;;
        --scheduler-only)
            SCHEDULER_ONLY=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# ログディレクトリ作成
mkdir -p logs

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting Phase 0 Agents (Data Collection & Auto Pipeline)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$SCHEDULER_ONLY" = false ]; then
    # Channel Monitor Agent (8110)
    echo "👀 Starting Channel Monitor Agent on port 8110..."
    python agents/channel_monitor/server.py > logs/channel_monitor.log 2>&1 &
    echo $! > logs/channel_monitor.pid
    sleep 1

    # Video Collector Agent (8111)
    echo "📹 Starting Video Collector Agent on port 8111..."
    python agents/video_collector/server.py > logs/video_collector.log 2>&1 &
    echo $! > logs/video_collector.pid
    sleep 1

    # Trend Analyzer Agent (8112)
    echo "📊 Starting Trend Analyzer Agent on port 8112..."
    python agents/trend_analyzer/server.py > logs/trend_analyzer.log 2>&1 &
    echo $! > logs/trend_analyzer.pid
    sleep 1

    # Self Channel Analyzer Agent (8114)
    echo "📈 Starting Self Channel Analyzer Agent on port 8114..."
    python agents/self_analyzer/server.py > logs/self_analyzer.log 2>&1 &
    echo $! > logs/self_analyzer.pid
    sleep 1

    # Marketing Analytics Agent (8115)
    echo "📊 Starting Marketing Analytics Agent on port 8115..."
    python agents/marketing_analytics/server.py > logs/marketing_analytics.log 2>&1 &
    echo $! > logs/marketing_analytics.pid
    sleep 1

    # Style Learner Agent (8116)
    echo "🎨 Starting Style Learner Agent on port 8116..."
    python agents/style_learner/server.py > logs/style_learner.log 2>&1 &
    echo $! > logs/style_learner.pid
    sleep 1
fi

# 自動スケジューラ起動
if [ "$AUTO_SCHEDULER" = true ]; then
    echo ""
    echo "━━━ Auto Scheduler ━━━"
    echo "🤖 Starting Auto Scheduler (30min buzz check + daily pipeline)..."
    python auto_scheduler.py start > logs/scheduler.log 2>&1 &
    echo $! > logs/scheduler.pid
    sleep 2
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Phase 0 System Started!"
echo ""
echo "Active Agents:"
echo "  - Channel Monitor:       http://localhost:8110  (競合監視)"
echo "  - Video Collector:       http://localhost:8111  (バズ動画収集)"
echo "  - Trend Analyzer:        http://localhost:8112  (トレンド分析)"
echo "  - Self Channel Analyzer: http://localhost:8114  (自チャンネル分析)"
echo "  - Marketing Analytics:   http://localhost:8115  (ファネル・KPI)"
echo "  - Style Learner:         http://localhost:8116  (台本スタイル学習)"
echo ""
if [ "$AUTO_SCHEDULER" = true ]; then
echo "Auto Scheduler:"
echo "  - Buzz Monitor:   every 30 minutes"
echo "  - Daily Pipeline: 09:00 JST"
echo "  - Weekly Report:  Monday 10:00 JST"
echo ""
fi
echo "Log files:"
echo "  - Agents:    logs/*.log"
echo "  - Scheduler: logs/scheduler.log"
echo ""
echo "Commands:"
echo "  ./stop_phase0_agents.sh          # 全停止"
echo "  python auto_scheduler.py check   # バズチェック"
echo "  python auto_scheduler.py status  # スケジューラ状態"
echo "  tail -f logs/scheduler.log       # ログ監視"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
