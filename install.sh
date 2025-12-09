#!/bin/bash
# SNS A2A Agents - macOS常時起動インストーラー

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  SNS A2A Agents インストーラー${NC}"
echo -e "${GREEN}========================================${NC}"

# ログディレクトリ作成
mkdir -p "$SCRIPT_DIR/logs"

# Python依存関係インストール
echo -e "${YELLOW}依存関係をインストール中...${NC}"
pip3 install -q -r "$SCRIPT_DIR/_shared/requirements.txt"

# LaunchAgentsディレクトリ作成
mkdir -p "$LAUNCHD_DIR"

# plistファイルをコピー
echo -e "${YELLOW}LaunchAgentsを設定中...${NC}"

for plist in "$SCRIPT_DIR/launchd/"*.plist; do
    if [ -f "$plist" ]; then
        filename=$(basename "$plist")

        # 既存のサービスを停止
        launchctl unload "$LAUNCHD_DIR/$filename" 2>/dev/null || true

        # コピー
        cp "$plist" "$LAUNCHD_DIR/"

        # 起動
        launchctl load "$LAUNCHD_DIR/$filename"

        echo -e "  ✓ $filename"
    fi
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  インストール完了！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "サービス状態確認:"
echo "  launchctl list | grep com.markx.a2a"
echo ""
echo "ログ確認:"
echo "  tail -f $SCRIPT_DIR/logs/orchestrator.log"
echo ""
echo "アンインストール:"
echo "  ./uninstall.sh"
