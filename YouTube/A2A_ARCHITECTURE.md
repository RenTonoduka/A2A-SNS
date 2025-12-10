# A2A統合アーキテクチャ設計書

## 概要

全Phase（0-4）を真のA2Aプロトコルで統合し、人間の介入なしで完全自動化を実現する。

---

## 現状 vs 新アーキテクチャ

### Before（現状）

```
┌─────────────────────────────────────────────────────────┐
│  auto_scheduler.py (Python)                              │
│       │                                                  │
│       ├─ ChannelManager.auto_discover_buzz()            │
│       │     └─ 直接Python関数呼び出し（A2Aではない）      │
│       │                                                  │
│       └─ pipeline_runner.run_from_buzz()                │
│             └─ HTTP POST（個別呼び出し、連携なし）        │
│                                                          │
│  ※ エージェントは起動してるけど使われてない              │
│  ※ Phase間でデータが引き継がれない                      │
└─────────────────────────────────────────────────────────┘
```

### After（新アーキテクチャ）

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Master Coordinator (8099)               │   │
│  │           = 全Phase統括オーケストレーター          │   │
│  └────────────────────┬─────────────────────────────┘   │
│                       │                                  │
│         ┌─────────────┼─────────────┐                   │
│         │ A2A         │ A2A         │ A2A              │
│         ▼             ▼             ▼                   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐          │
│  │  Phase 0   │ │  Phase 1   │ │  Phase 2   │          │
│  │ Scheduler  │→│   Data     │→│  Script    │          │
│  │  (8100)    │ │  (8110-)   │ │  (8101-)   │          │
│  └────────────┘ └────────────┘ └────────────┘          │
│         │             │             │                   │
│         └─────────────┴─────────────┘                   │
│                       │                                  │
│              A2A Protocol で                            │
│              データ受け渡し                              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## エージェント一覧（ポート番号）

### Master Coordinator
| ポート | エージェント | 役割 |
|--------|-------------|------|
| 8099 | master-coordinator | 全Phase統括、自動トリガー |

### Phase 0: スケジューリング
| ポート | エージェント | 役割 |
|--------|-------------|------|
| 8100 | scheduler-agent | 定期実行、バズ検出トリガー |

### Phase 1: データ収集
| ポート | エージェント | 役割 |
|--------|-------------|------|
| 8110 | channel-monitor | チャンネル監視 |
| 8111 | video-collector | 動画データ収集 |
| 8112 | trend-analyzer | トレンド分析・バズ検出 |
| 8114 | self-analyzer | 自チャンネル分析 |
| 8115 | marketing-analytics | KPI分析 |
| 8116 | style-learner | スタイル学習 |

### Phase 2: 台本生成
| ポート | エージェント | 役割 |
|--------|-------------|------|
| 8101 | research-agent | 競合分析 |
| 8102 | hook-agent | フック文生成 |
| 8103 | concept-agent | 台本コンセプト |
| 8113 | script-writer | 本編作成 |

### Phase 3-4: レビュー・改善
| ポート | エージェント | 役割 |
|--------|-------------|------|
| 8104 | reviewer-agent | 100点満点評価 |
| 8105 | improver-agent | 台本改善 |

---

## A2A通信フロー

### 1. 定期トリガー（毎30分）

```
Master Coordinator (8099)
    │
    │ [A2A] POST /a2a/tasks/send
    │ {"message": "定期バズチェックを実行"}
    ▼
Scheduler Agent (8100)
    │
    │ [A2A] POST /a2a/tasks/send
    │ {"message": "チャンネル監視を実行"}
    ▼
Channel Monitor (8110)
    │
    │ [A2A Response]
    │ {"artifacts": [{"type": "data", "data": {"new_videos": [...]}}]}
    ▼
Video Collector (8111)
    │
    │ [A2A] 新着動画のデータ収集
    ▼
Trend Analyzer (8112)
    │
    │ [A2A Response]
    │ {"artifacts": [{"type": "data", "data": {
    │     "buzz_videos": [...],
    │     "trends": {...}
    │ }}]}
    ▼
Master Coordinator (8099)
    │
    │ バズ動画あり？ → Phase 2 へ
    ▼
Script Pipeline (8101→8102→8103→8113)
    │
    │ [A2A] 前Phaseの出力を次に渡す
    ▼
Review & Improve Loop (8104 ⇄ 8105)
    │
    │ [A2A] スコア < 90 → 改善ループ
    ▼
完成台本 + メール通知
```

---

## Phase間データフォーマット

### Phase 0 → Phase 1

```json
{
  "trigger": "scheduled",
  "timestamp": "2024-12-11T09:00:00+09:00",
  "action": "full_check"
}
```

### Phase 1 → Phase 2

```json
{
  "buzz_videos": [
    {
      "video_id": "xxxxx",
      "title": "バズ動画タイトル",
      "channel_name": "チャンネル名",
      "view_count": 500000,
      "subscriber_count": 100000,
      "performance_ratio": 5.0,
      "published_at": "2024-12-10T10:00:00Z",
      "transcript": "動画のトランスクリプト..."
    }
  ],
  "trends": {
    "keywords": ["AI", "Claude", "自動化"],
    "patterns": ["数字型タイトル", "疑問形"]
  },
  "recommended_themes": [
    "Claude活用術 初心者編",
    "AI副業 2024年最新"
  ]
}
```

### Phase 2 → Phase 3

```json
{
  "theme": "Claude活用術 初心者編",
  "draft_script": "台本テキスト...",
  "hook_options": [
    "知らないと損！",
    "なぜ今Claudeなのか"
  ],
  "title_options": [
    "【完全版】Claude活用術",
    "Claude入門ガイド"
  ],
  "reference_videos": [
    {"video_id": "xxxxx", "pr_ratio": 5.0}
  ]
}
```

### Phase 3 → Phase 4（改善時）

```json
{
  "current_score": 72,
  "evaluation": {
    "hook": 15,
    "structure": 18,
    "specificity": 12,
    "differentiation": 12,
    "cta": 15
  },
  "improvements_needed": [
    "フック力が弱い - 数字や具体性を追加",
    "具体性不足 - データや事例を追加"
  ],
  "current_script": "現在の台本..."
}
```

### Phase 4 → Phase 3（再評価）

```json
{
  "improved_script": "改善後の台本...",
  "changes_made": [
    "フックを「3分で分かる」に変更",
    "具体的な数値（87%の人が...）を追加"
  ],
  "iteration": 2
}
```

---

## Master Coordinator 実装方針

### 主要機能

1. **トリガー管理**
   - 定期実行（APScheduler統合）
   - バズ検出トリガー
   - 手動実行

2. **Phase連携**
   - A2Aでエージェント呼び出し
   - 結果を次Phaseに受け渡し
   - エラーハンドリング

3. **状態管理**
   - 実行履歴
   - 日次制限
   - 失敗リトライ

4. **通知**
   - バズ検出時
   - 台本完成時
   - エラー発生時

### コード構造

```
agents/
└── master_coordinator/
    ├── server.py         # A2Aサーバー
    ├── orchestrator.py   # Phase連携ロジック
    ├── scheduler.py      # 定期実行
    └── state.py          # 状態管理
```

---

## 実装ステップ

### Step 1: Master Coordinator 作成
- [ ] server.py（A2Aエンドポイント）
- [ ] orchestrator.py（Phase連携）

### Step 2: Phase 0 A2A化
- [ ] scheduler-agent として auto_scheduler.py を再実装
- [ ] A2Aで Trend Analyzer を呼び出し

### Step 3: Phase 1 連携
- [ ] Channel Monitor → Video Collector → Trend Analyzer のA2A連携
- [ ] 結果を Master Coordinator に返却

### Step 4: Phase 2-4 統合
- [ ] 既存の pipeline_runner.py ロジックをA2A化
- [ ] Review-Improve ループをA2A連携

### Step 5: テスト
- [ ] 単体テスト（各エージェント）
- [ ] 統合テスト（フルパイプライン）

---

## 起動方法（予定）

```bash
# 全システム起動
./start_a2a_system.sh

# または個別起動
python agents/master_coordinator/server.py  # 8099
python agents/scheduler/server.py           # 8100 (新規)
./start_phase1_agents.sh                    # 8110-8116
./start_agents.sh                           # 8101-8105, 8113

# 手動トリガー
curl -X POST http://localhost:8099/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -d '{"message": {"role": "user", "parts": [{"type": "text", "text": "フルパイプラインを実行"}]}}'
```

---

## 次のアクション

1. Master Coordinator の実装開始
2. 設計レビュー後に Phase 0 A2A 化
