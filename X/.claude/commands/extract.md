# /extract コマンド

特定アカウントからポストを抽出する

## 使用方法

```
/extract @username              # 基本抽出（50件）
/extract @user1 @user2          # 複数アカウント
/extract @username --max 100    # 件数指定
/extract @username --min-likes 1000  # いいね数フィルタ
```

## 実行手順

### Step 1: セッション確認

まずセッション状態を確認:

```bash
python session_manager.py info
```

セッションがない、または無効な場合:
```
⚠️ セッションが必要です。
以下のコマンドでログインしてください:

python session_manager.py login
```

### Step 2: ポスト抽出実行

```bash
python post_extractor.py <username> \
  --max <件数> \
  --min-likes <最小いいね数> \
  --format <json|csv|markdown>
```

### Step 3: 結果確認

抽出完了後、以下を確認:
- 取得件数
- 保存先ファイル
- トップポスト（いいね数上位）

### Step 4: 出力サマリー

```
✅ ポスト抽出完了

📊 統計:
- 対象: @username
- 取得件数: XX件
- フィルタ: いいねXXX以上

📈 エンゲージメント:
- 平均いいね: X,XXX
- 最高いいね: XX,XXX
- 平均RT: XXX

🔥 トップ5ポスト:
1. [内容要約] (❤️ X,XXX)
2. ...

📁 保存先: data/x_posts_YYYYMMDD_HHMMSS.json
```

---

## オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--max N` | 最大取得件数 | 50 |
| `--min-likes N` | 最小いいね数 | 0 |
| `--min-retweets N` | 最小RT数 | 0 |
| `--include-replies` | リプライを含める | false |
| `--include-retweets` | RTを含める | false |
| `--format` | 出力形式 (json/csv/markdown) | json |

---

## 入力例

```
/extract @elonmusk --max 100 --min-likes 10000
```

## 関連コマンド

- `/analyze` - 抽出したポストを分析
- `/session` - セッション管理
- `/compare` - 複数アカウントの比較
