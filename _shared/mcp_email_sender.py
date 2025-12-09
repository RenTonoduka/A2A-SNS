"""
MCP Email Sender - MCP経由でメール送信
pipeline_runner.py から呼び出して使用
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

# 通知先メール
NOTIFY_EMAIL = "tonoduka@h-bb.jp"


def create_script_email_html(
    theme: str,
    score: int,
    script_content: str,
    buzz_video: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None
) -> str:
    """
    台本完成メールのHTML本文を生成

    Args:
        theme: 動画テーマ
        score: スコア
        script_content: 台本内容
        buzz_video: 参考バズ動画情報
        timestamp: タイムスタンプ
    """
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    video_url = ""
    buzz_section = ""

    if buzz_video:
        video_url = f"https://youtube.com/watch?v={buzz_video.get('video_id', '')}"
        pr = buzz_video.get('performance_ratio', buzz_video.get('pr', 0))
        view_count = buzz_video.get('view_count', buzz_video.get('views', 0))

        buzz_section = f"""
<div class="buzz-video">
<h2>🔥 参考バズ動画</h2>
<table>
<tr><td><strong>タイトル:</strong></td><td>{buzz_video.get('title', 'N/A')}</td></tr>
<tr><td><strong>チャンネル:</strong></td><td>{buzz_video.get('channel_name', buzz_video.get('channel', 'N/A'))}</td></tr>
<tr><td><strong>再生数:</strong></td><td>{view_count:,}回</td></tr>
<tr><td><strong>PR:</strong></td><td><strong>{pr:.1f}x</strong></td></tr>
</table>
<p><a href="{video_url}" class="cta-button">▶️ 参考動画を見る</a></p>
</div>
"""

    # スクリプト内容をHTMLエスケープ
    script_html = script_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    html = f"""<html>
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

{buzz_section}

<h2>📝 生成された台本</h2>
<div class="script-content">
{script_html}
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
</html>"""

    return html


def create_buzz_detection_email_html(
    videos: List[Dict[str, Any]],
    threshold: float = 5.0
) -> str:
    """
    バズ動画検出メールのHTML本文を生成

    Args:
        videos: バズ動画リスト
        threshold: PRしきい値
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    videos_html = ""
    for i, v in enumerate(videos[:10], 1):
        pr = v.get('performance_ratio', v.get('pr', 0))
        view_count = v.get('view_count', v.get('views', 0))
        video_url = f"https://youtube.com/watch?v={v.get('video_id', '')}"

        videos_html += f"""
<div class="video-item">
<h3>【{i}位】PR: {pr:.1f}x</h3>
<table>
<tr><td><strong>タイトル:</strong></td><td>{v.get('title', 'N/A')}</td></tr>
<tr><td><strong>チャンネル:</strong></td><td>{v.get('channel_name', v.get('channel', 'N/A'))}</td></tr>
<tr><td><strong>再生数:</strong></td><td>{view_count:,}回</td></tr>
</table>
<p><a href="{video_url}" class="cta-button">▶️ 動画を見る</a></p>
</div>
"""

    html = f"""<html>
<head>
<style>
body {{ font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif; line-height: 1.8; color: #333; }}
.header {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 10px; }}
.section {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #f5576c; }}
.video-item {{ background: #fff; padding: 15px; margin: 10px 0; border-radius: 8px; border: 1px solid #dee2e6; }}
.footer {{ background: #e9ecef; padding: 15px; margin-top: 20px; border-radius: 8px; font-size: 12px; color: #6c757d; }}
a {{ color: #f5576c; }}
h2 {{ color: #f5576c; border-bottom: 2px solid #f5576c; padding-bottom: 5px; }}
h3 {{ color: #333; margin-bottom: 10px; }}
.cta-button {{ display: inline-block; background: #f5576c; color: white !important; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 14px; }}
</style>
</head>
<body>

<div class="header">
<h1>🔥 バズ動画検出！</h1>
<p>{len(videos)}件のバズ動画が見つかりました</p>
</div>

<div class="section">
<h2>📋 検出条件</h2>
<table>
<tr><td><strong>PRしきい値:</strong></td><td>>= {threshold}x</td></tr>
<tr><td><strong>検出日時:</strong></td><td>{timestamp}</td></tr>
<tr><td><strong>検出数:</strong></td><td>{len(videos)}件</td></tr>
</table>
</div>

<h2>🎬 検出されたバズ動画</h2>
{videos_html}

<div class="section">
<h2>💡 次のアクション</h2>
<ol>
<li>トランスクリプトを取得して構成を分析</li>
<li>タイトルパターンを抽出</li>
<li>台本生成に活用</li>
</ol>
</div>

<div class="footer">
<p>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</p>
<p>🤖 YouTube A2A Pipeline - Phase 1 (Data Collection)</p>
</div>

</body>
</html>"""

    return html


def get_subject_for_script(theme: str, score: int) -> str:
    """台本メールの件名を生成"""
    if score >= 90:
        return f"[A2A] 🎉 高品質台本完成！ {theme[:30]}... ({score}点)"
    elif score >= 70:
        return f"[A2A] ✅ 台本完成 {theme[:30]}... ({score}点)"
    else:
        return f"[A2A] 📝 台本生成完了 {theme[:30]}... (要レビュー)"


def generate_mcp_email_call(
    to: str,
    subject: str,
    body: str,
    html_body: str
) -> Dict[str, Any]:
    """
    MCP email送信用のパラメータを生成

    Claude Code から直接 mcp__klavis-strata__execute_action を呼び出す際に使用
    """
    return {
        "server_name": "gmail",
        "category_name": "GMAIL_EMAIL",
        "action_name": "gmail_send_email",
        "body_schema": json.dumps({
            "to": [to],
            "subject": subject,
            "body": body,
            "htmlBody": html_body,
            "mimeType": "multipart/alternative"
        })
    }


def print_mcp_email_instruction(
    to: str,
    subject: str,
    body: str,
    html_body: str
) -> str:
    """
    MCP email送信の指示を出力（Claude Codeが実行する用）
    """
    instruction = f"""
## 📧 メール送信が必要です

以下のMCPコマンドを実行してください:

```
mcp__klavis-strata__execute_action(
    server_name="gmail",
    category_name="GMAIL_EMAIL",
    action_name="gmail_send_email",
    body_schema='{json.dumps({
        "to": [to],
        "subject": subject,
        "body": body[:100] + "...",
        "htmlBody": "（HTML本文）",
        "mimeType": "multipart/alternative"
    })}'
)
```

宛先: {to}
件名: {subject}
"""
    return instruction


# ============================================
# 高レベル関数（pipeline_runner.py から呼び出し）
# ============================================

def prepare_script_completion_email(
    theme: str,
    score: int,
    output_file: str,
    buzz_video: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    台本完成メールを準備

    Args:
        theme: 動画テーマ
        score: スコア
        output_file: 台本ファイルパス
        buzz_video: 参考バズ動画情報

    Returns:
        MCP実行用のパラメータ dict
    """
    # 台本内容を読み込み
    script_content = ""
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            script_content = f.read()
    except Exception as e:
        script_content = f"(ファイル読み込みエラー: {e})"

    # HTML生成
    html_body = create_script_email_html(
        theme=theme,
        score=score,
        script_content=script_content,
        buzz_video=buzz_video
    )

    # 件名
    subject = get_subject_for_script(theme, score)

    # プレーンテキスト本文
    plain_body = f"""台本完成通知

テーマ: {theme}
スコア: {score}/100
"""
    if buzz_video:
        plain_body += f"""
参考動画: {buzz_video.get('title', 'N/A')}
URL: https://youtube.com/watch?v={buzz_video.get('video_id', '')}
"""

    plain_body += f"""
---
{script_content[:5000]}
"""

    return {
        "to": NOTIFY_EMAIL,
        "subject": subject,
        "body": plain_body,
        "html_body": html_body,
        "mcp_params": generate_mcp_email_call(NOTIFY_EMAIL, subject, plain_body, html_body)
    }


def prepare_buzz_detection_email(
    videos: List[Dict[str, Any]],
    threshold: float = 5.0
) -> Dict[str, Any]:
    """
    バズ動画検出メールを準備

    Args:
        videos: バズ動画リスト
        threshold: PRしきい値

    Returns:
        MCP実行用のパラメータ dict
    """
    # HTML生成
    html_body = create_buzz_detection_email_html(videos, threshold)

    # 件名
    subject = f"[A2A] 🔥 バズ動画検出 {len(videos)}件 (PR>={threshold})"

    # プレーンテキスト本文
    plain_body = f"""バズ動画検出通知

検出数: {len(videos)}件
PRしきい値: >= {threshold}x

検出動画:
"""
    for i, v in enumerate(videos[:5], 1):
        pr = v.get('performance_ratio', v.get('pr', 0))
        plain_body += f"""
{i}. {v.get('title', 'N/A')}
   PR: {pr:.1f}x
   URL: https://youtube.com/watch?v={v.get('video_id', '')}
"""

    return {
        "to": NOTIFY_EMAIL,
        "subject": subject,
        "body": plain_body,
        "html_body": html_body,
        "mcp_params": generate_mcp_email_call(NOTIFY_EMAIL, subject, plain_body, html_body)
    }


# ============================================
# Google Docs 作成
# ============================================

def create_google_doc_content(
    theme: str,
    score: int,
    script_content: str,
    buzz_video: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None
) -> str:
    """
    Google Docs用のテキストコンテンツを生成

    Args:
        theme: 動画テーマ
        score: スコア
        script_content: 台本内容
        buzz_video: 参考バズ動画情報
        timestamp: タイムスタンプ
    """
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    # バズ動画セクション
    buzz_section = ""
    if buzz_video:
        video_url = f"https://youtube.com/watch?v={buzz_video.get('video_id', '')}"
        pr = buzz_video.get('performance_ratio', buzz_video.get('pr', 0))
        view_count = buzz_video.get('view_count', buzz_video.get('views', 0))

        buzz_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 参考バズ動画
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
タイトル: {buzz_video.get('title', 'N/A')}
チャンネル: {buzz_video.get('channel_name', buzz_video.get('channel', 'N/A'))}
再生数: {view_count:,}回
PR: {pr:.1f}x (登録者比)
URL: {video_url}

💡 この動画の構成・フック・展開を参考にしました
"""

    doc_content = f"""🎬 YouTube台本
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 基本情報
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return doc_content


def prepare_google_doc_creation(
    theme: str,
    score: int,
    output_file: str,
    buzz_video: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Google Docs作成用のMCPパラメータを準備

    Args:
        theme: 動画テーマ
        score: スコア
        output_file: 台本ファイルパス
        buzz_video: 参考バズ動画情報

    Returns:
        MCP実行用のパラメータ dict
    """
    # 台本内容を読み込み
    script_content = ""
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            script_content = f.read()
    except Exception as e:
        script_content = f"(ファイル読み込みエラー: {e})"

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    # ドキュメントタイトル
    doc_title = f"【台本】{theme[:40]} ({timestamp})"

    # コンテンツ生成
    doc_content = create_google_doc_content(
        theme=theme,
        score=score,
        script_content=script_content,
        buzz_video=buzz_video,
        timestamp=timestamp
    )

    # MCPパラメータ
    mcp_params = {
        "server_name": "google docs",
        "category_name": "GOOGLE_DOCS_DOCUMENT",
        "action_name": "google_docs_create_document_from_text",
        "body_schema": json.dumps({
            "title": doc_title,
            "text_content": doc_content
        }, ensure_ascii=False)
    }

    return {
        "title": doc_title,
        "content": doc_content,
        "mcp_params": mcp_params
    }


def prepare_script_with_doc_and_email(
    theme: str,
    score: int,
    output_file: str,
    buzz_video: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    台本完成時にGoogle Docs作成 + メール送信の両方を準備

    Args:
        theme: 動画テーマ
        score: スコア
        output_file: 台本ファイルパス
        buzz_video: 参考バズ動画情報

    Returns:
        email_params, google_doc_params の両方を含むdict
    """
    # メール準備
    email_data = prepare_script_completion_email(
        theme=theme,
        score=score,
        output_file=output_file,
        buzz_video=buzz_video
    )

    # Google Docs準備
    doc_data = prepare_google_doc_creation(
        theme=theme,
        score=score,
        output_file=output_file,
        buzz_video=buzz_video
    )

    return {
        "theme": theme,
        "score": score,
        "email": email_data,
        "google_doc": doc_data,
        "combined_mcp_calls": [
            {
                "type": "google_doc",
                "description": f"Google Docs作成: {doc_data['title']}",
                "params": doc_data['mcp_params']
            },
            {
                "type": "email",
                "description": f"メール送信: {email_data['subject']}",
                "params": email_data['mcp_params']
            }
        ]
    }


# テスト
if __name__ == "__main__":
    print("=" * 60)
    print("MCP Email Sender Test")
    print("=" * 60)

    # テスト用データ
    test_buzz = {
        'title': '【衝撃】ChatGPT最新機能',
        'channel_name': 'AIチャンネル',
        'video_id': 'test123',
        'view_count': 100000,
        'performance_ratio': 5.5
    }

    # 台本メール準備テスト
    result = prepare_script_completion_email(
        theme="テストテーマ",
        score=85,
        output_file="/tmp/test.md",
        buzz_video=test_buzz
    )

    print(f"\n件名: {result['subject']}")
    print(f"宛先: {result['to']}")
    print(f"\nMCPパラメータ:")
    print(json.dumps(result['mcp_params'], indent=2, ensure_ascii=False)[:500])

    print("\n" + "=" * 60)
    print("✅ Test Complete")
    print("=" * 60)
