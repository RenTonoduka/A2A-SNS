"""
SNS Orchestrator Agent
SNS運用全体を統括し、適切なエージェントにタスクを振り分ける
"""

import sys
import os

# 親ディレクトリをパスに追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SNS_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SNS_DIR)

from _shared.a2a_base_server import A2ABaseServer, TaskSendRequest, Task, Part, Message, TaskStatus, Artifact
from _shared.a2a_client import A2AClient, AgentRegistry


class SNSOrchestratorAgent(A2ABaseServer):
    """SNS統括エージェント"""

    def __init__(self, port: int = 8080):
        super().__init__(
            name="sns-orchestrator",
            description="SNS運用を統括し、各プラットフォーム専門エージェントにタスクを振り分けます",
            port=port,
            workspace="."
        )

        # 子エージェントの登録
        self.registry = AgentRegistry()
        self._register_agents()

    def _register_agents(self):
        """利用可能なエージェントを登録"""
        # YouTube エージェント群
        self.registry.register("youtube-script-writer", "http://localhost:8081")
        self.registry.register("youtube-shorts-creator", "http://localhost:8082")
        self.registry.register("youtube-seo-optimizer", "http://localhost:8083")
        self.registry.register("youtube-thumbnail-planner", "http://localhost:8084")

        # 今後追加予定
        # self.registry.register("x-post-creator", "http://localhost:8090")
        # self.registry.register("instagram-post-creator", "http://localhost:8100")

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
                    "id": "sns-strategy",
                    "name": "SNS戦略立案",
                    "description": "SNS横断でのコンテンツ戦略を立案"
                },
                {
                    "id": "task-routing",
                    "name": "タスク振り分け",
                    "description": "適切な専門エージェントにタスクを振り分け"
                },
                {
                    "id": "youtube-coordination",
                    "name": "YouTube運用統括",
                    "description": "YouTube関連の制作タスクを統括"
                }
            ]
        }

    def get_system_prompt(self) -> str:
        return """あなたはSNS運用を統括するオーケストレーターエージェントです。

## 役割
- ユーザーのSNS関連リクエストを分析
- 適切な専門エージェントを選択してタスクを振り分け
- 複数エージェントの結果を統合して最終成果物を作成

## 利用可能な専門エージェント

### YouTube
- youtube-script-writer: 動画台本・構成作成
- youtube-shorts-creator: Shorts企画・スクリプト
- youtube-seo-optimizer: タイトル・説明・タグ最適化
- youtube-thumbnail-planner: サムネイル企画・構成案

### 今後追加予定
- X (Twitter) エージェント群
- Instagram エージェント群
- TikTok エージェント群
- LINE エージェント群

## 応答形式
1. リクエストを分析
2. 必要なエージェントを特定
3. タスクプランを提示
4. 実行（または実行指示）

日本語で丁寧に応答してください。"""

    async def handle_task(self, request: TaskSendRequest) -> Task:
        """タスクを処理（オーケストレーション）"""
        # 基本のタスク処理を実行
        task = await super().handle_task(request)

        # TODO: 将来的に子エージェントへの自動振り分けを実装
        # 現状はClaude Code CLIが戦略とタスクプランを返す

        return task


if __name__ == "__main__":
    agent = SNSOrchestratorAgent(port=8080)
    print(f"Starting SNS Orchestrator Agent on port 8080...")
    agent.run()
