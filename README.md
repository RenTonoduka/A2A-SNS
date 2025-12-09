# SNS A2A エージェント群

SNS運用を自動化するA2Aエージェントシステム。Claude Code CLIをバックエンドに使用し、各プラットフォーム専門のエージェントが協調して動作します。

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    SNS A2A Agents                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────┐                                   │
│  │   SNS Orchestrator   │  :8080                            │
│  │   （統括エージェント）  │                                   │
│  └──────────┬───────────┘                                   │
│             │                                                │
│      ┌──────┴──────┬──────────┬──────────┐                  │
│      ▼             ▼          ▼          ▼                  │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐            │
│  │YouTube │  │   X    │  │  IG    │  │ TikTok │            │
│  │ Agents │  │ Agents │  │ Agents │  │ Agents │            │
│  └────────┘  └────────┘  └────────┘  └────────┘            │
│      │         (予定)      (予定)      (予定)                │
│      │                                                       │
│      ├── script-writer      :8081                           │
│      ├── shorts-creator     :8082                           │
│      ├── seo-optimizer      :8083                           │
│      └── thumbnail-planner  :8084                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## ディレクトリ構造

```
SNS/
├── _shared/                    # 共通モジュール
│   ├── a2a_base_server.py     # A2Aサーバー基底クラス
│   ├── a2a_client.py          # A2Aクライアント
│   └── requirements.txt       # Python依存関係
│
├── orchestrator/               # SNS統括エージェント
│   ├── server.py
│   ├── agent_card.json
│   └── prompts/
│
├── YouTube/                    # YouTube専門エージェント群
│   ├── script-writer/         # 台本作成
│   ├── shorts-creator/        # Shorts企画
│   ├── seo-optimizer/         # SEO最適化
│   └── thumbnail-planner/     # サムネイル企画
│
├── docker-compose.yml          # 一括起動設定
├── Dockerfile
└── README.md
```

## クイックスタート

### 1. 依存関係インストール

```bash
cd A2A/SNS
pip install -r _shared/requirements.txt
```

### 2. 単体起動（開発用）

```bash
# Orchestrator
python orchestrator/server.py

# YouTube エージェント（別ターミナル）
python YouTube/script-writer/server.py
python YouTube/shorts-creator/server.py
python YouTube/seo-optimizer/server.py
python YouTube/thumbnail-planner/server.py
```

### 3. Docker一括起動

```bash
docker-compose up -d
```

## 使い方

### Agent Card 取得

```bash
curl http://localhost:8080/.well-known/agent.json
```

### タスク送信

```bash
curl -X POST http://localhost:8080/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "AIツールの紹介動画を作りたい"}]
    }
  }'
```

### Python から呼び出し

```python
from _shared.a2a_client import A2AClient
import asyncio

async def main():
    client = A2AClient("http://localhost:8080")

    # Agent Card確認
    card = await client.get_agent_card()
    print(card)

    # タスク送信
    result = await client.send_task("AIツールの紹介動画の台本を作って")
    print(result)

asyncio.run(main())
```

## エージェント一覧

| エージェント | ポート | 役割 |
|-------------|--------|------|
| sns-orchestrator | 8080 | SNS運用統括、タスク振り分け |
| youtube-script-writer | 8081 | 動画台本・構成作成 |
| youtube-shorts-creator | 8082 | Shorts企画・スクリプト |
| youtube-seo-optimizer | 8083 | タイトル・説明・タグ最適化 |
| youtube-thumbnail-planner | 8084 | サムネイル企画・構成案 |

## 今後の追加予定

- [ ] X (Twitter) エージェント群
- [ ] Instagram エージェント群
- [ ] TikTok エージェント群
- [ ] LINE公式 エージェント群

## 技術仕様

- **プロトコル**: A2A (Agent-to-Agent) Protocol
- **通信**: HTTP / JSON-RPC 2.0
- **バックエンド**: Claude Code CLI
- **フレームワーク**: FastAPI
- **コスト**: Claude Codeサブスク内（API課金なし）
