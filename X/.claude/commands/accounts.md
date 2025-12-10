# /accounts コマンド

アカウントリストの管理と一括抽出

## 使用方法

```
/accounts list                         # アカウント一覧
/accounts add @username                # アカウント追加
/accounts extract-all                  # 全アカウントから一括抽出
/accounts extract-category tech        # カテゴリ別抽出
/accounts stats                        # 統計情報
```

## アカウントリスト

`accounts.json` でアカウントを管理:

```json
{
  "accounts": [
    {
      "username": "elonmusk",
      "category": "tech",
      "priority": "high",
      "notes": "Tesla/SpaceX CEO",
      "enabled": true
    }
  ]
}
```

## 実行手順

### アカウント一覧表示

```bash
python account_manager.py list
```

### アカウント追加

```bash
python account_manager.py add --username @elonmusk --category tech --priority high --notes "メモ"
```

### アカウント削除

```bash
python account_manager.py remove --username @elonmusk
```

### 一括抽出（全アカウント）

```bash
python account_manager.py extract-all --max 50
```

### カテゴリ別抽出

```bash
python account_manager.py extract-category --category tech --max 50
```

### 優先度別抽出

```bash
python account_manager.py extract-priority --priority high --max 50
```

### 統計情報

```bash
python account_manager.py stats
```

---

## カテゴリ一覧

| カテゴリ | 説明 | バズ閾値 |
|---------|------|---------|
| `tech` | テクノロジー系 | 5,000 |
| `business` | ビジネス・起業系 | 3,000 |
| `ai` | AI・機械学習系 | 5,000 |
| `startup` | スタートアップ系 | 2,000 |
| `marketing` | マーケティング系 | 1,000 |

## 優先度

| 優先度 | アイコン | 説明 |
|--------|---------|------|
| `high` | 🔴 | 最優先で監視 |
| `medium` | 🟡 | 通常監視 |
| `low` | 🟢 | 低頻度監視 |

---

## 出力例

### アカウント一覧

```
📋 アカウント一覧 (5件):

  ✅ @elonmusk [tech] 🔴
      Tesla/SpaceX/X CEO
      最終チェック: 2024-01-15T12:00:00
      バズ検出: 15件

  ✅ @naval [business] 🔴
      AngelList founder, philosopher
      最終チェック: 2024-01-15T12:05:00
      バズ検出: 8件

  ❌ @example [general] 🟡
      (無効化されています)
```

### 一括抽出結果

```
🚀 全アカウントから一括抽出中...

📥 Extracting @elonmusk...
  🔥 Found 3 buzz posts

📥 Extracting @naval...
  🔥 Found 2 buzz posts

📥 Extracting @pmarca...
  🔥 Found 1 buzz posts

✅ 完了!
  対象アカウント: 5件
  バズ検出: 12件
```

### 統計情報

```
📊 統計情報:

  総アカウント数: 5
  有効アカウント: 4

  カテゴリ別:
    tech: 2件
    business: 1件
    ai: 1件

  優先度別:
    🔴 high: 3件
    🟡 medium: 1件

  累計抽出ポスト: 500
  累計バズ検出: 45
```

---

## ワークフロー例

### 1. 初期セットアップ

```bash
# アカウントを追加
python account_manager.py add -u @elonmusk -c tech -p high
python account_manager.py add -u @naval -c business -p high
python account_manager.py add -u @paulg -c startup -p medium
```

### 2. 定期抽出

```bash
# 高優先度のみ抽出（毎日）
python account_manager.py extract-priority --priority high

# 全アカウント抽出（週次）
python account_manager.py extract-all
```

### 3. 分析・生成

```bash
# バズ分析
python post_generator.py analyze

# ポスト生成
python post_generator.py generate --topic "AI"
```

---

## accounts.json の編集

直接JSONファイルを編集することも可能:

```json
{
  "accounts": [
    {
      "username": "new_account",
      "category": "tech",
      "priority": "high",
      "notes": "追加したいアカウント",
      "enabled": true
    }
  ]
}
```

---

## 関連コマンド

- `/monitor` - リアルタイム監視
- `/extract` - 単一アカウント抽出
- `/generate` - ポスト生成
- `/buzz` - バズ分析
