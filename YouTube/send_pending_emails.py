#!/usr/bin/env python3
"""
Send Pending Emails - 保留中のメールをMCP経由で送信

使用方法:
  python send_pending_emails.py

このスクリプトは output/ ディレクトリ内の *_email.json ファイルを検索し、
MCP経由で送信するための情報を表示します。

Claude Code から実行する場合:
  1. このスクリプトを実行してメール情報を取得
  2. 表示されたMCPコマンドを実行
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
FINAL_DIR = OUTPUT_DIR / "final"
SCRIPTS_DIR = OUTPUT_DIR / "scripts"


def find_pending_emails():
    """保留中のメールJSONファイルを検索"""
    pending = []

    for directory in [OUTPUT_DIR, FINAL_DIR, SCRIPTS_DIR]:
        if not directory.exists():
            continue
        for f in directory.glob("*_email.json"):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                    pending.append({
                        'file': f,
                        'data': data,
                        'created': datetime.fromtimestamp(f.stat().st_mtime)
                    })
            except Exception as e:
                print(f"⚠️ Error reading {f}: {e}")

    # 作成日時でソート
    pending.sort(key=lambda x: x['created'], reverse=True)
    return pending


def display_email_info(email_info):
    """メール情報を表示"""
    data = email_info['data']
    body_schema = json.loads(data.get('body_schema', '{}'))

    print(f"\n📧 ファイル: {email_info['file'].name}")
    print(f"   作成日時: {email_info['created'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   宛先: {body_schema.get('to', ['N/A'])}")
    print(f"   件名: {body_schema.get('subject', 'N/A')}")


def generate_mcp_command(email_info):
    """MCP送信コマンドを生成"""
    data = email_info['data']

    # body_schemaを整形
    body_schema = data.get('body_schema', '{}')
    if isinstance(body_schema, str):
        body_obj = json.loads(body_schema)
    else:
        body_obj = body_schema

    # HTMLは長いので省略表示
    html_preview = body_obj.get('htmlBody', '')[:100] + '...' if body_obj.get('htmlBody') else ''

    return f"""
## MCP送信コマンド

```python
mcp__klavis-strata__execute_action(
    server_name="{data.get('server_name', 'gmail')}",
    category_name="{data.get('category_name', 'GMAIL_EMAIL')}",
    action_name="{data.get('action_name', 'gmail_send_email')}",
    body_schema='{json.dumps(body_obj, ensure_ascii=False)}'
)
```

件名: {body_obj.get('subject', 'N/A')}
"""


def main():
    print("=" * 60)
    print("📧 Pending Email Sender")
    print("=" * 60)

    pending = find_pending_emails()

    if not pending:
        print("\n✅ 保留中のメールはありません")
        return

    print(f"\n🔍 {len(pending)}件の保留メールが見つかりました")

    for i, email_info in enumerate(pending, 1):
        print(f"\n{'='*40}")
        print(f"[{i}/{len(pending)}]")
        display_email_info(email_info)
        print(generate_mcp_command(email_info))

    print("\n" + "=" * 60)
    print("💡 上記のMCPコマンドをClaude Codeで実行してください")
    print("=" * 60)

    # 最新のメールのbody_schemaをJSON形式で出力（コピペ用）
    if pending:
        latest = pending[0]
        print(f"\n📋 最新メール（{latest['file'].name}）のbody_schema:")
        print("-" * 40)
        data = latest['data']
        body_schema = data.get('body_schema', '{}')
        if isinstance(body_schema, str):
            print(body_schema)
        else:
            print(json.dumps(body_schema, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
