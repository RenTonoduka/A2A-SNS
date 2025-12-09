# 将来タスク - AWS本番構成

## 概要

現在のローカルA2Aエージェント群をAWS上でスケーラブルに展開し、SaaS化する構想。

## 目標アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                        Front-end Layer                          │
│                                                                 │
│   Next.js / V0 / 管理画面 / LP                                  │
│   「台本生成リクエスト」ボタン → API呼び出し                      │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST API / WebSocket
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Back-end Gateway                            │
│                                                                 │
│   FastAPI / Django / API Gateway + Lambda                       │
│   ┣━ 認証・課金管理                                              │
│   ┣━ ジョブキュー投入 (SQS / Redis)                              │
│   ┗━ 結果取得・通知                                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │ SQS / Redis Queue
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Agent Worker Cluster (EC2 / ECS)               │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │ Research     │  │ Hook         │  │ Concept      │         │
│   │ Agent EC2    │  │ Agent EC2    │  │ Agent EC2    │         │
│   │ Claude CLI   │  │ Claude CLI   │  │ Claude CLI   │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐                           │
│   │ Reviewer     │  │ Improver     │  ← Auto Scaling Group     │
│   │ Agent EC2    │  │ Agent EC2    │     負荷に応じて増減       │
│   │ Claude CLI   │  │ Claude CLI   │                           │
│   └──────────────┘  └──────────────┘                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │ 結果保存
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Storage Layer                            │
│                                                                 │
│   S3 (台本ファイル) / RDS (メタデータ) / DynamoDB (ジョブ状態)   │
└─────────────────────────────────────────────────────────────────┘
```

## タスク一覧

### Phase 1: インフラ基盤

- [ ] AWS VPC設計・構築
- [ ] EC2インスタンス用AMI作成（Claude CLI + Python環境）
- [ ] Auto Scaling Group設定
- [ ] SQSキュー作成（ジョブ管理用）
- [ ] S3バケット作成（台本保存用）
- [ ] RDS/DynamoDB設計（メタデータ・ジョブ状態）

### Phase 2: バックエンドAPI

- [ ] API Gateway / FastAPI構築
- [ ] 認証機能（JWT / Cognito）
- [ ] ジョブ投入エンドポイント
- [ ] 結果取得エンドポイント
- [ ] Webhook通知機能

### Phase 3: ワーカー実装

- [ ] SQSポーリング処理
- [ ] A2Aエージェント呼び出しロジック
- [ ] 結果S3保存処理
- [ ] エラーハンドリング・リトライ
- [ ] Dead Letter Queue設定

### Phase 4: フロントエンド

- [ ] 管理画面UI（Next.js）
- [ ] 台本生成リクエストフォーム
- [ ] ジョブ状態表示（リアルタイム）
- [ ] 完成台本一覧・ダウンロード
- [ ] 課金プラン選択UI

### Phase 5: SaaS化

- [ ] Stripe連携（課金）
- [ ] プラン別制限（月間生成数など）
- [ ] ユーザーダッシュボード
- [ ] 利用統計・分析
- [ ] LP作成

## 技術スタック案

| レイヤー | 技術 |
|---------|------|
| フロントエンド | Next.js 14 / Tailwind / shadcn/ui |
| バックエンド | FastAPI / API Gateway + Lambda |
| キュー | Amazon SQS |
| ワーカー | EC2 (t3.medium) + Auto Scaling |
| ストレージ | S3 / RDS PostgreSQL / DynamoDB |
| 認証 | Amazon Cognito / JWT |
| 課金 | Stripe |
| 監視 | CloudWatch / Datadog |
| CI/CD | GitHub Actions / AWS CodePipeline |

## コスト試算（月間）

| 項目 | 想定コスト |
|------|-----------|
| EC2 (t3.medium x 3) | ~$100 |
| RDS (db.t3.micro) | ~$15 |
| S3 | ~$5 |
| SQS | ~$1 |
| データ転送 | ~$10 |
| **合計** | **~$130/月** |

※ Claude API費用は別途

## 参考

- 現在のローカル実装: `pipeline_runner.py`
- A2Aエージェント: `agents/*/server.py`
- 共通基盤: `_shared/a2a_base_server.py`

## 更新履歴

- 2024-12-10: 初版作成
