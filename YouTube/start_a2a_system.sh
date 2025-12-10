#!/bin/bash
# A2A統合システム起動スクリプト
# Master Coordinator + 全Phase エージェント

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# オプション解析
WITH_SCHEDULER=false
MASTER_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-scheduler)
            WITH_SCHEDULER=true
            shift
            ;;
        --master-only)
            MASTER_ONLY=true
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
echo "🚀 Starting A2A Integrated System"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ==========================================
# Master Coordinator (8099)
# ==========================================
echo ""
echo "━━━ Master Coordinator ━━━"
if [ "$WITH_SCHEDULER" = true ]; then
    echo "🎬 Starting Master Coordinator on port 8099 (with scheduler)..."
    python agents/master_coordinator/server.py --port 8099 --with-scheduler > logs/master_coordinator.log 2>&1 &
else
    echo "🎬 Starting Master Coordinator on port 8099..."
    python agents/master_coordinator/server.py --port 8099 > logs/master_coordinator.log 2>&1 &
fi
echo $! > logs/master_coordinator.pid
sleep 2

if [ "$MASTER_ONLY" = true ]; then
    echo ""
    echo "✅ Master Coordinator started (master-only mode)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
fi

# ==========================================
# Phase 1: Data Collection Agents
# ==========================================
echo ""
echo "━━━ Phase 1: Data Collection ━━━"

echo "👀 Starting Channel Monitor Agent on port 8110..."
python agents/channel_monitor/server.py > logs/channel_monitor.log 2>&1 &
echo $! > logs/channel_monitor.pid
sleep 1

echo "📹 Starting Video Collector Agent on port 8111..."
python agents/video_collector/server.py > logs/video_collector.log 2>&1 &
echo $! > logs/video_collector.pid
sleep 1

echo "📊 Starting Trend Analyzer Agent on port 8112..."
python agents/trend_analyzer/server.py > logs/trend_analyzer.log 2>&1 &
echo $! > logs/trend_analyzer.pid
sleep 1

echo "📈 Starting Self Analyzer Agent on port 8114..."
python agents/self_analyzer/server.py > logs/self_analyzer.log 2>&1 &
echo $! > logs/self_analyzer.pid
sleep 1

echo "📊 Starting Marketing Analytics Agent on port 8115..."
python agents/marketing_analytics/server.py > logs/marketing_analytics.log 2>&1 &
echo $! > logs/marketing_analytics.pid
sleep 1

echo "🎨 Starting Style Learner Agent on port 8116..."
python agents/style_learner/server.py > logs/style_learner.log 2>&1 &
echo $! > logs/style_learner.pid
sleep 1

# ==========================================
# Phase 2: Script Generation Agents
# ==========================================
echo ""
echo "━━━ Phase 2: Script Generation ━━━"

echo "🔍 Starting Research Agent on port 8101..."
python agents/research/server.py > logs/research.log 2>&1 &
echo $! > logs/research.pid
sleep 1

echo "🪝 Starting Hook Agent on port 8102..."
python agents/hook/server.py > logs/hook.log 2>&1 &
echo $! > logs/hook.pid
sleep 1

echo "💡 Starting Concept Agent on port 8103..."
python agents/concept/server.py > logs/concept.log 2>&1 &
echo $! > logs/concept.pid
sleep 1

echo "✍️ Starting Script Writer Agent on port 8113..."
python agents/script_writer/server.py > logs/script_writer.log 2>&1 &
echo $! > logs/script_writer.pid
sleep 1

# ==========================================
# Phase 3-4: Review & Improve Agents
# ==========================================
echo ""
echo "━━━ Phase 3-4: Review & Improve ━━━"

echo "📝 Starting Reviewer Agent on port 8104..."
python agents/reviewer/server.py > logs/reviewer.log 2>&1 &
echo $! > logs/reviewer.pid
sleep 1

echo "🔧 Starting Improver Agent on port 8105..."
python agents/improver/server.py > logs/improver.log 2>&1 &
echo $! > logs/improver.pid
sleep 1

# ==========================================
# 起動確認
# ==========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ A2A System Started!"
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│  Master Coordinator: http://localhost:8099                  │"
echo "├─────────────────────────────────────────────────────────────┤"
echo "│  Phase 1: Data Collection                                   │"
echo "│    - channel_monitor:     http://localhost:8110             │"
echo "│    - video_collector:     http://localhost:8111             │"
echo "│    - trend_analyzer:      http://localhost:8112             │"
echo "│    - self_analyzer:       http://localhost:8114             │"
echo "│    - marketing_analytics: http://localhost:8115             │"
echo "│    - style_learner:       http://localhost:8116             │"
echo "├─────────────────────────────────────────────────────────────┤"
echo "│  Phase 2: Script Generation                                 │"
echo "│    - research:            http://localhost:8101             │"
echo "│    - hook:                http://localhost:8102             │"
echo "│    - concept:             http://localhost:8103             │"
echo "│    - script_writer:       http://localhost:8113             │"
echo "├─────────────────────────────────────────────────────────────┤"
echo "│  Phase 3-4: Review & Improve                                │"
echo "│    - reviewer:            http://localhost:8104             │"
echo "│    - improver:            http://localhost:8105             │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "Usage:"
echo "  # システム状態確認"
echo "  curl http://localhost:8099/status"
echo ""
echo "  # バズチェック（手動）"
echo "  curl -X POST http://localhost:8099/trigger/buzz-check"
echo ""
echo "  # フルパイプライン実行"
echo "  curl -X POST http://localhost:8099/trigger/full-pipeline"
echo ""
echo "  # A2Aタスク送信"
echo "  curl -X POST http://localhost:8099/a2a/tasks/send \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"フルパイプラインを実行\"}]}}'"
echo ""
echo "Stop:"
echo "  ./stop_a2a_system.sh"
echo ""
echo "Logs:"
echo "  tail -f logs/master_coordinator.log"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
