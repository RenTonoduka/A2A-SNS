"""
A2A Client - 他のA2Aエージェントを呼び出すクライアント
"""

import httpx
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class A2AClient:
    """A2Aエージェントを呼び出すクライアント"""

    def __init__(self, base_url: str, timeout: float = 600.0):
        self.base_url = base_url.rstrip("/")
        # httpx.Timeoutで全タイムアウトを明示的に設定
        # connect=30秒、read=600秒、write=600秒、pool=600秒
        # LLM処理は時間がかかるため十分な待ち時間を確保
        self.timeout = httpx.Timeout(
            connect=30.0,
            read=timeout,
            write=timeout,
            pool=timeout
        )
        self._agent_card = None

    async def get_agent_card(self) -> dict:
        """Agent Cardを取得"""
        if self._agent_card:
            return self._agent_card

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.get(f"{self.base_url}/.well-known/agent.json")
            response.raise_for_status()
            self._agent_card = response.json()
            return self._agent_card

    async def send_task(
        self,
        message: str,
        task_id: Optional[str] = None,
        context_id: Optional[str] = None
    ) -> dict:
        """タスクを送信"""
        payload = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": message}]
            }
        }

        if task_id:
            payload["id"] = task_id
        if context_id:
            payload["contextId"] = context_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/a2a/tasks/send",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def get_task(self, task_id: str) -> dict:
        """タスク状態を取得"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/a2a/tasks/{task_id}")
            response.raise_for_status()
            return response.json()

    async def cancel_task(self, task_id: str) -> dict:
        """タスクをキャンセル"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/a2a/tasks/{task_id}/cancel")
            response.raise_for_status()
            return response.json()


class AgentRegistry:
    """複数のA2Aエージェントを管理"""

    def __init__(self):
        self.agents: Dict[str, A2AClient] = {}

    def register(self, name: str, url: str):
        """エージェントを登録"""
        self.agents[name] = A2AClient(url)

    def get(self, name: str) -> Optional[A2AClient]:
        """エージェントを取得"""
        return self.agents.get(name)

    async def discover_all(self) -> Dict[str, dict]:
        """全エージェントのAgent Cardを取得"""
        cards = {}
        for name, client in self.agents.items():
            try:
                cards[name] = await client.get_agent_card()
            except Exception as e:
                cards[name] = {"error": str(e)}
        return cards
