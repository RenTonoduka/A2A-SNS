# /monitor コマンド

特定アカウントを監視し、バズポストを自動検出

## 使用方法

```
/monitor @username                     # 1回チェック
/monitor @username --start             # 継続監視開始
/monitor status                        # 監視状態確認
/monitor recent                        # 最近のバズ表示
/monitor @user1 @user2 --compare       # 複数アカウント比較
```

## 監視フロー

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  ポスト取得  │────▶│  バズ判定   │────▶│   保存      │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌─────────────┐
                    │   通知      │
                    │ (Webhook)   │
                    └─────────────┘
```

## 実行手順

### 単発チェック

```bash
# 特定アカウントをチェック
python monitor.py check --account @elonmusk

# 複数アカウントをチェック
python monitor.py check --accounts @elonmusk @naval @pmarca
```

### 継続監視

```bash
# 監視開始（30分間隔）
python monitor.py start --account @elonmusk --interval 30

# 複数アカウント監視
python monitor.py start --accounts @elonmusk @naval --interval 15

# カスタム閾値で監視
python monitor.py start --account @elonmusk --threshold 5000 --ratio 5.0
```

### 状態確認

```bash
# 監視状態を表示
python monitor.py status

# 最近のバズポストを表示
python monitor.py recent --limit 10
```

---

## バズ判定基準

### 絶対値基準
- いいね数 >= 1,000（デフォルト）
- `--threshold` オプションで変更可能

### 相対値基準
- アカウント平均の3倍以上（デフォルト）
- `--ratio` オプションで変更可能

### バズスコア計算

```
バズスコア = (いいね / 平均いいね) * 0.7 + (RT / 平均RT) * 0.3
```

---

## 出力例

### チェック結果

```
🔍 Checking @elonmusk...

🔥 Found 3 buzz posts:

1. @elonmusk - ❤️ 125,000 | 🔄 15,000
   Tesla's new Model...
   バズスコア: 8.5x
   🔗 https://x.com/elonmusk/status/...

2. @elonmusk - ❤️ 89,000 | 🔄 12,000
   AI is going to...
   バズスコア: 6.2x
   🔗 https://x.com/elonmusk/status/...

📁 Saved to: data/buzz/buzz_20240115_120000.json
```

### 監視ステータス

```
🔥 X Buzz Monitor Status

📊 監視状態: 稼働中
📡 監視間隔: 30分
🎯 バズ閾値: いいね >= 1,000 または 平均の3.0倍

👤 監視対象アカウント:
  @elonmusk
    最終チェック: 2024-01-15T12:00:00
    バズ検出数: 15
    平均いいね: 45,000
  @naval
    最終チェック: 2024-01-15T12:05:00
    バズ検出数: 8
    平均いいね: 12,000

📈 本日の統計:
  バズ検出: 5件 / 50件上限
```

---

## オプション一覧

| オプション | 説明 | デフォルト |
|-----------|------|----------|
| `--account`, `-a` | 対象アカウント | - |
| `--accounts` | 複数アカウント | - |
| `--interval` | 監視間隔（分） | 30 |
| `--threshold` | バズ判定いいね閾値 | 1000 |
| `--ratio` | バズ判定倍率閾値 | 3.0 |
| `--no-immediate` | 即座実行をスキップ | false |
| `--limit` | 表示件数 | 10 |

---

## 通知設定

### Webhook設定

`config.py` または環境変数で設定:

```python
MonitorConfig(
    notify_on_buzz=True,
    notification_webhook="https://discord.com/api/webhooks/..."
)
```

### 環境変数

```bash
export X_MONITOR_WEBHOOK="https://discord.com/api/webhooks/..."
```

---

## 保存データ形式

### バズポストファイル

`data/buzz/buzz_YYYYMMDD_HHMMSS.json`:

```json
{
  "detected_at": "2024-01-15T12:00:00",
  "count": 3,
  "posts": [
    {
      "post_id": "1234567890",
      "author_username": "elonmusk",
      "content": "...",
      "likes": 125000,
      "retweets": 15000,
      "buzz_score": 8.5,
      "reason": "いいね125,000件 (閾値: 1,000) / バズスコア8.5x",
      "detected_at": "2024-01-15T12:00:00"
    }
  ]
}
```

---

## 関連コマンド

- `/extract` - 手動でポスト抽出
- `/buzz` - バズ分析（既存データ）
- `/analyze` - 詳細分析
- `/session` - セッション管理

---

## 注意事項

1. **セッション必須**: 事前に `/session login` でログインしておく
2. **レート制限**: 監視間隔は最低15分推奨
3. **リソース**: 継続監視はバックグラウンドで実行
4. **保存上限**: 1日最大50件のバズポスト保存
