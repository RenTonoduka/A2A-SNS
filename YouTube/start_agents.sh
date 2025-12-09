#!/bin/bash
# YouTube A2A Agents Starter
# Phase 1 (データ収集) + Phase 2 (台本生成) エージェント起動

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎬 YouTube A2A Pipeline - Starting All Agents"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ログディレクトリ作成
mkdir -p logs

# 既存プロセスを停止
echo "Stopping existing agents..."
# Phase 1 agents
pkill -f "agents/channel_monitor/server.py" 2>/dev/null
pkill -f "agents/video_collector/server.py" 2>/dev/null
pkill -f "agents/trend_analyzer/server.py" 2>/dev/null
# Phase 2 agents
pkill -f "agents/research/server.py" 2>/dev/null
pkill -f "agents/hook/server.py" 2>/dev/null
pkill -f "agents/concept/server.py" 2>/dev/null
pkill -f "agents/reviewer/server.py" 2>/dev/null
pkill -f "agents/improver/server.py" 2>/dev/null
pkill -f "agents/coordinator/server.py" 2>/dev/null
pkill -f "agents/script_writer/server.py" 2>/dev/null
sleep 2

echo ""
echo "━━━ Phase 1: Data Collection ━━━"

# Channel Monitor Agent (8110)
echo "Starting Channel Monitor on port 8110..."
python agents/channel_monitor/server.py > logs/channel_monitor.log 2>&1 &
echo $! > logs/channel_monitor.pid

# Video Collector Agent (8111)
echo "Starting Video Collector on port 8111..."
python agents/video_collector/server.py > logs/video_collector.log 2>&1 &
echo $! > logs/video_collector.pid

# Trend Analyzer Agent (8112)
echo "Starting Trend Analyzer on port 8112..."
python agents/trend_analyzer/server.py > logs/trend_analyzer.log 2>&1 &
echo $! > logs/trend_analyzer.pid

echo ""
echo "━━━ Phase 2: Script Generation ━━━"

# Research Agent (8101)
echo "Starting Research Agent on port 8101..."
python agents/research/server.py > logs/research.log 2>&1 &
echo $! > logs/research.pid

# Hook Agent (8102)
echo "Starting Hook Agent on port 8102..."
python agents/hook/server.py > logs/hook.log 2>&1 &
echo $! > logs/hook.pid

# Concept Agent (8103)
echo "Starting Concept Agent on port 8103..."
python agents/concept/server.py > logs/concept.log 2>&1 &
echo $! > logs/concept.pid

# Reviewer Agent (8104)
echo "Starting Reviewer Agent on port 8104..."
python agents/reviewer/server.py > logs/reviewer.log 2>&1 &
echo $! > logs/reviewer.pid

# Improver Agent (8105)
echo "Starting Improver Agent on port 8105..."
python agents/improver/server.py > logs/improver.log 2>&1 &
echo $! > logs/improver.pid

# Script Writer Agent (8113) - 本編作成
echo "Starting Script Writer Agent on port 8113..."
python agents/script_writer/server.py > logs/script_writer.log 2>&1 &
echo $! > logs/script_writer.pid

# 少し待機
sleep 3

# Coordinator (8100) - 最後に起動
echo "Starting Pipeline Coordinator on port 8100..."
python agents/coordinator/server.py > logs/coordinator.log 2>&1 &
echo $! > logs/coordinator.pid

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All Agents Started"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Phase 1 - Data Collection:"
echo "  📡 Channel Monitor:  http://localhost:8110"
echo "  📹 Video Collector:  http://localhost:8111"
echo "  📊 Trend Analyzer:   http://localhost:8112"
echo ""
echo "Phase 2 - Script Generation:"
echo "  🎬 Coordinator:      http://localhost:8100"
echo "  🔍 Research:         http://localhost:8101"
echo "  🎣 Hook:             http://localhost:8102"
echo "  📝 Concept (v2.3):   http://localhost:8103"
echo "  📊 Reviewer:         http://localhost:8104"
echo "  ✨ Improver:         http://localhost:8105"
echo "  ✍️  Script Writer:    http://localhost:8113"
echo ""
echo "Commands:"
echo "  # バズ動画検出 → 台本生成"
echo "  python pipeline_runner.py buzz"
echo ""
echo "  # テーマ指定で台本生成"
echo "  python pipeline_runner.py run --theme \"AIを使った副業の始め方\""
echo ""
echo "  # 自動テーマ生成 → 台本生成"
echo "  python pipeline_runner.py auto --hint \"AI活用\""
echo ""
echo "Agent Cards:"
echo "  curl http://localhost:8100/.well-known/agent.json"
echo ""
echo "Logs:"
echo "  tail -f logs/coordinator.log"
echo "  tail -f logs/trend_analyzer.log"
echo ""
echo "Stop all:"
echo "  ./stop_agents.sh"
echo ""
