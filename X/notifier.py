"""
X Buzz Notifier - Gmail通知・スプレッドシート出力
バズポスト検出時にメール通知とスプシへの自動記録を行う
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

# パス設定
SCRIPT_DIR = Path(__file__).parent
SNS_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SNS_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from config import DATA_DIR, LOGS_DIR

# ログ設定
logger = logging.getLogger(__name__)

# 通知先メール
NOTIFY_EMAIL = "tonoduka@h-bb.jp"


def create_buzz_email_html(
    buzz_posts: List[Dict],
    timestamp: Optional[str] = None
) -> str:
    """
    バズポスト検出メールのHTML本文を生成

    Args:
        buzz_posts: バズポストのリスト
        timestamp: タイムスタンプ
    """
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    # ポストをいいね数でソート
    sorted_posts = sorted(buzz_posts, key=lambda x: x.get('likes', 0), reverse=True)

    # ポストリストのHTML生成
    posts_html = ""
    for i, post in enumerate(sorted_posts[:10], 1):  # 上位10件
        username = post.get('author_username', 'N/A')
        content = post.get('content', '')[:200]  # 200文字まで
        content_escaped = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        likes = post.get('likes', 0)
        retweets = post.get('retweets', 0)
        views = post.get('views', 0)
        post_url = post.get('post_url', '')
        buzz_score = post.get('buzz_score', 0)
        reason = post.get('reason', '')

        posts_html += f"""
<div class="post-card">
    <div class="post-header">
        <span class="rank">#{i}</span>
        <span class="username">@{username}</span>
        <span class="buzz-score">🔥 {buzz_score:.1f}x</span>
    </div>
    <div class="post-content">{content_escaped}...</div>
    <div class="post-stats">
        <span>❤️ {likes:,}</span>
        <span>🔄 {retweets:,}</span>
        <span>👁️ {views:,}</span>
    </div>
    <div class="post-reason">{reason}</div>
    <div class="post-link">
        <a href="{post_url}" class="view-button">▶️ 元ポストを見る</a>
    </div>
</div>
"""

    # カテゴリ別集計
    category_stats = {}
    for post in buzz_posts:
        cat = post.get('category', 'その他')
        if cat not in category_stats:
            category_stats[cat] = {'count': 0, 'total_likes': 0}
        category_stats[cat]['count'] += 1
        category_stats[cat]['total_likes'] += post.get('likes', 0)

    category_html = ""
    for cat, stats in sorted(category_stats.items(), key=lambda x: x[1]['total_likes'], reverse=True):
        category_html += f"<tr><td>{cat}</td><td>{stats['count']}件</td><td>{stats['total_likes']:,}</td></tr>"

    html = f"""<html>
<head>
<style>
body {{ font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif; line-height: 1.8; color: #333; max-width: 800px; margin: 0 auto; }}
.header {{ background: linear-gradient(135deg, #1DA1F2 0%, #0077B5 100%); color: white; padding: 20px; border-radius: 10px; }}
.header h1 {{ margin: 0; }}
.summary {{ background: #e8f5fe; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #1DA1F2; }}
.post-card {{ background: #fff; border: 1px solid #e1e8ed; border-radius: 12px; padding: 15px; margin: 15px 0; }}
.post-header {{ display: flex; align-items: center; margin-bottom: 10px; }}
.rank {{ font-size: 24px; font-weight: bold; color: #1DA1F2; margin-right: 10px; }}
.username {{ font-weight: bold; color: #14171a; flex: 1; }}
.buzz-score {{ background: #ff6b6b; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; }}
.post-content {{ color: #14171a; margin: 10px 0; white-space: pre-wrap; }}
.post-stats {{ color: #657786; font-size: 14px; }}
.post-stats span {{ margin-right: 15px; }}
.post-reason {{ font-size: 12px; color: #657786; margin-top: 5px; background: #f5f8fa; padding: 5px 10px; border-radius: 4px; }}
.post-link {{ margin-top: 10px; }}
.view-button {{ display: inline-block; background: #1DA1F2; color: white !important; padding: 8px 16px; border-radius: 20px; text-decoration: none; font-size: 14px; }}
.category-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
.category-table th, .category-table td {{ border: 1px solid #e1e8ed; padding: 10px; text-align: left; }}
.category-table th {{ background: #f5f8fa; }}
.footer {{ background: #f5f8fa; padding: 15px; margin-top: 20px; border-radius: 8px; font-size: 12px; color: #657786; }}
</style>
</head>
<body>

<div class="header">
    <h1>🐦 Xバズポスト検出レポート</h1>
    <p>{timestamp} - 自動監視システムより</p>
</div>

<div class="summary">
    <h2>📊 サマリー</h2>
    <p><strong>検出数:</strong> {len(buzz_posts)}件</p>
    <p><strong>総いいね数:</strong> {sum(p.get('likes', 0) for p in buzz_posts):,}</p>

    <h3>カテゴリ別</h3>
    <table class="category-table">
        <tr><th>カテゴリ</th><th>件数</th><th>総いいね</th></tr>
        {category_html}
    </table>
</div>

<h2>🔥 バズポスト TOP10</h2>
{posts_html}

<div class="footer">
    <p>このメールはX Buzz Auto Monitorによって自動送信されました。</p>
    <p>監視設定: accounts.json | ログ: logs/auto_monitor.log</p>
</div>

</body>
</html>"""

    return html


class BuzzNotifier:
    """
    バズポスト通知システム

    機能:
    1. Gmail通知: バズ検出時にメール送信
    2. スプレッドシート出力: バズポストを自動記録
    3. ローカルキャッシュ: 送信失敗時のフォールバック
    """

    def __init__(self, notify_email: str = NOTIFY_EMAIL):
        self.notify_email = notify_email
        self.cache_dir = DATA_DIR / "notification_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # スプレッドシートID（環境変数または設定ファイルから）
        self.spreadsheet_id = os.getenv("X_BUZZ_SPREADSHEET_ID", "")

        # MCP経由のGmail/Sheets API利用フラグ
        self.use_mcp = True

    def send_gmail_notification(self, buzz_posts: List[Dict]) -> Dict[str, Any]:
        """
        Gmailでバズ検出通知を送信
        MCP (Google Calendar/Drive) 経由でGmail APIを使用
        """
        if not buzz_posts:
            return {"skipped": "no buzz posts"}

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        subject = f"[X Buzz] {len(buzz_posts)}件のバズポスト検出 - {timestamp}"
        html_body = create_buzz_email_html(buzz_posts, timestamp)

        # キャッシュに保存（フォールバック用）
        cache_file = self.cache_dir / f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        cache_data = {
            "to": self.notify_email,
            "subject": subject,
            "body_html": html_body,
            "buzz_count": len(buzz_posts),
            "timestamp": timestamp,
            "sent": False
        }
        cache_file.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2))

        # MCP経由でGmail送信を試みる
        try:
            # _shared/google_notifier.py を使用
            from _shared.google_notifier import GoogleNotifier

            notifier = GoogleNotifier()
            result = notifier.send_email(
                to=self.notify_email,
                subject=subject,
                body=html_body,
                html=True
            )

            if result.get("success"):
                cache_data["sent"] = True
                cache_file.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2))
                logger.info(f"📧 Email sent to {self.notify_email}")
                return {"success": True, "method": "google_api", "message_id": result.get("message_id")}

        except ImportError:
            logger.warning("google_notifier not available, trying MCP fallback")
        except Exception as e:
            logger.error(f"Gmail send error: {e}")

        # フォールバック: ローカル保存のみ
        logger.info(f"📁 Email cached to: {cache_file}")
        return {"cached": True, "file": str(cache_file)}

    def log_to_spreadsheet(self, buzz_posts: List[Dict]) -> Dict[str, Any]:
        """
        バズポストをスプレッドシートに記録
        MCP (Google Sheets) 経由で出力
        """
        if not buzz_posts:
            return {"skipped": "no buzz posts"}

        timestamp = datetime.now().isoformat()

        # スプシ用のデータ整形
        rows = []
        for post in buzz_posts:
            row = [
                timestamp,
                post.get('author_username', ''),
                post.get('content', '')[:200],
                post.get('likes', 0),
                post.get('retweets', 0),
                post.get('views', 0),
                post.get('buzz_score', 0),
                post.get('reason', ''),
                post.get('post_url', ''),
                post.get('category', ''),
            ]
            rows.append(row)

        # ローカルキャッシュに保存
        cache_file = self.cache_dir / f"sheets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        cache_data = {
            "timestamp": timestamp,
            "rows": rows,
            "synced": False
        }
        cache_file.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2))

        # MCP経由でスプシ更新を試みる
        if self.spreadsheet_id:
            try:
                # Claude Code の MCP tools を使用
                # これは実行時にClaude Code CLIから呼び出される想定
                logger.info(f"📊 {len(rows)} rows prepared for spreadsheet")
                return {
                    "prepared": True,
                    "rows": len(rows),
                    "spreadsheet_id": self.spreadsheet_id,
                    "cache_file": str(cache_file)
                }
            except Exception as e:
                logger.error(f"Spreadsheet error: {e}")

        logger.info(f"📁 Spreadsheet data cached to: {cache_file}")
        return {"cached": True, "file": str(cache_file), "rows": len(rows)}

    def notify(self, buzz_posts: List[Dict]) -> Dict[str, Any]:
        """
        バズポストを通知（メール + スプシ）
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "buzz_count": len(buzz_posts)
        }

        # Gmail通知
        email_result = self.send_gmail_notification(buzz_posts)
        results["email"] = email_result

        # スプシ出力
        sheets_result = self.log_to_spreadsheet(buzz_posts)
        results["spreadsheet"] = sheets_result

        return results

    def get_pending_notifications(self) -> List[Dict]:
        """未送信の通知を取得"""
        pending = []
        for f in self.cache_dir.glob("email_*.json"):
            try:
                data = json.loads(f.read_text())
                if not data.get("sent", False):
                    pending.append({"file": str(f), **data})
            except:
                pass
        return pending

    def retry_pending(self) -> Dict[str, Any]:
        """未送信の通知を再送信"""
        pending = self.get_pending_notifications()
        results = {"total": len(pending), "sent": 0, "failed": 0}

        for item in pending:
            try:
                from _shared.google_notifier import GoogleNotifier
                notifier = GoogleNotifier()
                result = notifier.send_email(
                    to=item["to"],
                    subject=item["subject"],
                    body=item["body_html"],
                    html=True
                )

                if result.get("success"):
                    # キャッシュを更新
                    cache_file = Path(item["file"])
                    data = json.loads(cache_file.read_text())
                    data["sent"] = True
                    cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                    results["sent"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Retry failed: {e}")
                results["failed"] += 1

        return results


# CLIエントリーポイント
def main():
    import argparse

    parser = argparse.ArgumentParser(description="X Buzz Notifier")
    parser.add_argument("command", choices=["test", "pending", "retry"],
                       help="test: テスト送信, pending: 未送信一覧, retry: 再送信")
    parser.add_argument("--email", default=NOTIFY_EMAIL, help="通知先メール")

    args = parser.parse_args()

    notifier = BuzzNotifier(notify_email=args.email)

    if args.command == "test":
        # テストデータでメール送信テスト
        test_posts = [
            {
                "author_username": "test_user",
                "content": "これはテストポストです。バズ検出システムのテストです。",
                "likes": 10000,
                "retweets": 500,
                "views": 100000,
                "buzz_score": 5.5,
                "reason": "いいね10,000件",
                "post_url": "https://x.com/test/status/123",
                "category": "tech"
            }
        ]

        print("📧 Sending test notification...")
        result = notifier.notify(test_posts)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "pending":
        pending = notifier.get_pending_notifications()
        if pending:
            print(f"📋 未送信通知: {len(pending)}件")
            for item in pending:
                print(f"  - {item['timestamp']}: {item['subject']}")
        else:
            print("✅ 未送信の通知はありません")

    elif args.command == "retry":
        print("🔄 未送信通知を再送信中...")
        result = notifier.retry_pending()
        print(f"結果: {result['sent']}/{result['total']} 件送信成功")


if __name__ == "__main__":
    main()
