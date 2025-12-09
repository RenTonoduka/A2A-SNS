#!/bin/bash
# YouTube 自動パイプライン実行スクリプト
# チャンネルリストから優秀動画を分析し、台本を自動生成

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/auto_pipeline_$(date +%Y%m%d).log"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "🎬 YouTube Auto Pipeline - $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

# エージェントが起動しているか確認
echo "🔍 Checking agent status..." | tee -a "$LOG_FILE"
AGENT_CHECK=$(python pipeline_runner.py check 2>&1)
echo "$AGENT_CHECK" | tee -a "$LOG_FILE"

if echo "$AGENT_CHECK" | grep -q "Not Running"; then
    echo "⚠️ Some agents are not running. Starting agents..." | tee -a "$LOG_FILE"
    ./start_agents.sh >> "$LOG_FILE" 2>&1
    sleep 10
fi

# 自動パイプライン実行
echo "" | tee -a "$LOG_FILE"
echo "🚀 Starting auto pipeline..." | tee -a "$LOG_FILE"
python pipeline_runner.py auto --count 1 >> "$LOG_FILE" 2>&1

# 結果確認
echo "" | tee -a "$LOG_FILE"
echo "📁 Generated files:" | tee -a "$LOG_FILE"
ls -la "$SCRIPT_DIR/output/final/" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "✅ Auto pipeline completed at $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
