# Phase 1: データ収集・監視システム

## 概要

登録チャンネル（`research/data/channels.csv`）を監視し、新着動画の検出、データ収集、トレンド分析を自動化するシステムです。

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    Phase 1: Data Collection                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐      ┌─────────────────┐              │
│  │ Channel Monitor │ ───▶ │ Video Collector │              │
│  │    (8110)       │      │    (8111)       │              │
│  │                 │      │                 │              │
│  │ ・チャンネル監視 │      │ ・動画情報取得  │              │
│  │ ・新着検知      │      │ ・CSV更新      │              │
│  │ ・統計更新      │      │ ・PR計算       │              │
│  └─────────────────┘      └────────┬────────┘              │
│                                    │                       │
│                                    ▼                       │
│                          ┌─────────────────┐              │
│                          │ Trend Analyzer  │              │
│                          │    (8112)       │              │
│                          │                 │              │
│                          │ ・バズ動画検出  │              │
│                          │ ・キーワード分析│              │
│                          │ ・トレンド抽出  │              │
│                          └─────────────────┘              │
│                                    │                       │
│                                    ▼                       │
│                        【Phase 2へ: 台本生成】              │
└─────────────────────────────────────────────────────────────┘
```

## エージェント

### 1. Channel Monitor (Port 8110)
- **役割**: 登録チャンネルの監視・新着検知
- **機能**:
  - チャンネル状態確認（登録者数・動画数）
  - 新着動画の検出
  - channels.csvの更新

### 2. Video Collector (Port 8111)
- **役割**: 動画情報の収集・保存
- **機能**:
  - 動画メタデータ取得
  - videos.csvへの追加・更新
  - performance_ratio計算

### 3. Trend Analyzer (Port 8112)
- **役割**: バズ動画分析・トレンド抽出
- **機能**:
  - バズ動画ランキング
  - キーワード分析
  - 推奨テーマ提案

## データファイル

```
research/data/
├── channels.csv     # 監視対象チャンネル（36件）
├── videos.csv       # 収集済み動画データ
├── fetch_log.csv    # 取得履歴
└── trends/          # トレンド分析結果
```

### performance_ratio (PR)

バズ動画の指標:
```
PR = view_count / subscriber_count
```

| ランク | PR範囲 | 評価 |
|--------|--------|------|
| S | >= 10.0 | 大バズ |
| A | >= 5.0 | バズ |
| B | >= 2.0 | 好調 |
| C | >= 1.0 | 平均 |
| D | < 1.0 | 低調 |

## 使い方

### エージェント起動

```bash
cd YouTube
./start_phase1_agents.sh
```

### パイプライン実行

```bash
# フル実行（監視→収集→分析）
python data_collection_runner.py run

# 状態確認
python data_collection_runner.py status

# チャンネル監視のみ
python data_collection_runner.py monitor

# 動画収集のみ
python data_collection_runner.py collect

# トレンド分析のみ
python data_collection_runner.py analyze
```

### エージェント停止

```bash
./stop_phase1_agents.sh
```

## 出力

レポートは `output/reports/` に保存:
- `YYYYMMDD_HHMMSS_data_collection.json` - フルパイプライン結果
- `YYYYMMDD_HHMMSS_trend_analysis.json` - トレンド分析結果

## Phase 2への連携

トレンド分析で抽出された「推奨テーマ」を元に、Phase 2（台本生成パイプライン）を実行:

```bash
# Phase 2 エージェント起動
./start_agents.sh

# 推奨テーマで台本生成
python pipeline_runner.py run --theme "Trend Analyzerが提案したテーマ"
```

## 定期実行

毎日自動でデータ収集を行う場合:

```bash
# cron設定例（毎日9時に実行）
0 9 * * * cd /path/to/YouTube && ./start_phase1_agents.sh && sleep 5 && python data_collection_runner.py run && ./stop_phase1_agents.sh
```

## トラブルシューティング

### エージェントが起動しない

```bash
# ログ確認
tail -f logs/channel_monitor.log
tail -f logs/video_collector.log
tail -f logs/trend_analyzer.log
```

### タイムアウトエラー

```bash
# タイムアウト延長（15分）
python data_collection_runner.py run --timeout 900
```

## 関連ファイル

- `agents/channel_monitor/server.py` - Channel Monitor
- `agents/video_collector/server.py` - Video Collector
- `agents/trend_analyzer/server.py` - Trend Analyzer
- `data_collection_runner.py` - パイプラインランナー
- `start_phase1_agents.sh` - 起動スクリプト
- `stop_phase1_agents.sh` - 停止スクリプト
