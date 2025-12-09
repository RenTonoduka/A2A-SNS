# /improve-organization コマンド

エージェント組織を自己改善する継続的改善サイクルを実行

## 使用方法

```
/improve-organization              # 1回実行
/improve-organization 3            # 3回繰り返し
/improve-organization --continuous # 90点達成まで継続
```

## 実行手順

このコマンドは `organization-improver-agent` を起動し、パイプラインのボトルネックを検出して自動改善します。

---

### Step 1: 現状分析

**収集するデータ**:
1. 直近のパイプライン実行結果
2. 各エージェントの成功率・所要時間
3. スコアの軸別内訳
4. 失敗パターンの傾向

**分析観点**:
- 平均スコアが90点未満の軸は？
- ボトルネックになっているエージェントは？
- 繰り返し発生する失敗パターンは？

---

### Step 2: ギャップ検出

**検出ロジック**:

```
if 軸スコア < 15/満点:
    → 特化エージェント作成

if エージェント成功率 < 70%:
    → エージェント強化 or 分割

if 失敗パターン発生率 > 30%:
    → 対策エージェント作成
```

**出力例**:
```
検出されたギャップ:
1. 🔴 具体性スコア低い（12/20） → data-enrichment-agent 作成
2. 🟡 フック失敗率40% → hook-specialist-agent 作成
3. 🟡 CTA不足（10/15） → cta-optimizer-agent 作成
```

---

### Step 3: 改善計画立案

**計画内容**:
1. 新エージェントの仕様設計
2. 既存エージェントの強化ポイント
3. パイプライン統合方法

**優先順位**:
| 優先度 | 条件 | 対応 |
|--------|------|------|
| 緊急 | 成功率 < 50% | 即座に対応 |
| 高 | スコア < 50% | 今サイクルで対応 |
| 中 | 失敗率 > 30% | 今サイクルで対応 |
| 低 | 改善余地あり | 次サイクル |

---

### Step 4: 自動実装

**実行内容**:
1. `agent-factory-agent` で新エージェント作成
2. 対応するコマンド.md作成
3. `pipeline-coordinator-agent.md` 更新
4. 連携先エージェントの更新

**作成されるファイル例**:
```
.claude/agents/hook-specialist-agent.md
.claude/agents/data-enrichment-agent.md
.claude/commands/hook-generate.md
.claude/commands/enrich-data.md
```

---

### Step 5: 検証

**検証方法**:
1. 改善版パイプラインでテスト実行
2. スコアの変化を確認
3. 改善効果を測定

**成功基準**:
- スコアが前回より向上
- 失敗率が減少
- 所要時間が増加しすぎていない

---

### Step 6: 学習記録

**保存先**:
```
.claude/memory/improvements/YYYYMMDD_cycleN.md
```

**記録内容**:
- 検出された問題
- 実施した改善
- 結果（Before/After）
- 学習事項

---

## 出力例

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 Organization Improvement Cycle #1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Step 1] 現状分析
├─ 直近5回のパイプライン結果を分析
├─ 平均スコア: 78/100
├─ 成功率（90点以上）: 60%
└─ ボトルネック: video-concept-agent (45min)

[Step 2] ギャップ検出
├─ 🔴 具体性: 12/20 → data-enrichment-agent 必要
├─ 🟡 フック: 失敗率40% → hook-specialist-agent 必要
└─ 🟡 CTA: 10/15 → cta-optimizer-agent 必要

[Step 3] 改善計画
├─ 優先度1: hook-specialist-agent 作成
├─ 優先度2: data-enrichment-agent 作成
└─ 優先度3: video-concept-agent 入力強化

[Step 4] 自動実装
├─ ✅ .claude/agents/hook-specialist-agent.md 作成
├─ ✅ .claude/agents/data-enrichment-agent.md 作成
├─ ✅ .claude/commands/hook-generate.md 作成
├─ ✅ .claude/commands/enrich-data.md 作成
└─ ✅ pipeline-coordinator-agent.md 更新

[Step 5] 検証
├─ テスト実行: AIエージェント自動化
├─ スコア: 87/100 (+9)
└─ 成功率: 80% (+20%)

[Step 6] 学習記録
└─ ✅ .claude/memory/improvements/20251209_cycle1.md 保存

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Cycle #1 完了
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 改善サマリー

| 指標 | Before | After | 改善 |
|------|--------|-------|------|
| 平均スコア | 78 | 87 | +12% |
| 成功率 | 60% | 80% | +33% |

## 追加エージェント

1. hook-specialist-agent - フック文専門生成
2. data-enrichment-agent - 数値データ付与

## 次サイクル候補

- CTA最適化エージェント
- 差別化強化エージェント
```

---

## オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| [回数] | 改善サイクル回数 | 1 |
| `--continuous` | 90点達成まで継続 | false |
| `--dry-run` | 計画のみ表示（実装しない） | false |
| `--focus [軸]` | 特定軸に集中改善 | 全軸 |

---

## 連携

- 入力: パイプライン実行結果
- 使用: `organization-improver-agent`, `agent-factory-agent`
- 出力: 新エージェント群、改善されたパイプライン
