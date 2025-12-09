"""
Claude Code Runner
フル機能モード: ファイル操作、Bash実行、Task tool（サブエージェント）が使える
"""

import subprocess
import os
from typing import Optional, List


class ClaudeRunner:
    """
    Claude Code CLIのラッパー（フル機能モード）

    機能:
    - ファイル操作（Read, Write, Edit）
    - Bash実行
    - Task tool（サブエージェント起動）
    - Web検索（WebFetch, WebSearch）
    - 検索（Glob, Grep）
    """

    # 許可するツール（デフォルト）
    DEFAULT_ALLOWED_TOOLS = [
        "Read", "Write", "Edit",      # ファイル操作
        "Bash",                        # コマンド実行
        "Glob", "Grep",               # 検索
        "Task",                        # サブエージェント起動
        "WebFetch", "WebSearch",      # Web検索
        "TodoWrite",                   # タスク管理
    ]

    def __init__(
        self,
        workspace: str = ".",
        timeout: int = 300,
        allowed_tools: Optional[List[str]] = None,
        enable_full_tools: bool = True
    ):
        self.workspace = workspace
        self.timeout = timeout
        self.allowed_tools = allowed_tools or self.DEFAULT_ALLOWED_TOOLS
        self.enable_full_tools = enable_full_tools

    def run(
        self,
        prompt: str,
        output_format: str = "text",
        use_full_tools: Optional[bool] = None
    ) -> dict:
        """
        Claude Codeを実行

        Args:
            prompt: 送信するプロンプト
            output_format: "text" | "json" | "stream-json"
            use_full_tools: Trueでフル機能モード（デフォルトはenable_full_tools設定に従う）

        Returns:
            {"success": bool, "output": str, "error": str}
        """
        use_tools = use_full_tools if use_full_tools is not None else self.enable_full_tools

        try:
            if use_tools:
                # フル機能モード: -p でプロンプト指定、ツール実行可能
                cmd = [
                    "claude",
                    "-p", prompt,
                    "--output-format", output_format,
                    "--allowedTools", ",".join(self.allowed_tools),
                ]
                input_data = None
            else:
                # テキスト生成のみモード（従来互換）
                cmd = ["claude", "--output-format", output_format]
                input_data = prompt

            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                cwd=self.workspace,
                timeout=self.timeout
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip(),
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip()
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": None,
                "error": f"Timeout after {self.timeout}s"
            }
        except Exception as e:
            return {
                "success": False,
                "output": None,
                "error": str(e)
            }

    def ask(self, question: str) -> str:
        """シンプルな質問（フル機能モード）"""
        result = self.run(question)
        return result["output"] if result["success"] else f"Error: {result['error']}"

    def execute_task(self, task: str) -> str:
        """タスク実行を依頼（フル機能モード）"""
        result = self.run(task)
        return result["output"] if result["success"] else f"Error: {result['error']}"

    def execute_with_subagent(self, task: str, subagent_type: str) -> str:
        """
        Task tool（サブエージェント）を使用してタスクを実行

        Args:
            task: 実行するタスク
            subagent_type: サブエージェントタイプ（例: "Explore", "Plan", "code-reviewer"）

        Returns:
            実行結果
        """
        prompt = f"""
Task toolを使用して以下のタスクを実行してください:
- subagent_type: {subagent_type}
- タスク: {task}
"""
        return self.execute_task(prompt)

    def request_slash_command(self, command: str, context: str = "") -> str:
        """
        スラッシュコマンドの実行を依頼

        フル機能モードなので実際にコマンドが実行される
        """
        if context:
            prompt = f"{context}\n\n{command} を実行してください"
        else:
            prompt = f"{command} を実行してください"

        return self.execute_task(prompt)

    def read_file(self, file_path: str) -> str:
        """ファイルを読み込む（Read tool使用）"""
        return self.execute_task(f"Read toolを使って {file_path} を読み込んで内容を教えて")

    def write_file(self, file_path: str, content: str) -> str:
        """ファイルを書き込む（Write tool使用）"""
        return self.execute_task(f"Write toolを使って {file_path} に以下の内容を書き込んで:\n\n{content}")

    def run_bash(self, command: str) -> str:
        """Bashコマンドを実行（Bash tool使用）"""
        return self.execute_task(f"Bash toolを使って以下のコマンドを実行して: {command}")

    def search_codebase(self, query: str) -> str:
        """コードベースを検索（Explore agent使用）"""
        return self.execute_with_subagent(query, "Explore")


# テスト
if __name__ == "__main__":
    print("=" * 60)
    print("Claude Runner テスト（フル機能モード）")
    print("=" * 60)

    workspace = "/Users/tonodukaren/Programming/AI/02_Workspace/03_Markx/40_dev/A2A/SNS"
    runner = ClaudeRunner(workspace=workspace, timeout=120)

    print(f"\n設定:")
    print(f"  - workspace: {workspace}")
    print(f"  - enable_full_tools: {runner.enable_full_tools}")
    print(f"  - allowed_tools: {runner.allowed_tools}")

    print("\n[1] ファイル読み込みテスト（Read tool）")
    result = runner.execute_task("Read toolを使ってREADME.mdの最初の10行を読んで")
    print(f"応答: {result[:500]}...\n")

    print("[2] ディレクトリ確認テスト（Bash tool）")
    result = runner.run_bash("ls -la")
    print(f"応答: {result[:500]}...\n")

    print("[3] サブエージェント実行テスト（Task tool）")
    result = runner.execute_with_subagent(
        "このディレクトリの構造を簡潔に説明して",
        "Explore"
    )
    print(f"応答: {result[:500]}...\n")

    print("=" * 60)
    print("✅ フル機能モード テスト完了")
    print("=" * 60)
