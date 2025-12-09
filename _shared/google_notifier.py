"""
Google Notifier - Chat/Gmail/Calendar通知
A2Aエージェントからの通知・ログ送信用
"""

import os
import json
import base64
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

# Google API
try:
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from .google_auth import get_credentials
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# .envから読み込み
ENV_PATH = Path(__file__).parent / "config" / ".env"

def load_api_key() -> str:
    """APIキーを読み込む"""
    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                if line.startswith("GOOGLE_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return os.getenv("GOOGLE_API_KEY", "")

def load_config() -> Dict[str, str]:
    """設定を読み込む"""
    config = {}
    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    return config


class GoogleNotifier:
    """
    Google APIs を使用した通知システム
    - Chat: 自分宛てメッセージ
    - Gmail: ログメール送信
    - Calendar: イベント作成
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or load_api_key()
        self.config = load_config()
        self.base_url = "https://www.googleapis.com"

        # Google API クライアント（OAuth認証済みの場合）
        self._gmail_service = None
        self._calendar_service = None
        self._chat_service = None
        self._credentials = None

    def _get_credentials(self):
        """OAuth認証情報を取得"""
        if self._credentials is None and GOOGLE_API_AVAILABLE:
            self._credentials = get_credentials()
        return self._credentials

    def _get_gmail_service(self):
        """Gmail APIサービスを取得"""
        if self._gmail_service is None:
            creds = self._get_credentials()
            if creds:
                self._gmail_service = build('gmail', 'v1', credentials=creds)
        return self._gmail_service

    def _get_calendar_service(self):
        """Calendar APIサービスを取得"""
        if self._calendar_service is None:
            creds = self._get_credentials()
            if creds:
                self._calendar_service = build('calendar', 'v3', credentials=creds)
        return self._calendar_service

    # ============================================
    # Gmail API
    # ============================================

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> Dict[str, Any]:
        """
        Gmailでメール送信

        Args:
            to: 送信先メールアドレス
            subject: 件名
            body: 本文
            html: HTMLメールかどうか
        """
        service = self._get_gmail_service()
        if not service:
            # フォールバック: ログに記録
            self.log_to_file(f"📧 Email to {to}: {subject}\n{body}", "EMAIL", "gmail")
            return {"fallback": "logged_to_file"}

        try:
            message = MIMEText(body, 'html' if html else 'plain', 'utf-8')
            message['to'] = to
            message['subject'] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

            self.log_to_file(f"📧 Email sent to {to}: {subject}", "INFO", "gmail")
            return {"success": True, "message_id": result.get('id')}

        except Exception as e:
            self.log_to_file(f"❌ Email failed: {str(e)}", "ERROR", "gmail")
            return {"error": str(e)}

    def send_log_email(self, subject: str, body: str) -> Dict[str, Any]:
        """自分宛てにログメールを送信"""
        my_email = self.config.get("MY_EMAIL", "")
        if not my_email:
            return {"error": "MY_EMAIL not configured in .env"}
        return self.send_email(my_email, f"[A2A Log] {subject}", body)

    # ============================================
    # Calendar API
    # ============================================

    def create_event(
        self,
        title: str,
        description: str = "",
        start_time: Optional[datetime] = None,
        duration_minutes: int = 30,
        calendar_id: str = 'primary'
    ) -> Dict[str, Any]:
        """
        Googleカレンダーにイベント作成

        Args:
            title: イベントタイトル
            description: 説明
            start_time: 開始時刻（デフォルト: 現在時刻）
            duration_minutes: 所要時間（分）
            calendar_id: カレンダーID
        """
        service = self._get_calendar_service()
        if not service:
            self.log_to_file(f"📅 Event: {title}\n{description}", "CALENDAR", "calendar")
            return {"fallback": "logged_to_file"}

        try:
            if start_time is None:
                start_time = datetime.now()

            end_time = start_time + timedelta(minutes=duration_minutes)

            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
            }

            result = service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()

            self.log_to_file(f"📅 Event created: {title}", "INFO", "calendar")
            return {"success": True, "event_id": result.get('id'), "link": result.get('htmlLink')}

        except Exception as e:
            self.log_to_file(f"❌ Calendar failed: {str(e)}", "ERROR", "calendar")
            return {"error": str(e)}

    def create_reminder(
        self,
        title: str,
        minutes_from_now: int = 30
    ) -> Dict[str, Any]:
        """リマインダーイベントを作成"""
        start_time = datetime.now() + timedelta(minutes=minutes_from_now)
        return self.create_event(
            title=f"🔔 {title}",
            description="A2A Agent Reminder",
            start_time=start_time,
            duration_minutes=15
        )

    # ============================================
    # Logging to File (Always works)
    # ============================================

    def log_to_file(
        self,
        message: str,
        level: str = "INFO",
        agent_name: str = "system"
    ) -> str:
        """ローカルログファイルに記録"""
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] [{agent_name}] {message}\n"

        # 日別ログファイル
        log_file = log_dir / f"notifications_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

        return f"Logged to {log_file}"

    # ============================================
    # Agent Notification Methods
    # ============================================

    def notify_task_started(self, agent_name: str, task_id: str, task_summary: str):
        """タスク開始通知"""
        message = f"🚀 タスク開始\nAgent: {agent_name}\nID: {task_id}\n内容: {task_summary}"
        return self.log_to_file(message, "INFO", agent_name)

    def notify_task_completed(
        self,
        agent_name: str,
        task_id: str,
        result_summary: str,
        duration_seconds: float
    ):
        """タスク完了通知"""
        message = f"✅ タスク完了\nAgent: {agent_name}\nID: {task_id}\n結果: {result_summary}\n所要時間: {duration_seconds:.1f}秒"
        return self.log_to_file(message, "INFO", agent_name)

    def notify_task_failed(self, agent_name: str, task_id: str, error: str):
        """タスク失敗通知"""
        message = f"❌ タスク失敗\nAgent: {agent_name}\nID: {task_id}\nエラー: {error}"
        return self.log_to_file(message, "ERROR", agent_name)

    def notify_pipeline_status(self, phase: str, status: str, details: str = ""):
        """パイプライン状況通知"""
        message = f"📊 Pipeline Status\nPhase: {phase}\nStatus: {status}\n{details}"
        return self.log_to_file(message, "INFO", "coordinator")

    def notify_buzz_videos(
        self,
        videos: List[Dict[str, Any]],
        threshold: float = 2.0,
        send_email: bool = True
    ) -> Dict[str, Any]:
        """
        バズ動画検出時の通知

        Args:
            videos: バズ動画リスト [{"title": "", "channel": "", "views": 0, "pr": 0.0, "url": ""}]
            threshold: PRしきい値
            send_email: メール送信するか
        """
        if not videos:
            return {"status": "no_buzz_videos"}

        # ログに記録
        message = f"🔥 バズ動画検出！ {len(videos)}件 (PR >= {threshold})"
        self.log_to_file(message, "BUZZ", "trend_analyzer")

        # メール本文作成
        email_body = f"""
🔥 バズ動画を{len(videos)}件検出しました！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
検出条件: Performance Ratio >= {threshold}
検出日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        for i, v in enumerate(videos[:10], 1):  # 上位10件
            pr = v.get('pr', v.get('performance_ratio', 0))
            email_body += f"""
【{i}位】PR: {pr:.1f}x
タイトル: {v.get('title', 'N/A')}
チャンネル: {v.get('channel', v.get('channel_name', 'N/A'))}
再生数: {v.get('views', v.get('view_count', 0)):,}
URL: https://youtube.com/watch?v={v.get('video_id', '')}
"""

        email_body += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 次のアクション:
1. トランスクリプトを取得して構成を分析
2. タイトルパターンを抽出
3. 台本生成に活用

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YouTube A2A Pipeline - Phase 1
"""

        result = {"logged": True, "video_count": len(videos)}

        if send_email:
            email_result = self.send_log_email(
                f"🔥 バズ動画検出 {len(videos)}件 (PR>={threshold})",
                email_body
            )
            result["email"] = email_result

        return result

    # ============================================
    # Summary Report
    # ============================================

    def send_daily_summary(self, stats: Dict[str, Any]) -> str:
        """日次サマリーを記録"""
        summary = f"""
📈 Daily Summary - {datetime.now().strftime('%Y-%m-%d')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Tasks: {stats.get('total_tasks', 0)}
Completed: {stats.get('completed', 0)}
Failed: {stats.get('failed', 0)}
Success Rate: {stats.get('success_rate', 0):.1f}%

Top Agents:
{self._format_agent_stats(stats.get('agent_stats', {}))}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return self.log_to_file(summary, "SUMMARY", "system")

    def _format_agent_stats(self, agent_stats: Dict) -> str:
        """エージェント統計をフォーマット"""
        lines = []
        for agent, stats in agent_stats.items():
            lines.append(f"  - {agent}: {stats.get('tasks', 0)} tasks, {stats.get('success_rate', 0):.0f}% success")
        return "\n".join(lines) if lines else "  No data"


# シングルトンインスタンス
_notifier = None

def get_notifier() -> GoogleNotifier:
    """シングルトンのNotifierを取得"""
    global _notifier
    if _notifier is None:
        _notifier = GoogleNotifier()
    return _notifier


# 便利関数
def notify(message: str, level: str = "INFO", agent: str = "system"):
    """クイック通知"""
    return get_notifier().log_to_file(message, level, agent)


def notify_start(agent: str, task_id: str, summary: str):
    """タスク開始通知"""
    return get_notifier().notify_task_started(agent, task_id, summary)


def notify_complete(agent: str, task_id: str, result: str, duration: float):
    """タスク完了通知"""
    return get_notifier().notify_task_completed(agent, task_id, result, duration)


def notify_error(agent: str, task_id: str, error: str):
    """エラー通知"""
    return get_notifier().notify_task_failed(agent, task_id, error)


# Gmail送信ヘルパー
def send_log_email(subject: str, body: str):
    """自分宛てログメール送信"""
    return get_notifier().send_log_email(subject, body)


# Calendar作成ヘルパー
def create_reminder(title: str, minutes_from_now: int = 30):
    """リマインダー作成"""
    return get_notifier().create_reminder(title, minutes_from_now)


# バズ動画通知ヘルパー
def notify_buzz_videos(videos: List[Dict[str, Any]], threshold: float = 2.0):
    """バズ動画検出時にメール通知"""
    return get_notifier().notify_buzz_videos(videos, threshold, send_email=True)


# 台本完成通知（台本本文をメール本文に含める）
def notify_script_completed(
    theme: str,
    score: int,
    output_file: str,
    buzz_video: Optional[Dict[str, Any]] = None,
    include_script_content: bool = True
) -> Dict[str, Any]:
    """
    台本完成時の通知（台本全文をメール本文に含める）

    Args:
        theme: 動画テーマ
        score: 最終スコア（100点満点）
        output_file: 出力ファイルパス
        buzz_video: 参考にしたバズ動画情報（オプション）
        include_script_content: 台本内容をメールに含めるか
    """
    notifier = get_notifier()

    # ログに記録
    message = f"✅ 台本完成: {theme} (Score: {score}/100)"
    notifier.log_to_file(message, "SCRIPT", "script_writer")

    # 台本内容を読み込み
    script_content = ""
    if include_script_content and output_file:
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                script_content = f.read()
        except Exception as e:
            script_content = f"(台本ファイル読み込みエラー: {e})"

    # メール本文作成（HTML形式）
    video_url = f"https://youtube.com/watch?v={buzz_video.get('video_id', '')}" if buzz_video else ""

    email_body = f"""
<html>
<head>
<style>
body {{ font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif; line-height: 1.8; color: #333; }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; }}
.section {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #667eea; }}
.buzz-video {{ background: #fff3cd; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ffc107; }}
.script-content {{ background: #ffffff; padding: 20px; margin: 15px 0; border-radius: 8px; border: 1px solid #dee2e6; white-space: pre-wrap; font-size: 14px; }}
.footer {{ background: #e9ecef; padding: 15px; margin-top: 20px; border-radius: 8px; font-size: 12px; color: #6c757d; }}
a {{ color: #667eea; }}
h2 {{ color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 5px; }}
</style>
</head>
<body>

<div class="header">
<h1>🎬 YouTube台本完成通知</h1>
<p>AI A2A Pipelineが台本を生成しました</p>
</div>

<div class="section">
<h2>📋 基本情報</h2>
<table>
<tr><td><strong>テーマ:</strong></td><td>{theme}</td></tr>
<tr><td><strong>最終スコア:</strong></td><td>{score}/100点</td></tr>
<tr><td><strong>完成日時:</strong></td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
</table>
</div>
"""

    if buzz_video:
        pr = buzz_video.get('performance_ratio', buzz_video.get('pr', 0))
        email_body += f"""
<div class="buzz-video">
<h2>🔥 参考バズ動画</h2>
<table>
<tr><td><strong>タイトル:</strong></td><td>{buzz_video.get('title', 'N/A')}</td></tr>
<tr><td><strong>チャンネル:</strong></td><td>{buzz_video.get('channel_name', buzz_video.get('channel', 'N/A'))}</td></tr>
<tr><td><strong>再生数:</strong></td><td>{buzz_video.get('view_count', buzz_video.get('views', 0)):,}回</td></tr>
<tr><td><strong>PR (Performance Ratio):</strong></td><td><strong>{pr:.1f}x</strong> (登録者比)</td></tr>
<tr><td><strong>動画URL:</strong></td><td><a href="{video_url}">{video_url}</a></td></tr>
</table>
<p>💡 この動画の構成・フック・展開を参考にして台本を生成しました</p>
</div>
"""

    if script_content:
        email_body += f"""
<h2>📝 生成された台本（全文）</h2>
<div class="script-content">
{script_content}
</div>
"""

    email_body += f"""
<div class="section">
<h2>💡 次のステップ</h2>
<ol>
<li>台本を確認・修正</li>
<li>サムネイル作成</li>
<li>撮影・編集</li>
<li>YouTubeにアップロード</li>
</ol>
</div>

<div class="footer">
<p>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</p>
<p>🤖 YouTube A2A Pipeline - Phase 2 (Script Generation)</p>
<p>このメールはAI自動生成システムから送信されました</p>
</div>

</body>
</html>
"""

    # スコアに応じた件名
    if score >= 90:
        subject = f"🎉 高品質台本完成！ {theme[:30]}... ({score}点)"
    elif score >= 70:
        subject = f"✅ 台本完成 {theme[:30]}... ({score}点)"
    else:
        subject = f"📝 台本生成完了 {theme[:30]}... (要レビュー)"

    email_result = notifier.send_email(
        to=notifier.config.get("MY_EMAIL", ""),
        subject=f"[A2A] {subject}",
        body=email_body,
        html=True
    )

    return {
        "logged": True,
        "theme": theme,
        "score": score,
        "email": email_result,
        "script_included": bool(script_content)
    }


# Google Docsに台本を作成してメール送信
def notify_script_with_google_doc(
    theme: str,
    score: int,
    output_file: str,
    buzz_video: Optional[Dict[str, Any]] = None,
    folder_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    台本をGoogle Docsに作成し、リンク付きでメール送信

    Args:
        theme: 動画テーマ
        score: 最終スコア
        output_file: ローカル台本ファイルパス
        buzz_video: 参考バズ動画情報
        folder_id: Google Drive保存先フォルダID（省略時はルート）

    Returns:
        Dict with google_doc_url, email result
    """
    notifier = get_notifier()

    # 台本内容を読み込み
    script_content = ""
    if output_file:
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                script_content = f.read()
        except Exception as e:
            script_content = f"(台本ファイル読み込みエラー: {e})"

    # Google Docs作成用のコンテンツ
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    doc_title = f"【台本】{theme[:40]} ({timestamp})"

    # バズ動画情報セクション
    buzz_section = ""
    video_url = ""
    if buzz_video:
        video_url = f"https://youtube.com/watch?v={buzz_video.get('video_id', '')}"
        pr = buzz_video.get('performance_ratio', buzz_video.get('pr', 0))
        buzz_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 参考バズ動画
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
タイトル: {buzz_video.get('title', 'N/A')}
チャンネル: {buzz_video.get('channel_name', buzz_video.get('channel', 'N/A'))}
再生数: {buzz_video.get('view_count', buzz_video.get('views', 0)):,}回
PR: {pr:.1f}x (登録者比)
URL: {video_url}

💡 この動画の構成・フック・展開を参考にしました
"""

    doc_content = f"""🎬 YouTube台本
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 基本情報
テーマ: {theme}
スコア: {score}/100点
生成日時: {timestamp}
{buzz_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 台本本文
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{script_content}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Generated by YouTube A2A Pipeline
"""

    result = {
        "logged": True,
        "theme": theme,
        "score": score,
        "google_doc_url": None,
        "email": None
    }

    # MCPでGoogle Docs作成を試行（Claude Codeから実行される場合）
    # ここではMCP呼び出し情報を返す
    mcp_instruction = f"""
## Google Docs作成（MCPで実行してください）

```
mcp__google-drive__createGoogleDoc(
    name="{doc_title}",
    content='''台本内容は上記参照''',
    parentFolderId="{folder_id or 'root'}"
)
```
"""

    # HTMLメール作成
    email_body = f"""
<html>
<head>
<style>
body {{ font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif; line-height: 1.8; color: #333; }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; }}
.section {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #667eea; }}
.buzz-video {{ background: #fff3cd; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ffc107; }}
.script-content {{ background: #ffffff; padding: 20px; margin: 15px 0; border-radius: 8px; border: 1px solid #dee2e6; white-space: pre-wrap; font-size: 14px; max-height: 600px; overflow-y: auto; }}
.footer {{ background: #e9ecef; padding: 15px; margin-top: 20px; border-radius: 8px; font-size: 12px; color: #6c757d; }}
a {{ color: #667eea; }}
h2 {{ color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 5px; }}
.cta-button {{ display: inline-block; background: #667eea; color: white !important; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 10px 5px; }}
</style>
</head>
<body>

<div class="header">
<h1>🎬 YouTube台本完成</h1>
<p>AI A2A Pipelineが台本を生成しました</p>
</div>

<div class="section">
<h2>📋 基本情報</h2>
<table>
<tr><td><strong>テーマ:</strong></td><td>{theme}</td></tr>
<tr><td><strong>最終スコア:</strong></td><td>{score}/100点</td></tr>
<tr><td><strong>完成日時:</strong></td><td>{timestamp}</td></tr>
</table>
</div>
"""

    if buzz_video:
        pr = buzz_video.get('performance_ratio', buzz_video.get('pr', 0))
        email_body += f"""
<div class="buzz-video">
<h2>🔥 参考バズ動画</h2>
<table>
<tr><td><strong>タイトル:</strong></td><td>{buzz_video.get('title', 'N/A')}</td></tr>
<tr><td><strong>チャンネル:</strong></td><td>{buzz_video.get('channel_name', buzz_video.get('channel', 'N/A'))}</td></tr>
<tr><td><strong>再生数:</strong></td><td>{buzz_video.get('view_count', buzz_video.get('views', 0)):,}回</td></tr>
<tr><td><strong>PR:</strong></td><td><strong>{pr:.1f}x</strong></td></tr>
</table>
<p><a href="{video_url}" class="cta-button">▶️ 参考動画を見る</a></p>
</div>
"""

    email_body += f"""
<h2>📝 生成された台本</h2>
<div class="script-content">
{script_content[:15000]}{'...(続きはファイルを参照)' if len(script_content) > 15000 else ''}
</div>

<div class="section">
<h2>💡 次のステップ</h2>
<ol>
<li>台本を確認・修正</li>
<li>サムネイル作成</li>
<li>撮影・編集</li>
<li>YouTubeにアップロード</li>
</ol>
</div>

<div class="footer">
<p>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</p>
<p>🤖 YouTube A2A Pipeline</p>
</div>

</body>
</html>
"""

    # スコアに応じた件名
    if score >= 90:
        subject = f"🎉 高品質台本完成！ {theme[:30]}..."
    elif score >= 70:
        subject = f"✅ 台本完成 {theme[:30]}..."
    else:
        subject = f"📝 台本生成完了 {theme[:30]}..."

    email_result = notifier.send_email(
        to=notifier.config.get("MY_EMAIL", ""),
        subject=f"[A2A] {subject}",
        body=email_body,
        html=True
    )

    result["email"] = email_result
    result["mcp_instruction"] = mcp_instruction
    result["doc_content"] = doc_content

    notifier.log_to_file(f"✅ 台本送信: {theme}", "SCRIPT", "notifier")

    return result


# パイプラインエラー通知
def notify_pipeline_error(
    phase: str,
    error: str,
    details: Optional[str] = None
) -> Dict[str, Any]:
    """
    パイプラインエラー通知

    Args:
        phase: エラーが発生したフェーズ
        error: エラーメッセージ
        details: 追加詳細（オプション）
    """
    notifier = get_notifier()

    # ログに記録
    message = f"❌ Pipeline Error [{phase}]: {error}"
    notifier.log_to_file(message, "ERROR", "pipeline")

    # メール本文作成
    email_body = f"""
❌ パイプラインでエラーが発生しました

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
フェーズ: {phase}
エラー: {error}
発生日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    if details:
        email_body += f"""
詳細:
{details}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    email_body += """
💡 対処方法:
1. ログを確認: tail -f logs/coordinator.log
2. エージェント状態確認: python pipeline_runner.py check
3. 再実行を検討

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YouTube A2A Pipeline
"""

    email_result = notifier.send_log_email(
        f"❌ Pipeline Error: {phase}",
        email_body
    )

    return {
        "logged": True,
        "phase": phase,
        "error": error,
        "email": email_result
    }


# テスト
if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("Google Notifier テスト")
    print("=" * 60)

    notifier = GoogleNotifier()

    # コマンドライン引数でテストタイプを指定
    test_type = sys.argv[1] if len(sys.argv) > 1 else "log"

    if test_type == "log":
        print("\n📝 ローカルログテスト")

        print("\n[1] タスク開始通知")
        result = notifier.notify_task_started(
            "research-agent",
            "task-001",
            "AIエージェントの競合分析"
        )
        print(f"結果: {result}")

        print("\n[2] タスク完了通知")
        result = notifier.notify_task_completed(
            "research-agent",
            "task-001",
            "競合10件分析完了",
            45.2
        )
        print(f"結果: {result}")

        print("\n[3] パイプライン状況")
        result = notifier.notify_pipeline_status(
            "Phase 2: Concept",
            "In Progress",
            "hook-agent, concept-agent 実行中"
        )
        print(f"結果: {result}")

    elif test_type == "email":
        print("\n📧 Gmail APIテスト")
        result = notifier.send_log_email(
            "A2A Pipeline テスト",
            """
こんにちは！

これはA2A Pipelineからのテストメールです。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
テスト情報:
- 時刻: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """
- エージェント: research-agent, hook-agent
- ステータス: 正常動作中
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

よろしくお願いいたします。
A2A Pipeline System
"""
        )
        print(f"結果: {result}")

    elif test_type == "calendar":
        print("\n📅 Calendar APIテスト")
        result = notifier.create_reminder(
            "A2A Pipeline テスト完了確認",
            minutes_from_now=5
        )
        print(f"結果: {result}")

    elif test_type == "all":
        print("\n🔄 全APIテスト")

        print("\n[1] ログ記録")
        result = notifier.log_to_file("全APIテスト開始", "INFO", "test")
        print(f"結果: {result}")

        print("\n[2] Gmail送信")
        result = notifier.send_log_email(
            "A2A 全APIテスト",
            f"テスト実行時刻: {datetime.now()}"
        )
        print(f"結果: {result}")

        print("\n[3] Calendar作成")
        result = notifier.create_reminder("A2A テスト確認", 5)
        print(f"結果: {result}")

    else:
        print(f"""
使用方法:
  python google_notifier.py [test_type]

test_type:
  log      - ローカルログテスト（デフォルト）
  email    - Gmail API送信テスト
  calendar - Calendar APIテスト
  all      - 全APIテスト
""")

    print("\n" + "=" * 60)
    print("✅ テスト完了")
    print("=" * 60)
