# YouTube Auto Pipeline - 自動台本生成システム

## 概要

チャンネルリスト（`research/data/channels.csv`）から優秀動画を分析し、自動で台本を生成するパイプラインシステムです。

## 出力ディレクトリ構造

```
output/
├── scripts/    # 生成中の台本・リサーチ結果
├── concepts/   # フック文・コンセプト
├── reviews/    # レビュー結果
└── final/      # 完成台本（90点以上）
```

**完成した台本は `output/final/` に保存されます**

ファイル名形式: `{YYYYMMDD_HHMMSS}_{テーマ}_FINAL_{スコア}pts.md`

## 使い方

### 1. 手動実行（特定テーマ）

```bash
cd YouTube
python pipeline_runner.py run --theme "AI活用で副業を始める方法"
```

### 2. 自動テーマ生成＆実行

チャンネルリストから優秀動画を分析し、テーマを自動生成：

```bash
python pipeline_runner.py auto --count 1
# --count: 生成する台本数（デフォルト1）
# --hint: テーマ生成のヒント（任意）
```

### 3. エージェント状態確認

```bash
python pipeline_runner.py check
```

### 4. クイックテスト

```bash
python quick_test.py
```

## 定期実行の設定

毎日9時に自動実行するには：

```bash
# plistファイルをlaunchdディレクトリにコピー
cp com.youtube.autopipeline.plist ~/Library/LaunchAgents/

# サービス登録
launchctl load ~/Library/LaunchAgents/com.youtube.autopipeline.plist

# 確認
launchctl list | grep youtube

# 停止する場合
launchctl unload ~/Library/LaunchAgents/com.youtube.autopipeline.plist
```

## パイプラインフロー

```
1. Research Agent (8101)
   └─> 競合分析・視聴者インサイト

2. Hook Agent (8102) + Concept Agent (8103) [並列]
   ├─> フック文生成
   └─> PASTOR/AREAフレームワーク台本

3. Reviewer Agent (8104)
   └─> 5軸100点満点評価

4. [スコア < 90点の場合]
   Improver Agent (8105)
   └─> 低スコア軸を重点改善
   └─> → Reviewer (ループ: 最大3回)

5. 最終出力
   └─> output/final/ に保存
```

## 注意事項

- エージェントはClaude Code CLIを使用するため、各処理に数分かかります
- デフォルトタイムアウト: 600秒（10分）
- 全エージェントが起動している必要があります（`./start_agents.sh`）

## トラブルシューティング

### エージェントが起動しない場合

```bash
# ログ確認
tail -f logs/research.log

# 全エージェント再起動
./stop_agents.sh && ./start_agents.sh
```

### タイムアウトエラー

`pipeline_runner.py`のタイムアウト値を調整：

```python
runner = PipelineRunner(timeout=900)  # 15分に延長
```

## 関連ファイル

- `pipeline_runner.py` - メインパイプラインクラス
- `auto_pipeline.sh` - 自動実行ラッパースクリプト
- `quick_test.py` - エージェント動作確認
- `start_agents.sh` - 全エージェント起動
- `stop_agents.sh` - 全エージェント停止
- `research/data/channels.csv` - 分析対象チャンネルリスト
