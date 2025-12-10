#!/bin/bash
#
# X Buzz Auto Monitor - macOS セットアップスクリプト
#
# 使用方法:
#   ./setup-auto-monitor.sh install    # インストール
#   ./setup-auto-monitor.sh uninstall  # アンインストール
#   ./setup-auto-monitor.sh status     # ステータス確認
#   ./setup-auto-monitor.sh logs       # ログ表示
#

set -e

# 設定
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_NAME="com.markx.x-buzz-monitor.plist"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_DIR="$PROJECT_DIR/logs"

# 色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo ""
    echo "=========================================="
    echo "🔥 X Buzz Auto Monitor - Setup"
    echo "=========================================="
    echo ""
}

check_dependencies() {
    echo "📦 Checking dependencies..."

    # Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 is not installed${NC}"
        exit 1
    fi
    echo "  ✅ Python3: $(python3 --version)"

    # 必要なパッケージ
    if ! python3 -c "import playwright" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Playwright not installed. Installing...${NC}"
        pip3 install playwright
        python3 -m playwright install chromium
    fi
    echo "  ✅ Playwright installed"

    # APScheduler (optional)
    if python3 -c "import apscheduler" 2>/dev/null; then
        echo "  ✅ APScheduler installed"
    else
        echo -e "${YELLOW}⚠️  APScheduler not installed (optional)${NC}"
    fi

    echo ""
}

install() {
    print_header

    check_dependencies

    echo "📁 Creating directories..."
    mkdir -p "$LOG_DIR"
    mkdir -p "$PROJECT_DIR/data/buzz"
    mkdir -p "$HOME/Library/LaunchAgents"

    echo "📋 Installing launchd plist..."

    if [ ! -f "$PLIST_SRC" ]; then
        echo -e "${RED}❌ Plist file not found: $PLIST_SRC${NC}"
        exit 1
    fi

    # 既存のジョブを停止
    if launchctl list | grep -q "$PLIST_NAME"; then
        echo "  Stopping existing job..."
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
    fi

    # plistをコピー
    cp "$PLIST_SRC" "$PLIST_DEST"
    echo "  ✅ Copied to: $PLIST_DEST"

    # 権限設定
    chmod 644 "$PLIST_DEST"

    # ロード
    echo "🚀 Loading launchd job..."
    launchctl load "$PLIST_DEST"

    echo ""
    echo -e "${GREEN}✅ Installation complete!${NC}"
    echo ""
    echo "監視は30分ごとに自動実行されます。"
    echo ""
    echo "コマンド:"
    echo "  ステータス確認: $0 status"
    echo "  ログ表示:       $0 logs"
    echo "  アンインストール: $0 uninstall"
    echo ""
}

uninstall() {
    print_header

    echo "🛑 Stopping and unloading job..."

    if [ -f "$PLIST_DEST" ]; then
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
        rm "$PLIST_DEST"
        echo "  ✅ Removed: $PLIST_DEST"
    else
        echo "  ℹ️  Plist not found (already uninstalled?)"
    fi

    echo ""
    echo -e "${GREEN}✅ Uninstall complete!${NC}"
    echo ""
}

status() {
    print_header

    echo "📊 Launchd Job Status:"
    echo ""

    if [ -f "$PLIST_DEST" ]; then
        echo "  ✅ Plist installed: $PLIST_DEST"
    else
        echo -e "  ${RED}❌ Plist not installed${NC}"
        return
    fi

    echo ""
    if launchctl list | grep -q "com.markx.x-buzz-monitor"; then
        echo "  ✅ Job is loaded"
        echo ""
        echo "  Job info:"
        launchctl list | grep "com.markx.x-buzz-monitor" | awk '{print "    PID: " $1 "  Status: " $2}'
    else
        echo -e "  ${YELLOW}⚠️  Job is not loaded${NC}"
    fi

    echo ""
    echo "📋 Monitor Status:"
    cd "$PROJECT_DIR"
    python3 auto_monitor.py status 2>/dev/null || echo "  Unable to get monitor status"

    echo ""
    echo "📁 Log files:"
    if [ -f "$LOG_DIR/launchd_stdout.log" ]; then
        echo "  stdout: $LOG_DIR/launchd_stdout.log ($(wc -l < "$LOG_DIR/launchd_stdout.log") lines)"
    fi
    if [ -f "$LOG_DIR/launchd_stderr.log" ]; then
        echo "  stderr: $LOG_DIR/launchd_stderr.log ($(wc -l < "$LOG_DIR/launchd_stderr.log") lines)"
    fi
    if [ -f "$LOG_DIR/auto_monitor.log" ]; then
        echo "  monitor: $LOG_DIR/auto_monitor.log ($(wc -l < "$LOG_DIR/auto_monitor.log") lines)"
    fi
}

logs() {
    print_header

    echo "📜 Recent logs (last 50 lines):"
    echo ""

    if [ -f "$LOG_DIR/auto_monitor.log" ]; then
        echo "=== auto_monitor.log ==="
        tail -50 "$LOG_DIR/auto_monitor.log"
    fi

    echo ""
    if [ -f "$LOG_DIR/launchd_stderr.log" ]; then
        if [ -s "$LOG_DIR/launchd_stderr.log" ]; then
            echo "=== launchd_stderr.log (errors) ==="
            tail -20 "$LOG_DIR/launchd_stderr.log"
        fi
    fi
}

run_now() {
    print_header

    echo "🚀 Running monitor check now..."
    cd "$PROJECT_DIR"
    python3 auto_monitor.py check
}

# メイン処理
case "${1:-}" in
    install)
        install
        ;;
    uninstall)
        uninstall
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    run)
        run_now
        ;;
    *)
        echo "Usage: $0 {install|uninstall|status|logs|run}"
        echo ""
        echo "Commands:"
        echo "  install   - Install and start auto monitor"
        echo "  uninstall - Stop and remove auto monitor"
        echo "  status    - Show current status"
        echo "  logs      - Show recent logs"
        echo "  run       - Run monitor check now"
        exit 1
        ;;
esac
