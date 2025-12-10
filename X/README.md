# X Post Extractor

X（旧Twitter）の特定アカウントからポストを抽出するA2Aエージェント

## 機能

- **セッション管理**: Playwrightでログイン状態を保存・復元
- **ポスト抽出**: 特定アカウントの最新ポストを取得
- **フィルタリング**: いいね数、RT数、リプライ除外などでフィルタ
- **複数フォーマット出力**: JSON / CSV / Markdown
- **A2A対応**: Agent-to-Agent プロトコルでの連携

## セットアップ

### 1. 依存関係のインストール

```bash
cd SNS/X
pip install -r requirements.txt
playwright install chromium
```

### 2. 初回ログイン（セッション作成）

```bash
python session_manager.py login
```

ブラウザが開くので、手動でXにログインしてください。
ログイン完了後、自動的にセッションが保存されます。

### 3. セッション確認

```bash
# セッション状態を確認
python session_manager.py verify

# セッション情報を表示
python session_manager.py info

# セッションをクリア（再ログインが必要になる）
python session_manager.py clear
```

## 使用方法

### CLI での抽出

```bash
# 単一アカウントから50件抽出
python post_extractor.py elonmusk

# 複数アカウント
python post_extractor.py elonmusk naval pmarca

# オプション指定
python post_extractor.py elonmusk \
  --max 100 \
  --format csv \
  --min-likes 1000 \
  --include-retweets
```

### A2A サーバーとして起動

```bash
# デフォルトポート 8120 で起動
python server.py

# カスタムポート
python server.py --port 8121
```

### A2A API

```bash
# Agent Card 取得
curl http://localhost:8120/.well-known/agent.json

# タスク送信
curl -X POST http://localhost:8120/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "@elonmusk のポストを50件抽出して"}]
    }
  }'

# 直接抽出API
curl -X POST http://localhost:8120/extract \
  -H "Content-Type: application/json" \
  -d '{
    "usernames": ["elonmusk"],
    "max_posts": 50,
    "min_likes": 100,
    "output_format": "json"
  }'
```

## ディレクトリ構成

```
X/
├── config.py           # 設定
├── session_manager.py  # セッション管理
├── post_extractor.py   # ポスト抽出
├── server.py           # A2Aサーバー
├── requirements.txt    # 依存関係
├── README.md           # このファイル
├── sessions/           # セッション保存先
│   └── default_storage.json
├── data/               # 抽出データ保存先
│   └── x_posts_*.json
└── logs/               # ログ
    ├── session.log
    ├── extractor.log
    └── server.log
```

## 設定オプション

### ExtractorConfig

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| max_posts_per_account | 50 | アカウントごとの最大取得数 |
| include_replies | False | リプライを含めるか |
| include_retweets | False | リツイートを含めるか |
| min_likes | 0 | 最小いいね数フィルタ |
| min_retweets | 0 | 最小RT数フィルタ |
| output_format | json | 出力形式 (json/csv/markdown) |

### BrowserConfig

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| headless | False | ヘッドレスモード（初回ログインはFalse推奨） |
| session_name | default | セッション名（複数アカウント用） |
| slow_mo | 50 | 操作間隔(ms) |

## 出力形式

### JSON

```json
[
  {
    "post_id": "1234567890",
    "author_username": "elonmusk",
    "author_name": "Elon Musk",
    "content": "ポスト内容...",
    "timestamp": "2024-01-01T00:00:00.000Z",
    "likes": 10000,
    "retweets": 5000,
    "replies": 2000,
    "views": 1000000,
    "is_retweet": false,
    "is_reply": false,
    "media_urls": [],
    "post_url": "https://x.com/elonmusk/status/1234567890",
    "extracted_at": "2024-01-02T00:00:00.000000"
  }
]
```

### CSV

| post_id | author_username | content | likes | retweets | ... |
|---------|-----------------|---------|-------|----------|-----|
| 123... | elonmusk | ... | 10000 | 5000 | ... |

### Markdown

```markdown
# X Posts - elonmusk

## @elonmusk

> ポスト内容...

- 📅 2024-01-01T00:00:00.000Z
- ❤️ 10000 | 🔄 5000 | 💬 2000
- 🔗 [https://x.com/...](https://x.com/...)
```

## 他のA2Aエージェントとの連携

```python
from _shared.a2a_client import A2AClient

# X抽出エージェントを呼び出し
client = A2AClient("http://localhost:8120")

result = await client.send_task(
    message="@naval のポストを100件抽出して、いいね1000以上のものだけ"
)

print(result)
```

## 注意事項

- X の利用規約を遵守してください
- 過度なスクレイピングはアカウント制限の原因になります
- レート制限対策として、リクエスト間に適切な待機時間を設けています
- セッションファイルには認証情報が含まれるため、外部に漏洩しないよう注意してください
