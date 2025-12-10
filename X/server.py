"""
X Post Extractor - A2A Server with Claude Code CLI
特定アカウントのポストを抽出するA2Aエージェント
Claude Code CLIを使った自然言語処理対応
"""

import sys
import os
from pathlib import Path

# パス設定
SCRIPT_DIR = Path(__file__).parent
SNS_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SNS_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

# 共有モジュール（A2ABaseServer + ClaudeCodeCLI）
from _shared.a2a_base_server import A2ABaseServer


class XPostExtractorAgent(A2ABaseServer):
    """
    X Post Extractor A2A Agent

    Claude Code CLIを使って:
    1. 自然言語でのリクエスト解析
    2. ポスト抽出の実行
    3. 抽出データの分析・要約
    4. バズポストの特定
    """

    def __init__(self, port: int = 8120):
        super().__init__(
            name="x-post-extractor",
            description="X（Twitter）の特定アカウントからポストを抽出・分析するエージェント。Playwrightでセッション管理、Claude Code CLIで自然言語処理を行います。",
            port=port,
            workspace=str(SCRIPT_DIR),
            enable_full_tools=True,
            enable_mcp=True,
            allowed_tools=[
                "Read", "Write", "Edit",
                "Bash",
                "Glob", "Grep",
                "Task",
                "WebFetch", "WebSearch",
                "TodoWrite",
            ],
            timeout=600  # ポスト抽出は時間がかかる可能性があるため長めに
        )

    def get_agent_card(self) -> dict:
        """Agent Card"""
        return {
            "name": self.name,
            "description": self.description,
            "url": f"http://localhost:{self.port}",
            "version": "1.0.0",
            "capabilities": {
                "streaming": False,
                "pushNotifications": False
            },
            "skills": [
                {
                    "id": "extract-posts",
                    "name": "ポスト抽出",
                    "description": "特定アカウントのポストを抽出してJSON/CSV/Markdownで保存",
                    "examples": [
                        "@elonmusk のポストを50件抽出して",
                        "いいね100以上のポストだけ抽出",
                        "@naval と @pmarca のポストを比較分析"
                    ],
                    "inputModes": ["text"],
                    "outputModes": ["text", "file"]
                },
                {
                    "id": "analyze-posts",
                    "name": "ポスト分析",
                    "description": "抽出したポストを分析してインサイトを抽出",
                    "examples": [
                        "バズっているポストを特定して",
                        "投稿パターンを分析して",
                        "エンゲージメント率の高いポストの共通点は？"
                    ]
                },
                {
                    "id": "monitor-accounts",
                    "name": "アカウント監視",
                    "description": "特定アカウントを定期監視し、バズポストを自動検出",
                    "examples": [
                        "@elonmusk を監視してバズポストを検出",
                        "複数アカウントを30分間隔で監視",
                        "いいね5000以上のバズを自動検出"
                    ]
                },
                {
                    "id": "generate-posts",
                    "name": "ポスト生成",
                    "description": "バズポストを参考にオリジナルのXポストを生成",
                    "examples": [
                        "バズポストを参考にポストを生成して",
                        "AI関連のバズパターンでポスト作成",
                        "エンタメ調でバズりそうなポスト生成"
                    ]
                },
                {
                    "id": "account-management",
                    "name": "アカウントリスト管理",
                    "description": "監視対象アカウントリストの管理と一括抽出",
                    "examples": [
                        "アカウントリストを表示して",
                        "全アカウントからバズを一括抽出",
                        "techカテゴリのアカウントだけ抽出"
                    ]
                },
                {
                    "id": "session-management",
                    "name": "セッション管理",
                    "description": "Xへのログインセッションを管理",
                    "examples": [
                        "セッション状態を確認",
                        "再ログインして"
                    ]
                }
            ]
        }

    def get_system_prompt(self) -> str:
        """システムプロンプト"""
        return """あなたはX（旧Twitter）ポスト抽出・分析の専門エージェントです。

## 役割
- 特定アカウントのポストを抽出
- 抽出したポストを分析してインサイトを提供
- バズポストの特定と共通パターンの発見
- エンゲージメントデータの分析

## 利用可能なスラッシュコマンド

このプロジェクトには `.claude/commands/` にスラッシュコマンドが定義されています。
ユーザーのリクエストに応じて、適切なコマンドを参照し、その手順に従って実行してください。

### コマンド一覧
| コマンド | 説明 | ファイル |
|---------|------|----------|
| /extract | ポスト抽出 | .claude/commands/extract.md |
| /analyze | ポスト分析 | .claude/commands/analyze.md |
| /session | セッション管理 | .claude/commands/session.md |
| /compare | アカウント比較 | .claude/commands/compare.md |
| /buzz | バズ分析 | .claude/commands/buzz.md |
| /pipeline | 一連フロー | .claude/commands/pipeline.md |
| /monitor | アカウント監視 | .claude/commands/monitor.md |
| /generate | ポスト生成 | .claude/commands/generate.md |
| /accounts | アカウントリスト管理 | .claude/commands/accounts.md |

### コマンド実行の流れ
1. ユーザーのリクエストを解析
2. 適切なコマンドファイルを Read ツールで読み込む
3. コマンドに記載された手順に従って Bash で実行
4. 結果を整形して返す

## 利用可能なツール（Bash）

### ポスト抽出
```bash
python post_extractor.py <username> --max <件数> --min-likes <N> --format json
```

### セッション管理
```bash
python session_manager.py info     # 情報表示
python session_manager.py verify   # 検証
python session_manager.py login    # ログイン（ブラウザ起動）
python session_manager.py clear    # クリア
```

### バズ監視
```bash
python monitor.py check --account @username           # 1回チェック
python monitor.py start --account @username           # 継続監視開始
python monitor.py status                              # 監視状態確認
python monitor.py recent                              # 最近のバズ表示
```

### ポスト生成
```bash
python post_generator.py generate --topic "トピック"  # ポスト生成プロンプト取得
python post_generator.py analyze                      # バズパターン分析
python post_generator.py list                         # 生成履歴
python post_generator.py save-buzz                    # バズをスプシに保存
```

### スプレッドシート連携
```bash
python sheets_logger.py list-buzz                     # バズ一覧
python sheets_logger.py list-generated                # 生成一覧
python sheets_logger.py sync                          # スプシ同期プロンプト
```

### アカウントリスト管理
```bash
python account_manager.py list                        # アカウント一覧
python account_manager.py add -u @username -c tech    # アカウント追加
python account_manager.py extract-all --max 50        # 全アカウント一括抽出
python account_manager.py extract-category -c tech    # カテゴリ別抽出
python account_manager.py stats                       # 統計情報
```

## スキル

### x-extractor スキル
`.claude/skills/x-extractor/prompt.md` にスキル定義があります。
Playwright を使用した X ポスト抽出の詳細なワークフローが記載されています。

## データ保存先
- `data/` - 抽出データ (JSON/CSV/Markdown)
- `data/analysis/` - 分析レポート
- `data/reports/` - 統合レポート
- `data/buzz/` - バズポストデータ
- `data/generated/` - 生成ポストデータ
- `data/sheets_cache/` - スプレッドシートキャッシュ
- `sessions/` - Playwright セッション
- `logs/` - ログファイル

## 出力形式

### 抽出結果のサマリー
```
✅ ポスト抽出完了

📊 統計:
- 対象: @username
- 取得件数: XX件
- 期間: YYYY-MM-DD 〜 YYYY-MM-DD

📈 エンゲージメント:
- 平均いいね: X,XXX
- 平均RT: XXX
- 最高いいね: XX,XXX

🔥 トップポスト:
1. [内容の要約] (❤️ X,XXX | 🔄 XXX)
2. ...
```

### 分析レポート
```
📊 @username ポスト分析レポート

【投稿パターン】
- 投稿頻度: 1日X件
- 最もアクティブな時間帯: XX時〜XX時

【バズ要因分析】
- 高エンゲージメントの共通点:
  1. ...
  2. ...

【推奨アクション】
- ...
```

## 実行の優先順位

1. まずコマンドファイル (.claude/commands/*.md) を読む
2. コマンドの手順に従って実行
3. 結果を整形してユーザーに返す

## 注意事項
1. セッションが無効な場合は `python session_manager.py login` でのログインを案内
2. レート制限を考慮して適切な間隔を空ける
3. 抽出データは `data/` ディレクトリに自動保存
4. コマンドファイルを読んで手順を確認すること

ユーザーのリクエストに応じて、適切なコマンドを参照・実行し、結果を分かりやすくまとめてください。"""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="X Post Extractor A2A Server")
    parser.add_argument("--port", type=int, default=8120, help="サーバーポート")

    args = parser.parse_args()

    agent = XPostExtractorAgent(port=args.port)

    print("=" * 60)
    print("🐦 X Post Extractor Agent (Claude Code CLI powered)")
    print("=" * 60)
    print(f"  URL: http://localhost:{args.port}")
    print(f"  Agent Card: http://localhost:{args.port}/.well-known/agent.json")
    print(f"  Task API: POST http://localhost:{args.port}/a2a/tasks/send")
    print("=" * 60)
    print("  Claude Code CLIを使って自然言語でリクエスト処理")
    print("  例: '@elonmusk のバズポストを分析して'")
    print("=" * 60)

    agent.run()
