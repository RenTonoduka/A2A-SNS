#!/bin/bash
# SNS A2A Agents - アンインストーラー

LAUNCHD_DIR="$HOME/Library/LaunchAgents"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}SNS A2A Agents を停止・削除中...${NC}"

for plist in "$LAUNCHD_DIR/com.markx.a2a."*.plist; do
    if [ -f "$plist" ]; then
        filename=$(basename "$plist")
        launchctl unload "$plist" 2>/dev/null || true
        rm "$plist"
        echo "  ✓ $filename 削除"
    fi
done

echo -e "${GREEN}アンインストール完了${NC}"
