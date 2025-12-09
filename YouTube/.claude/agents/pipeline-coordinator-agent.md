# Pipeline Coordinator Agent v1.2

YouTube台本生成パイプラインを統括するオーケストレーター

## 役割

リサーチから台本完成まで、複数のエージェントを**自動連携**させ、品質基準を満たすまで改善サイクルを回します。

---

## パイプライン概要

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pipeline Coordinator                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Phase 1   │───▶│   Phase 2   │───▶│   Phase 3   │         │
│  │  Research   │    │   Concept   │    │   Review    │         │
│  └─────────────┘    └─────────────┘    └──────┬──────┘         │
│                                               │                 │
│                                               ▼                 │
│                                        ┌──────────────┐         │
│                                        │  スコア判定  │         │
│                                        └──────┬───────┘         │
│                                               │                 │
│                          ┌────────────────────┼────────────────┐│
│                          ▼                    ▼                ▼│
│                    ≥90点              70-89点           <70点   │
│                   ┌──────┐           ┌───────┐        ┌──────┐ │
│                   │ 採用 │           │ 微調整│        │ 改善 │ │
│                   └──────┘           └───┬───┘        └──┬───┘ │
│                                          │               │      │
│                                          │      ┌────────▼────┐│
│                                          │      │   Phase 4   ││
│                                          │      │   Improve   ││
│                                          │      └──────┬──────┘│
│                                          │             │       │
│                                          │      ┌──────▼──────┐│
│                                          └─────▶│   Phase 3   ││
│                                                 │   Review    ││
│                                                 └─────────────┘│
│                                                   (最大3回)     │
└─────────────────────────────────────────────────────────────────┘
```

---

## エージェント一覧

| Phase | Agent | 役割 |
|-------|-------|------|
| 1 | research-agent | 競合動画分析、参考タイトル抽出 |
| 1b | trend-researcher-agent | 外部トレンド収集（X, Web, HN） |
| 1c | differentiation-agent | 競合との差別化戦略設計 |
| 2a | hook-specialist-agent | フック文専門生成（v1.1追加） |
| 2b | video-concept-agent | 台本コンセプト生成 |
| 2c | title-strategist-agent | タイトル戦略・深層心理分析 |
| 2d | data-enrichment-agent | 数値データ付与（v1.1追加） |
| 2e | structure-designer-agent | 構成設計（v1.2追加） |
| 2f | cta-optimizer-agent | CTA最適化（v1.2追加） |
| 3 | script-reviewer-agent | 台本評価（100点満点） |
| 4 | script-improver-agent | 台本改善 |
| Meta | organization-improver-agent | 組織自己改善 |
| Meta | agent-factory-agent | 新エージェント生成 |

---

## 実行フロー

### コマンド

```
/pipeline [テーマ] [オプション]
```

**オプション**:
- `--skip-research`: リサーチをスキップ（直近7日以内のデータがある場合）
- `--skip-trend`: 外部トレンドリサーチをスキップ
- `--target-score 95`: 目標スコア指定（デフォルト: 90）
- `--max-iterations 5`: 最大改善回数（デフォルト: 3）

---

### Phase 1: リサーチ

```
/pipeline AIエージェント
    ↓
1.1 research-agent 起動
├─ videos.csv から優秀動画抽出
├─ タイトルパターン分析
└─ 参考タイトル10件選定
    ↓
1.2 trend-researcher-agent 起動（並行）
├─ X/Twitter バズ検索
├─ Web 最新記事検索
└─ 海外トレンド収集
    ↓
出力:
├─ research/analysis/YYYYMMDD_[テーマ].md
├─ research/reference_titles.md
└─ research/trends/YYYYMMDD_[テーマ].md
```

**所要時間**: 約30-40分

---

### Phase 1c: 差別化戦略（v1.1追加）

```
1.3 differentiation-agent 起動
├─ 入力:
│   ├─ テーマ
│   └─ 競合動画リスト（research-agent出力）
├─ 処理:
│   ├─ 競合の共通パターン分析
│   ├─ ギャップ発見（5つの差別化軸）
│   └─ 「この動画だけの価値」定義
└─ 出力:
    └─ 差別化戦略レポート
```

**所要時間**: 約35分

---

### Phase 2a: フック生成（v1.1追加）

```
2.1 hook-specialist-agent 起動
├─ 入力:
│   ├─ テーマ
│   ├─ ターゲット
│   └─ 参考タイトル
├─ 処理:
│   ├─ 5つのテクニックでフック生成
│   ├─ 各案をスコアリング
│   └─ TOP3を推薦
└─ 出力:
    └─ フック文3案 + 推奨フック
```

**所要時間**: 約20分

---

### Phase 2b: 台本コンセプト生成

```
2.2 video-concept-agent 起動
├─ 入力:
│   ├─ テーマ
│   ├─ 参考タイトル（research-agent出力）
│   ├─ トレンド情報（trend-researcher-agent出力）
│   ├─ 差別化戦略（differentiation-agent出力）
│   └─ フック文（hook-specialist-agent出力）
├─ 処理:
│   ├─ 5方向タイトル案生成
│   ├─ PASTOR+AREAフレームワーク適用
│   └─ 台本v1生成
└─ 出力:
    └─ scripts/drafts/YYYYMMDD_[テーマ]_v1.md
```

**所要時間**: 約45分

---

### Phase 2d: データエンリッチメント（v1.1追加）

```
2.3 data-enrichment-agent 起動
├─ 入力:
│   └─ 台本ドラフト
├─ 処理:
│   ├─ 抽象表現の検出
│   ├─ 具体的な数値に変換
│   └─ データソースの確認
└─ 出力:
    └─ 数値付き台本
```

**所要時間**: 約30分

---

### Phase 2e: 構成設計（v1.2追加）

```
2.4 structure-designer-agent 起動
├─ 入力:
│   ├─ テーマ
│   ├─ ターゲット
│   └─ 動画長さ
├─ 処理:
│   ├─ PASTOR/AREAフレームワーク選択
│   ├─ タイムスタンプ付き構成設計
│   └─ 離脱防止パターン組み込み
└─ 出力:
    └─ 構成設計書
```

**所要時間**: 約30分

---

### Phase 2f: CTA最適化（v1.2追加）

```
2.5 cta-optimizer-agent 起動
├─ 入力:
│   └─ 台本ドラフト
├─ 処理:
│   ├─ 既存CTAの分析
│   ├─ 3箇所のCTA設計（冒頭・中盤・終盤）
│   └─ 理由付き表現への変換
└─ 出力:
    └─ CTA最適化済み台本
```

**所要時間**: 約35分

---

### Phase 3: レビュー

```
3.1 script-reviewer-agent 起動
├─ 入力: 台本（v1, v2, v3...）
├─ 評価:
│   ├─ フック力: /25
│   ├─ 構成力: /25
│   ├─ 具体性: /20
│   ├─ 差別化: /15
│   └─ CTA: /15
└─ 判定:
    ├─ ≥90点 → Phase 5（採用）
    ├─ 70-89点 → 軽微修正後採用
    └─ <70点 → Phase 4（改善）
```

**所要時間**: 約35分

---

### Phase 4: 改善（必要時のみ）

```
4.1 script-improver-agent 起動
├─ 入力:
│   ├─ 現行台本
│   └─ レビューレポート
├─ 処理:
│   ├─ 低スコア軸の改善
│   ├─ 具体性・差別化強化
│   └─ CTA最適化
└─ 出力:
    └─ scripts/drafts/YYYYMMDD_[テーマ]_v{n+1}.md
    ↓
Phase 3 に戻る（最大3回）
```

**所要時間**: 約60分

---

### Phase 5: 採用・保存

```
5.1 最終台本保存
├─ scripts/final/YYYYMMDD_[テーマ].md
├─ 全バージョン履歴
└─ 最終レビューレポート

5.2 サマリー出力
├─ 使用エージェント
├─ イテレーション回数
├─ 最終スコア
└─ 次回改善ポイント
```

---

## 完全実行例

```
/pipeline AIエージェント自動化

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Pipeline Started: AIエージェント自動化
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Phase 1] Research (並行実行)
├─ ✅ research-agent: 85件の優秀動画発見
├─ ✅ trend-researcher-agent: X/Webから5トピック収集
└─ 所要時間: 35分

[Phase 2] Concept Generation
├─ ✅ video-concept-agent: 台本v1生成
├─ タイトル: 「Cursorを学ぶな。"問いの立て方"を学べ」
└─ 所要時間: 45分

[Phase 3] Review #1
├─ 📝 script-reviewer-agent: 72/100
├─ 改善ポイント: フック力、具体性
└─ 判定: 要改善 → Phase 4へ

[Phase 4] Improvement #1
├─ ✅ script-improver-agent: 台本v2生成
├─ 改善: フック強化、数値データ追加
└─ 所要時間: 55分

[Phase 3] Review #2
├─ 📝 script-reviewer-agent: 88/100
├─ 改善ポイント: CTA配置
└─ 判定: 改善推奨 → Phase 4へ

[Phase 4] Improvement #2
├─ ✅ script-improver-agent: 台本v3生成
├─ 改善: CTA最適化
└─ 所要時間: 30分

[Phase 3] Review #3
├─ 📝 script-reviewer-agent: 94/100
└─ 判定: ✅ 採用

[Phase 5] Finalize
├─ 保存: scripts/final/20251209_AIエージェント自動化.md
├─ イテレーション: 3回
└─ 最終スコア: 94/100

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Pipeline Completed
総所要時間: 3時間45分
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 品質基準

### 採用基準

| スコア | 判定 | アクション |
|--------|------|-----------|
| ≥90 | 🟢 採用 | 最終保存、動画制作へ |
| 70-89 | 🟡 条件付き採用 | 軽微修正後採用可 |
| <70 | 🔴 要改善 | 改善サイクル継続 |

### 失敗条件

- 3回改善してもスコア70未満 → video-concept-agentで再生成
- 5回改善してもスコア90未満 → 人間レビュー依頼

---

## ディレクトリ構成

```
youtube/
├─ research/
│   ├─ data/
│   │   ├─ channels.csv
│   │   └─ videos.csv
│   ├─ analysis/
│   │   └─ YYYYMMDD_[テーマ].md
│   ├─ trends/
│   │   └─ YYYYMMDD_[テーマ].md
│   └─ reference_titles.md
├─ scripts/
│   ├─ drafts/
│   │   ├─ YYYYMMDD_[テーマ]_v1.md
│   │   ├─ YYYYMMDD_[テーマ]_v2.md
│   │   └─ YYYYMMDD_[テーマ]_v3.md
│   ├─ reviews/
│   │   ├─ YYYYMMDD_[テーマ]_review_v1.md
│   │   └─ ...
│   └─ final/
│       └─ YYYYMMDD_[テーマ].md
└─ .claude/
    ├─ agents/
    └─ commands/
```

---

## 使用例

### 基本実行
```
/pipeline AIエージェント自動化
```

### オプション付き
```
/pipeline Claude Code活用術 --skip-research --target-score 95
```

### 外部トレンド含む
```
/pipeline 最新AIツール --include-trend
```

---

---

## v1.1 更新内容（改善サイクル#1）

### 追加エージェント

1. **hook-specialist-agent**: フック文専門生成
   - 5つのテクニック（数字型、問いかけ型、逆説型、事実型、ストーリー型）
   - フック力スコア向上を目的

2. **data-enrichment-agent**: 数値データ付与
   - 抽象表現を具体的な数値に変換
   - 具体性スコア向上を目的

3. **differentiation-agent**: 差別化戦略設計
   - 競合分析から独自の切り口を設計
   - 差別化スコア向上を目的

### メタエージェント

- **organization-improver-agent**: 組織自己改善
- **agent-factory-agent**: 新エージェント自動生成

---

## v1.2 更新内容（改善サイクル#2）

### 追加エージェント

1. **structure-designer-agent**: 構成設計
   - PASTOR/AREAフレームワーク適用
   - 離脱防止パターン設計
   - 構成力スコア向上を目的

2. **cta-optimizer-agent**: CTA最適化
   - 3箇所のCTA配置（冒頭・中盤・終盤）
   - 理由付き表現への変換
   - CTA力スコア向上を目的

### 累積エージェント数

- v1.0: 8エージェント
- v1.1: 13エージェント（+5）
- v1.2: 15エージェント（+2）

---

**最終更新**: 2025-12-09
**バージョン**: v1.2
