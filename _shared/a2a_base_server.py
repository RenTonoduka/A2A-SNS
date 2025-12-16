"""
A2A Base Server - Claude Code CLI wrapper
共通のA2Aサーバー基盤
MCP Tools統合対応
セキュリティ強化版 v2.0
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
import subprocess
import json
import uuid
import time
import os
import re
import hashlib
import secrets
from datetime import datetime
from abc import ABC, abstractmethod
from collections import defaultdict
import asyncio

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
# Security Configuration
# ============================================

# API Key認証
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key() -> Optional[str]:
    """環境変数からAPIキーを取得"""
    return os.environ.get("A2A_API_KEY")

def generate_api_key() -> str:
    """セキュアなAPIキーを生成"""
    return secrets.token_urlsafe(32)

async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Depends(API_KEY_HEADER)
) -> bool:
    """
    APIキー認証を検証
    - 環境変数 A2A_API_KEY が設定されている場合は認証必須
    - 設定されていない場合は警告を出して通過（開発モード）
    """
    expected_key = get_api_key()

    # 開発モード（APIキー未設定）
    if not expected_key:
        # ローカルホストからのアクセスのみ許可
        client_host = request.client.host if request.client else "unknown"
        if client_host not in ("127.0.0.1", "localhost", "::1"):
            raise HTTPException(
                status_code=403,
                detail="API key required for non-local access. Set A2A_API_KEY environment variable."
            )
        return True

    # 本番モード（APIキー必須）
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header."
        )

    # タイミング攻撃対策の比較
    if not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    return True


# ============================================
# Rate Limiting
# ============================================

class RateLimiter:
    """シンプルなインメモリレートリミッター"""

    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 500):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_counts: Dict[str, List[float]] = defaultdict(list)
        self.hour_counts: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_id: str) -> bool:
        """リクエストが許可されるかチェック"""
        async with self._lock:
            now = time.time()
            minute_ago = now - 60
            hour_ago = now - 3600

            # 古いエントリを削除
            self.minute_counts[client_id] = [
                t for t in self.minute_counts[client_id] if t > minute_ago
            ]
            self.hour_counts[client_id] = [
                t for t in self.hour_counts[client_id] if t > hour_ago
            ]

            # 制限チェック
            if len(self.minute_counts[client_id]) >= self.requests_per_minute:
                return False
            if len(self.hour_counts[client_id]) >= self.requests_per_hour:
                return False

            # カウント追加
            self.minute_counts[client_id].append(now)
            self.hour_counts[client_id].append(now)
            return True

# グローバルレートリミッター
rate_limiter = RateLimiter()

async def check_rate_limit(request: Request):
    """レート制限をチェック"""
    client_id = request.client.host if request.client else "unknown"

    if not await rate_limiter.is_allowed(client_id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    return True


# ============================================
# Input Validation
# ============================================

# 危険なパターンのブラックリスト
DANGEROUS_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"(?i)system\s*prompt",
    r"(?i)rm\s+-rf\s+/",
    r"(?i)sudo\s+rm",
    r"(?i)mkfs\.",
    r"(?i)dd\s+if=.+of=/dev/",
    r"(?i)>\s*/dev/sd[a-z]",
    r"(?i)chmod\s+777\s+/",
    r"(?i)curl.+\|\s*sh",
    r"(?i)wget.+\|\s*sh",
]

# コンパイル済みパターン
COMPILED_DANGEROUS_PATTERNS = [re.compile(p) for p in DANGEROUS_PATTERNS]

def sanitize_input(text: str, max_length: int = 50000) -> str:
    """
    入力テキストをサニタイズ

    Args:
        text: 入力テキスト
        max_length: 最大文字数

    Returns:
        サニタイズ済みテキスト

    Raises:
        ValueError: 危険なパターンが検出された場合
    """
    if not text:
        return ""

    # 長さ制限
    if len(text) > max_length:
        text = text[:max_length]

    # 危険なパターンチェック
    for pattern in COMPILED_DANGEROUS_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"Potentially dangerous input detected")

    return text

def validate_workspace_path(workspace: str, allowed_base: Optional[str] = None) -> str:
    """
    ワークスペースパスを検証

    Args:
        workspace: 検証するパス
        allowed_base: 許可されるベースディレクトリ

    Returns:
        検証済みパス

    Raises:
        ValueError: パスが不正な場合
    """
    # パストラバーサル攻撃対策
    normalized = os.path.normpath(os.path.abspath(workspace))

    if ".." in workspace:
        raise ValueError("Path traversal detected")

    if allowed_base:
        allowed_base = os.path.normpath(os.path.abspath(allowed_base))
        if not normalized.startswith(allowed_base):
            raise ValueError(f"Workspace must be within {allowed_base}")

    return normalized


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
    """A2Aサーバーの基底クラス（MCP統合対応・セキュリティ強化版）"""

    def __init__(
        self,
        name: str,
        description: str,
        port: int = 8000,
        workspace: str = ".",
        enable_full_tools: bool = True,
        enable_mcp: bool = True,
        allowed_tools: Optional[List[str]] = None,
        timeout: int = 300,
        enable_auth: bool = True,
        enable_rate_limit: bool = True,
        allowed_origins: Optional[List[str]] = None
    ):
        self.name = name
        self.description = description
        self.port = port
        self.workspace = validate_workspace_path(workspace)  # パス検証
        self.enable_mcp = enable_mcp
        self.enable_auth = enable_auth
        self.enable_rate_limit = enable_rate_limit

        self.app = FastAPI(title=f"A2A Agent: {name}")

        # CORS設定（セキュリティ強化）
        cors_origins = allowed_origins or [
            "http://localhost:*",
            "http://127.0.0.1:*",
        ]
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["X-API-Key", "Content-Type"],
        )

        self.claude = ClaudeCodeCLI(
            workspace=self.workspace,
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

    def _get_dependencies(self) -> List:
        """認証・レート制限の依存関係を取得"""
        deps = []
        if self.enable_auth:
            deps.append(Depends(verify_api_key))
        if self.enable_rate_limit:
            deps.append(Depends(check_rate_limit))
        return deps

    def _setup_routes(self):
        """A2Aエンドポイントを設定（セキュリティ強化版）"""

        # Agent Card は認証不要（公開情報）
        @self.app.get("/.well-known/agent.json")
        async def get_agent_card():
            """Agent Card を返す"""
            return self.get_agent_card()

        # タスク送信は認証・レート制限必須
        @self.app.post("/a2a/tasks/send", dependencies=self._get_dependencies())
        async def send_task(request: TaskSendRequest, http_request: Request):
            """タスクを受信して処理（認証・レート制限付き）"""
            return await self.handle_task(request)

        @self.app.get("/a2a/tasks/{task_id}", dependencies=self._get_dependencies())
        async def get_task(task_id: str):
            """タスク状態を取得"""
            # task_idのサニタイズ
            if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', task_id):
                raise HTTPException(status_code=400, detail="Invalid task ID format")
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            return self.tasks[task_id]

        @self.app.post("/a2a/tasks/{task_id}/cancel", dependencies=self._get_dependencies())
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

    async def pre_execute_tools(self, user_text: str) -> Dict[str, Any]:
        """
        LLM実行前に強制的にツールを実行するフック
        サブクラスでオーバーライドして、必要なデータを事前取得

        Args:
            user_text: ユーザーからのリクエストテキスト

        Returns:
            取得したデータ（LLMのコンテキストとして渡される）
        """
        return {}  # デフォルトは何もしない

    def build_enhanced_prompt(self, user_text: str, tool_results: Dict[str, Any]) -> str:
        """
        ツール実行結果を含む拡張プロンプトを構築

        Args:
            user_text: 元のリクエスト
            tool_results: pre_execute_toolsの結果

        Returns:
            拡張されたプロンプト
        """
        if not tool_results:
            return user_text.strip()

        # ツール結果をコンテキストとして追加
        context_parts = []
        for key, value in tool_results.items():
            if value:
                context_parts.append(f"## {key}\n{value}")

        if context_parts:
            context = "\n\n".join(context_parts)
            return f"""## 事前取得データ（必ず活用すること）

{context}

---

## リクエスト

{user_text.strip()}"""

        return user_text.strip()

    async def handle_task(self, request: TaskSendRequest) -> Task:
        """タスクを処理（入力検証付き）"""
        # タスクID検証・生成
        if request.id:
            if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', request.id):
                raise HTTPException(status_code=400, detail="Invalid task ID format")
            task_id = request.id
        else:
            task_id = str(uuid.uuid4())

        # メッセージからテキスト抽出 & 入力検証
        user_text = ""
        for part in request.message.parts:
            if part.text:
                user_text += part.text + "\n"

        # 🔒 入力サニタイズ（危険なパターンを検出）
        try:
            user_text = sanitize_input(user_text)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Input validation failed: {str(e)}"
            )

        # タスク作成
        task = Task(
            id=task_id,
            contextId=request.contextId,
            status=TaskStatus(state="working"),
            history=[request.message]
        )
        self.tasks[task_id] = task

        # 開始時刻記録 & 通知
        start_time = time.time()
        notify_start(self.name, task_id, user_text[:100])

        # 🆕 LLM実行前にツールを強制実行
        try:
            tool_results = await self.pre_execute_tools(user_text)
        except Exception as e:
            tool_results = {"tool_error": f"ツール事前実行エラー: {str(e)}"}

        # 拡張プロンプト構築
        enhanced_prompt = self.build_enhanced_prompt(user_text, tool_results)

        # Claude Code CLI 実行（MCPガイド含む完全なシステムプロンプト使用）
        try:
            result = self.claude.execute(
                prompt=enhanced_prompt,
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

    def run(self, host: Optional[str] = None):
        """
        サーバー起動

        Args:
            host: バインドするホスト（デフォルト: 環境変数 A2A_HOST または 127.0.0.1）
                  本番環境で外部公開する場合は 0.0.0.0 を指定
        """
        import uvicorn

        # ホスト決定（セキュリティ優先: デフォルトはlocalhostのみ）
        if host is None:
            host = os.environ.get("A2A_HOST", "127.0.0.1")

        # 0.0.0.0バインド時は警告
        if host == "0.0.0.0":
            api_key = get_api_key()
            if not api_key:
                print("⚠️  WARNING: Binding to 0.0.0.0 without A2A_API_KEY is dangerous!")
                print("⚠️  Set A2A_API_KEY environment variable for production.")

        print(f"🚀 Starting {self.name} on {host}:{self.port}")
        print(f"🔒 Auth: {'Enabled' if self.enable_auth else 'Disabled'}")
        print(f"🔒 Rate Limit: {'Enabled' if self.enable_rate_limit else 'Disabled'}")

        uvicorn.run(self.app, host=host, port=self.port)
