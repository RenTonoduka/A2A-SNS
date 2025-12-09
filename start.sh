#!/bin/bash
# SNS A2A Agents 起動スクリプト

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 色付き出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  SNS A2A Agents 起動${NC}"
echo -e "${GREEN}========================================${NC}"

# 依存関係チェック
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 が見つかりません"
    exit 1
fi

if ! command -v claude &> /dev/null; then
    echo "Error: claude CLI が見つかりません"
    echo "npm install -g @anthropic-ai/claude-code でインストールしてください"
    exit 1
fi

# 仮想環境作成（なければ）
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}仮想環境を作成中...${NC}"
    python3 -m venv venv
fi

# 仮想環境有効化
source venv/bin/activate

# 依存関係インストール
echo -e "${YELLOW}依存関係をインストール中...${NC}"
pip install -q -r _shared/requirements.txt

# エージェント起動
echo -e "${GREEN}エージェントを起動中...${NC}"

# バックグラウンドで起動
python orchestrator/server.py &
PIDS[0]=$!
echo "  ✓ sns-orchestrator (PID: ${PIDS[0]}, Port: 8080)"

sleep 1

python YouTube/script-writer/server.py &
PIDS[1]=$!
echo "  ✓ youtube-script-writer (PID: ${PIDS[1]}, Port: 8081)"

python YouTube/shorts-creator/server.py &
PIDS[2]=$!
echo "  ✓ youtube-shorts-creator (PID: ${PIDS[2]}, Port: 8082)"

python YouTube/seo-optimizer/server.py &
PIDS[3]=$!
echo "  ✓ youtube-seo-optimizer (PID: ${PIDS[3]}, Port: 8083)"

python YouTube/thumbnail-planner/server.py &
PIDS[4]=$!
echo "  ✓ youtube-thumbnail-planner (PID: ${PIDS[4]}, Port: 8084)"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  全エージェント起動完了！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Orchestrator: http://localhost:8080"
echo "Agent Card:   http://localhost:8080/.well-known/agent.json"
echo ""
echo "停止するには Ctrl+C を押してください"

# 終了時にすべてのプロセスを停止
cleanup() {
    echo ""
    echo -e "${YELLOW}エージェントを停止中...${NC}"
    for pid in "${PIDS[@]}"; do
        kill $pid 2>/dev/null || true
    done
    echo -e "${GREEN}停止完了${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 待機
wait
