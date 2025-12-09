"""
A2A Base Server - Claude Code CLI wrapper
共通のA2Aサーバー基盤
MCP Tools統合対応
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import subprocess
import json
import uuid
import time
from datetime import datetime
from abc import ABC, abstractmethod

# 通知システム（オプション）
try:
    from .google_notifier import notify_start, notify_complete, notify_error
    NOTIFIER_AVAILABLE = True
except ImportError:
    NOTIFIER_AVAILABLE = False
    def notify_start(*args, **kwargs): pass
    def notify_complete(*args, **kwargs): pass
    def notify_error(*args, **kwargs): pass

# MCPツール統合（オプション）
try:
    from .mcp_tools import (
        generate_mcp_guide,
        get_mcp_system_prompt_addition,
        AGENT_MCP_TOOLS,
        LOG_SPREADSHEET_ID,
        NOTIFY_EMAIL
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    def generate_mcp_guide(agent_name): return ""
    def get_mcp_system_prompt_addition(agent_name): return ""
    AGENT_MCP_TOOLS = {}
    LOG_SPREADSHEET_ID = ""
    NOTIFY_EMAIL = ""


# ============================================
# A2A Protocol Models
# ============================================

class Part(BaseModel):
    """A2A Part - 最小コンテンツ単位"""
    type: str = "text"  # text, file, data
    text: Optional[str] = None
    file: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None


class Message(BaseModel):
    """A2A Message - 通信ターン"""
    role: str  # user, agent
    parts: List[Part]


class TaskStatus(BaseModel):
    """A2A Task Status"""
    state: str  # submitted, working, completed, failed, input_required
    message: Optional[Message] = None


class Artifact(BaseModel):
    """A2A Artifact - 出力成果物"""
    name: Optional[str] = None
    parts: List[Part]


class Task(BaseModel):
    """A2A Task - 作業単位"""
    id: str
    contextId: Optional[str] = None
    status: TaskStatus
    artifacts: List[Artifact] = []
    history: List[Message] = []


class TaskSendRequest(BaseModel):
    """タスク送信リクエスト"""
    id: Optional[str] = None
    message: Message
    contextId: Optional[str] = None


class AgentCard(BaseModel):
    """A2A Agent Card - エージェント情報"""
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    capabilities: Dict[str, Any] = {}
    skills: List[Dict[str, Any]] = []


# ============================================
# Claude Code CLI Wrapper
# ============================================

class ClaudeCodeCLI:
    """
    Claude Code CLIのラッパー
    フル機能モード: ファイル操作、Bash実行、Task tool（サブエージェント）、MCP統合
    """

    # 許可するツール（必要に応じて調整可能）
    DEFAULT_ALLOWED_TOOLS = [
        "Read", "Write", "Edit",      # ファイル操作
        "Bash",                        # コマンド実行
        "Glob", "Grep",               # 検索
        "Task",                        # サブエージェント起動
        "WebFetch", "WebSearch",      # Web検索
        "TodoWrite",                   # タスク管理
    ]

    # MCPツール（Klavis Strata経由で各種サービス連携）
    MCP_TOOLS = [
        "mcp__klavis-strata__discover_server_categories_or_actions",
        "mcp__klavis-strata__get_category_actions",
        "mcp__klavis-strata__get_action_details",
        "mcp__klavis-strata__execute_action",
        "mcp__klavis-strata__search_documentation",
        "mcp__exa__web_search_exa",           # Web検索
        "mcp__exa__get_code_context_exa",     # コード検索
        "mcp__google-calendar__list-events",  # カレンダー
        "mcp__google-calendar__create-event",
        "mcp__google-drive__search",          # Google Drive
        "mcp__google-drive__createGoogleDoc",
        "mcp__google-drive__createGoogleSheet",
        "mcp__google-drive__updateGoogleSheet",
    ]

    def __init__(
        self,
        workspace: str = ".",
        allowed_tools: Optional[List[str]] = None,
        enable_full_tools: bool = True,
        enable_mcp: bool = True,
        timeout: int = 300
    ):
        self.workspace = workspace
        self.enable_full_tools = enable_full_tools
        self.enable_mcp = enable_mcp
        self.timeout = timeout

        # ツールリスト構築
        base_tools = allowed_tools or self.DEFAULT_ALLOWED_TOOLS
        if enable_mcp:
            self.allowed_tools = base_tools + self.MCP_TOOLS
        else:
            self.allowed_tools = base_tools

    def execute(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_format: str = "text"
    ) -> str:
        """
        Claude Code CLIを実行（フル機能モード）

        Args:
            prompt: 実行するプロンプト
            system_prompt: エージェントの役割定義
            output_format: "text" | "json" | "stream-json"

        Returns:
            Claude Code CLIの出力結果
        """
        # system_promptがあれば前置き
        if system_prompt:
            full_prompt = f"【役割】\n{system_prompt}\n\n【依頼】\n{prompt}"
        else:
            full_prompt = prompt

        try:
            if self.enable_full_tools:
                # フル機能モード: -p でプロンプト指定、ツール実行可能
                cmd = [
                    "claude",
                    "-p", full_prompt,
                    "--output-format", output_format,
                    "--allowedTools", ",".join(self.allowed_tools),
                ]
            else:
                # テキスト生成のみモード（従来互換）
                cmd = ["claude", "--output-format", output_format]

            result = subprocess.run(
                cmd,
                input=None if self.enable_full_tools else full_prompt,
                capture_output=True,
                text=True,
                cwd=self.workspace,
                timeout=self.timeout
            )

            if result.returncode != 0:
                return f"Error: {result.stderr}"

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {self.timeout}s"
        except Exception as e:
            return f"Error: {str(e)}"

    def execute_with_task_tool(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        subagent_type: Optional[str] = None
    ) -> str:
        """
        Task tool（サブエージェント）を使用してタスクを実行

        Args:
            prompt: 実行するプロンプト
            system_prompt: エージェントの役割定義
            subagent_type: 使用するサブエージェントタイプ（例: "Explore", "Plan"）

        Returns:
            実行結果
        """
        if subagent_type:
            enhanced_prompt = f"""
Task toolを使用して以下のタスクを実行してください:
- subagent_type: {subagent_type}
- タスク: {prompt}
"""
        else:
            enhanced_prompt = prompt

        return self.execute(enhanced_prompt, system_prompt)


# ============================================
# A2A Base Server
# ============================================

class A2ABaseServer(ABC):
    """A2Aサーバーの基底クラス（MCP統合対応）"""

    def __init__(
        self,
        name: str,
        description: str,
        port: int = 8000,
        workspace: str = ".",
        enable_full_tools: bool = True,
        enable_mcp: bool = True,
        allowed_tools: Optional[List[str]] = None,
        timeout: int = 300
    ):
        self.name = name
        self.description = description
        self.port = port
        self.workspace = workspace
        self.enable_mcp = enable_mcp
        self.app = FastAPI(title=f"A2A Agent: {name}")
        self.claude = ClaudeCodeCLI(
            workspace=workspace,
            enable_full_tools=enable_full_tools,
            enable_mcp=enable_mcp,
            allowed_tools=allowed_tools,
            timeout=timeout
        )
        self.tasks: Dict[str, Task] = {}

        # MCP設定
        self.mcp_guide = generate_mcp_guide(name) if MCP_AVAILABLE else ""
        self.mcp_prompt_addition = get_mcp_system_prompt_addition(name) if MCP_AVAILABLE else ""

        self._setup_routes()

    def _setup_routes(self):
        """A2Aエンドポイントを設定"""

        @self.app.get("/.well-known/agent.json")
        async def get_agent_card():
            """Agent Card を返す"""
            return self.get_agent_card()

        @self.app.post("/a2a/tasks/send")
        async def send_task(request: TaskSendRequest):
            """タスクを受信して処理"""
            return await self.handle_task(request)

        @self.app.get("/a2a/tasks/{task_id}")
        async def get_task(task_id: str):
            """タスク状態を取得"""
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            return self.tasks[task_id]

        @self.app.post("/a2a/tasks/{task_id}/cancel")
        async def cancel_task(task_id: str):
            """タスクをキャンセル"""
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            self.tasks[task_id].status.state = "cancelled"
            return self.tasks[task_id]

    @abstractmethod
    def get_agent_card(self) -> dict:
        """Agent Card を返す（サブクラスで実装）"""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """システムプロンプトを返す（サブクラスで実装）"""
        pass

    def get_full_system_prompt(self) -> str:
        """MCPガイドを含む完全なシステムプロンプトを生成"""
        base_prompt = self.get_system_prompt()

        if self.enable_mcp and self.mcp_prompt_addition:
            return f"{base_prompt}\n{self.mcp_prompt_addition}\n{self.mcp_guide}"

        return base_prompt

    async def handle_task(self, request: TaskSendRequest) -> Task:
        """タスクを処理"""
        # タスクID生成
        task_id = request.id or str(uuid.uuid4())

        # タスク作成
        task = Task(
            id=task_id,
            contextId=request.contextId,
            status=TaskStatus(state="working"),
            history=[request.message]
        )
        self.tasks[task_id] = task

        # メッセージからテキスト抽出
        user_text = ""
        for part in request.message.parts:
            if part.text:
                user_text += part.text + "\n"

        # 開始時刻記録 & 通知
        start_time = time.time()
        notify_start(self.name, task_id, user_text[:100])

        # Claude Code CLI 実行（MCPガイド含む完全なシステムプロンプト使用）
        try:
            result = self.claude.execute(
                prompt=user_text.strip(),
                system_prompt=self.get_full_system_prompt()
            )

            # 所要時間計算
            duration = time.time() - start_time

            # 成功時
            task.status = TaskStatus(
                state="completed",
                message=Message(
                    role="agent",
                    parts=[Part(type="text", text=result)]
                )
            )
            task.artifacts = [
                Artifact(
                    name="response",
                    parts=[Part(type="text", text=result)]
                )
            ]

            # 完了通知
            notify_complete(self.name, task_id, result[:100], duration)

        except Exception as e:
            # エラー時
            task.status = TaskStatus(
                state="failed",
                message=Message(
                    role="agent",
                    parts=[Part(type="text", text=f"Error: {str(e)}")]
                )
            )

            # エラー通知
            notify_error(self.name, task_id, str(e))

        return task

    def run(self):
        """サーバー起動"""
        import uvicorn
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)
