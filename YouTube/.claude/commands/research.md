# /research コマンド

競合リサーチを実行し、優秀動画のパターンを分析する

## 使用方法

```
/research [テーマ]        # テーマに関連する優秀動画を分析
/research update         # データ更新（YouTube API）
/research status         # データ状態確認
```

## 実行手順

### Step 1: データ確認

まず `research/data/videos.csv` を読み込み、データ状態を確認してください。

```
確認項目:
- 動画数
- チャンネル数
- 最終取得日（fetched_at列）
```

7日以上経過している場合は警告を表示。

### Step 2: 優秀動画抽出

videos.csv から以下の条件で抽出:

```
performance_ratio >= 2.0
（再生数 / 登録者数 >= 2倍）
```

performance_ratio で降順ソートし、上位30件を取得。

### Step 3: パターン分析

research-agent の Phase 3 に従って分析:

1. **タイトル構造分析**
   - 【】内のパターン
   - 数字の使い方
   - フックワード

2. **テーマ傾向**
   - ツール名
   - ターゲット層
   - ベネフィット

3. **成功チャンネル**
   - 小規模で高ratio

### Step 4: 参考タイトル選定

video-concept-agent 用に10件選定。

選定基準:
- ratio 5倍以上
- 構造が再現可能
- 入力テーマとの関連性

### Step 5: 出力

以下のファイルを生成:

```
research/analysis/YYYYMMDD_[テーマ].md   # 分析レポート
research/reference_titles.md              # 参考タイトル一覧
```

---

## データ更新が必要な場合

```bash
cd research
export YOUTUBE_API_KEY='YOUR_KEY'
python3 channel_manager.py fetch --top 10
```

---

## 連携

このコマンドの出力は以下で使用:

- `/video-concept` → 参考タイトルとして使用
- `title-strategist-agent` → 成功パターンとして使用

---

## 入力例

```
/research AIエージェント
```

## 出力例

```
## 優秀動画TOP10（AIエージェント関連）

| # | タイトル | Ratio |
|---|---------|-------|
| 1 | 【9割の社長が熱望】万能AIエージェントに仕事を丸投げする方法 | 39.5x |
| 2 | 【非エンジニアでもOK】AIエージェントを構築してみる | 18.0x |
...

## 参考タイトル → research/reference_titles.md に出力完了
```
