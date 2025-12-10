# X Post Extractor - Claude Code Configuration

このディレクトリには、Claude Code CLI がこのプロジェクトで使用する設定ファイルが含まれています。

## 構成

```
.claude/
├── commands/              # スラッシュコマンド定義
│   ├── extract.md        # /extract - ポスト抽出
│   ├── analyze.md        # /analyze - ポスト分析
│   ├── session.md        # /session - セッション管理
│   ├── compare.md        # /compare - アカウント比較
│   ├── buzz.md           # /buzz - バズ分析
│   ├── pipeline.md       # /pipeline - 一連のフロー実行
│   ├── monitor.md        # /monitor - アカウント監視
│   ├── generate.md       # /generate - ポスト生成
│   └── accounts.md       # /accounts - アカウントリスト管理
├── skills/               # スキル定義
│   └── x-extractor/      # X抽出スキル
│       └── prompt.md
├── settings.local.json   # ローカル設定
└── README.md             # このファイル
```

## コマンド一覧

| コマンド | 説明 |
|---------|------|
| `/extract @user` | 特定アカウントのポストを抽出 |
| `/analyze` | 抽出したポストを分析 |
| `/session` | セッション状態確認・管理 |
| `/compare @user1 @user2` | 複数アカウントの比較 |
| `/buzz @user` | バズポスト特定・分析 |
| `/pipeline @user` | 抽出→分析→レポートの自動実行 |
| `/monitor @user` | アカウント監視・バズ自動検出 |
| `/generate` | バズポストからオリジナルポスト生成 |
| `/accounts` | アカウントリスト管理・一括抽出 |

## 使用例

```
# 基本的な抽出と分析
/session verify
/extract @elonmusk --max 100
/analyze

# バズ分析
/buzz @naval --threshold 5

# 比較分析
/compare @elonmusk @naval

# フルパイプライン
/pipeline @pmarca --full

# アカウント監視
/monitor @elonmusk --start --interval 30
/monitor status
/monitor recent

# ポスト生成
/generate --topic "AI技術"
/generate --style entertaining
```

## スキル

### x-extractor

X（旧Twitter）のポスト抽出・分析に特化したスキル。
Playwrightでセッション管理し、ポストデータを収集・分析します。

## A2A連携

このプロジェクトはA2A（Agent-to-Agent）プロトコルに対応しています。

```bash
# A2Aサーバー起動
python server.py --port 8120

# Agent Card
curl http://localhost:8120/.well-known/agent.json

# タスク送信
curl -X POST http://localhost:8120/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -d '{"message": {"role": "user", "parts": [{"type": "text", "text": "@elonmusk のポストを分析して"}]}}'
```

## 注意事項

- セッションファイル（`sessions/`）は機密情報を含むため、gitignore に追加されています
- 過度なスクレイピングはXのアカウント制限の原因になります
- X の利用規約を遵守してください
