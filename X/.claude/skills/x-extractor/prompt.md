# X Post Extractor Skill

X（旧Twitter）のポストを抽出・分析する専門スキル

## 概要

このスキルは Playwright を使用してXにログインし、特定アカウントのポストを抽出・分析します。

## 機能

### 1. ポスト抽出
- 特定アカウントの最新ポストを取得
- いいね数、RT数、リプライ数を含む
- JSON/CSV/Markdown形式で出力

### 2. セッション管理
- 一度ログインしてセッション保存
- 以降は自動でセッション復元
- セッション無効時は再ログイン案内

### 3. ポスト分析
- エンゲージメント統計
- バズポスト特定
- 投稿パターン分析

## 使用可能なコマンド

```bash
# セッション管理
python session_manager.py login    # ログイン
python session_manager.py verify   # 検証
python session_manager.py info     # 情報表示
python session_manager.py clear    # クリア

# ポスト抽出
python post_extractor.py <username> [options]
  --max N            # 最大件数
  --min-likes N      # 最小いいね数
  --format json|csv|markdown
  --include-replies
  --include-retweets
```

## データ構造

### XPost

```json
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
  "extracted_at": "2024-01-02T00:00:00"
}
```

## ディレクトリ構成

```
X/
├── sessions/           # セッションファイル
├── data/              # 抽出データ
│   ├── x_posts_*.json
│   └── analysis/      # 分析レポート
├── logs/              # ログファイル
└── reports/           # 統合レポート
```

## 注意事項

1. **レート制限**: 過度なスクレイピングは避ける
2. **セッション保護**: sessions/ フォルダは外部に漏洩させない
3. **利用規約**: X の ToS を遵守する

## 典型的なワークフロー

1. `/session` でセッション確認
2. `/extract @username` でポスト抽出
3. `/analyze` で分析
4. `/buzz` でバズ要因特定
5. レポート確認・活用
