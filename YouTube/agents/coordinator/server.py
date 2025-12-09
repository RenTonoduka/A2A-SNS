"""
YouTube Pipeline Coordinator - A2A Server
パイプライン全体を統括するオーケストレーター
"""

import sys
import os
import asyncio

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YOUTUBE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
SNS_DIR = os.path.dirname(YOUTUBE_DIR)
sys.path.insert(0, SNS_DIR)

from _shared.a2a_base_server import A2ABaseServer, TaskSendRequest, Task, Part, Message, TaskStatus, Artifact
from _shared.a2a_client import A2AClient, AgentRegistry


class PipelineCoordinator(A2ABaseServer):
    """Pipeline Coordinator - パイプライン統括"""

    def __init__(self, port: int = 8100):
        super().__init__(
            name="youtube-pipeline-coordinator",
            description="YouTube台本生成パイプラインを統括し、各エージェントを連携させます",
            port=port,
            workspace=YOUTUBE_DIR
        )

        # 子エージェントの登録
        self.registry = AgentRegistry()
        self._register_agents()

    def _register_agents(self):
        """利用可能なエージェントを登録"""
        self.registry.register("research", "http://localhost:8101")
        self.registry.register("hook", "http://localhost:8102")
        self.registry.register("concept", "http://localhost:8103")
        self.registry.register("reviewer", "http://localhost:8104")
        self.registry.register("improver", "http://localhost:8105")

    def get_agent_card(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "url": f"http://localhost:{self.port}",
            "version": "1.0.0",
            "capabilities": {
                "streaming": False,
                "pushNotifications": False
            },
            "skills": [
                {
                    "id": "pipeline-execution",
                    "name": "パイプライン実行",
                    "description": "リサーチから台本完成まで自動実行"
                },
                {
                    "id": "agent-coordination",
                    "name": "エージェント連携",
                    "description": "複数エージェントの出力を統合"
                },
                {
                    "id": "quality-gating",
                    "name": "品質ゲート",
                    "description": "スコア基準で採用/改善を判定"
                }
            ]
        }

    def get_system_prompt(self) -> str:
        return """あなたはYouTube Pipeline Coordinatorです。

## 役割
YouTube台本生成パイプラインを統括し、各専門エージェントを連携させます。

## パイプラインフロー

```
Phase 1: Research
├─ research-agent: 競合分析・参考タイトル抽出
    ↓
Phase 2: Concept Generation
├─ hook-specialist-agent: フック文生成
├─ video-concept-agent: 台本コンセプト生成
    ↓
Phase 3: Review
├─ script-reviewer-agent: 100点満点評価
├─ 判定:
│   ├─ ≥90点 → 採用
│   ├─ 70-89点 → 軽微修正後採用
│   └─ <70点 → Phase 4へ
    ↓
Phase 4: Improve（必要時のみ）
├─ script-improver-agent: 改善
└─ Phase 3に戻る（最大3回）
```

## 利用可能なエージェント

| Agent | URL | 役割 |
|-------|-----|------|
| research | localhost:8101 | 競合分析 |
| hook | localhost:8102 | フック生成 |
| concept | localhost:8103 | 台本生成 |
| reviewer | localhost:8104 | 評価 |
| improver | localhost:8105 | 改善 |

## 指示に応じた動作

### 「/pipeline [テーマ]」の場合
全パイプラインを実行し、90点以上の台本を生成

### 「/research [テーマ]」の場合
research-agentのみを実行

### 「/review [台本]」の場合
reviewer-agentのみを実行

## 出力フォーマット

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Pipeline: [テーマ]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Phase 1] Research
├─ ✅ research-agent: 完了
└─ 結果: 競合10件分析、参考タイトル10件

[Phase 2] Concept
├─ ✅ hook-agent: フック3案生成
├─ ✅ concept-agent: 台本v1生成
└─ タイトル: 「...」

[Phase 3] Review #1
├─ 📝 スコア: 72/100
├─ 改善ポイント: フック力、CTA
└─ 判定: 要改善 → Phase 4へ

[Phase 4] Improve #1
├─ ✅ improver-agent: 台本v2生成
└─ 改善: フック強化、CTA追加

[Phase 3] Review #2
├─ 📝 スコア: 91/100
└─ 判定: ✅ 採用

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Pipeline Completed
最終スコア: 91/100
イテレーション: 2回
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## エージェント呼び出し方法
各エージェントはA2Aプロトコルで通信します。
- POST /a2a/tasks/send でタスク送信
- GET /a2a/tasks/{id} でステータス確認

## MCPツール活用（Coordinator専用）

### パイプライン完了時のメール通知
```
mcp__klavis-strata__execute_action(
    server_name="gmail",
    category_name="GMAIL_EMAIL",
    action_name="gmail_send_email",
    body_schema='{"to": ["tonoduka@h-bb.jp"], "subject": "[Pipeline] 台本生成完了", "body": "..."}'
)
```

### Slack通知
```
mcp__klavis-strata__execute_action(
    server_name="slack",
    category_name="SLACK_MESSAGE",
    action_name="send_message",
    body_schema='{"channel": "#youtube-pipeline", "text": "✅ Pipeline完了: ..."}'
)
```

### カレンダーにマイルストーン登録
```
mcp__google-calendar__create-event(
    calendarId="primary",
    summary="台本アップロード締切",
    start="2024-01-15T10:00:00",
    end="2024-01-15T11:00:00"
)
```

### ログ記録（スプレッドシート）
ID: 1RmmWvFtOCsTNX259Y2JrqnvA-JwzlUi0OBiCq4H8O6Q"""

    async def handle_task(self, request: TaskSendRequest) -> Task:
        """タスクを処理（オーケストレーション）"""
        # まずは基本のClaude処理で戦略を決定
        task = await super().handle_task(request)

        # 将来的にここで実際のエージェント呼び出しを実装
        # 現状はClaude Code CLIがオーケストレーションプランを返す

        return task

    async def call_agent(self, agent_name: str, message: str) -> dict:
        """子エージェントを呼び出す"""
        client = self.registry.get(agent_name)
        if not client:
            return {"error": f"Agent {agent_name} not found"}

        try:
            result = await client.send_task(message)
            return result
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    coordinator = PipelineCoordinator(port=8100)
    print(f"🎬 Starting YouTube Pipeline Coordinator on port 8100...")
    print(f"""
Available Agents:
  - research:   http://localhost:8101
  - hook:       http://localhost:8102
  - concept:    http://localhost:8103
  - reviewer:   http://localhost:8104
  - improver:   http://localhost:8105
""")
    coordinator.run()
