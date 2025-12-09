"""
Buzz to Script Pipeline
バズ動画発見 → トランスクリプト取得 → 台本生成エージェント連携

MCPを使用してYouTubeトランスクリプトを取得し、
Script Writer Agentに渡す
"""

import os
import sys
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from a2a_client import A2AClient


# エージェントポート設定
AGENT_PORTS = {
    "trend_analyzer": 8112,
    "script_writer": 8113,
    "coordinator": 8100
}


def get_transcript_mcp_call(video_id: str) -> Dict[str, Any]:
    """
    MCPツールでトランスクリプト取得するための呼び出し情報を生成

    Claude Codeが実行する形式で返す
    """
    return {
        "tool": "mcp__klavis-strata__execute_action",
        "params": {
            "server_name": "youtube",
            "category_name": "YOUTUBE_TRANSCRIPT",
            "action_name": "get_youtube_video_transcript",
            "body_schema": json.dumps({
                "url": f"https://youtube.com/watch?v={video_id}"
            })
        }
    }


def format_buzz_videos_for_script_writer(
    buzz_videos: List[Dict[str, Any]],
    transcripts: Optional[Dict[str, str]] = None
) -> str:
    """
    バズ動画情報をScript Writer Agent用のプロンプトに整形

    Args:
        buzz_videos: バズ動画リスト
        transcripts: {video_id: transcript_text} のマッピング（オプション）

    Returns:
        Script Writer Agent向けのプロンプト文字列
    """
    prompt_parts = [
        "# バズ動画分析リクエスト",
        "",
        "以下のバズ動画を分析し、成功パターンを抽出して台本テンプレートを作成してください。",
        "",
        "## バズ動画一覧",
        ""
    ]

    for i, video in enumerate(buzz_videos[:5], 1):  # 上位5件
        video_id = video.get("video_id", "")
        title = video.get("title", "不明")
        channel = video.get("channel_name", "不明")
        views = video.get("view_count", 0)
        pr = video.get("performance_ratio", 0)

        prompt_parts.append(f"### {i}. {title}")
        prompt_parts.append(f"- チャンネル: {channel}")
        prompt_parts.append(f"- 再生数: {views:,}")
        prompt_parts.append(f"- PR (Performance Ratio): {pr:.1f}x")
        prompt_parts.append(f"- URL: https://youtube.com/watch?v={video_id}")

        # トランスクリプトがあれば追加
        if transcripts and video_id in transcripts:
            transcript = transcripts[video_id]
            # 長すぎる場合は切り詰め
            if len(transcript) > 5000:
                transcript = transcript[:5000] + "\n...(以下省略)"
            prompt_parts.append(f"\n#### トランスクリプト")
            prompt_parts.append(f"```")
            prompt_parts.append(transcript)
            prompt_parts.append(f"```")

        prompt_parts.append("")

    prompt_parts.extend([
        "## 分析タスク",
        "",
        "1. **構成分析**: 各動画の構成パターンを抽出",
        "2. **成功要因**: なぜバズったのか、共通点を特定",
        "3. **台本テンプレート**: 成功パターンを活用した台本テンプレートを作成",
        "",
        "## 出力形式",
        "",
        "- 構成分析表（Markdown）",
        "- 成功要因リスト",
        "- 再現可能な台本テンプレート（AREA形式）",
        ""
    ])

    return "\n".join(prompt_parts)


async def send_buzz_to_script_writer(
    buzz_videos: List[Dict[str, Any]],
    transcripts: Optional[Dict[str, str]] = None,
    script_writer_url: str = None
) -> Dict[str, Any]:
    """
    バズ動画情報をScript Writer Agentに送信

    Args:
        buzz_videos: バズ動画リスト
        transcripts: トランスクリプト（オプション）
        script_writer_url: Script Writer AgentのURL

    Returns:
        タスク結果
    """
    if script_writer_url is None:
        script_writer_url = f"http://localhost:{AGENT_PORTS['script_writer']}"

    client = A2AClient(script_writer_url)

    # プロンプト生成
    prompt = format_buzz_videos_for_script_writer(buzz_videos, transcripts)

    try:
        # タスク送信
        result = await client.send_task(prompt)
        return {
            "success": True,
            "task_id": result.get("id"),
            "status": result.get("status", {}).get("state"),
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def generate_transcript_fetch_instructions(buzz_videos: List[Dict[str, Any]]) -> str:
    """
    Claude Codeがトランスクリプトを取得するための指示を生成

    Args:
        buzz_videos: バズ動画リスト

    Returns:
        Claude Code向けの指示文字列（MCPツール呼び出し形式）
    """
    instructions = [
        "# バズ動画トランスクリプト取得指示",
        "",
        "以下の動画のトランスクリプトをMCPツールで取得してください：",
        ""
    ]

    for i, video in enumerate(buzz_videos[:5], 1):
        video_id = video.get("video_id", "")
        title = video.get("title", "不明")

        instructions.append(f"## {i}. {title}")
        instructions.append(f"video_id: {video_id}")
        instructions.append("")
        instructions.append("```")
        instructions.append("mcp__klavis-strata__execute_action(")
        instructions.append('    server_name="youtube",')
        instructions.append('    category_name="YOUTUBE_TRANSCRIPT",')
        instructions.append('    action_name="get_youtube_video_transcript",')
        instructions.append(f'    body_schema=\'{{"url": "https://youtube.com/watch?v={video_id}"}}\''
        )
        instructions.append(")")
        instructions.append("```")
        instructions.append("")

    instructions.extend([
        "## 次のステップ",
        "",
        "トランスクリプト取得後、Script Writer Agent (port 8113) に以下を送信：",
        "- バズ動画タイトル・URL・PR情報",
        "- 取得したトランスクリプト",
        "",
        "Script Writer Agentが構成分析と台本テンプレート生成を行います。"
    ])

    return "\n".join(instructions)


class BuzzToScriptPipeline:
    """
    バズ動画 → 台本生成の自動パイプライン
    """

    def __init__(
        self,
        script_writer_port: int = 8113,
        auto_fetch_transcripts: bool = True
    ):
        self.script_writer_url = f"http://localhost:{script_writer_port}"
        self.auto_fetch_transcripts = auto_fetch_transcripts

    def process_buzz_videos(
        self,
        buzz_videos: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        バズ動画を処理して台本生成パイプラインを開始

        Returns:
            {
                "transcript_instructions": トランスクリプト取得指示,
                "script_writer_prompt": Script Writer向けプロンプト,
                "video_count": 処理動画数
            }
        """
        if not buzz_videos:
            return {"error": "No buzz videos provided"}

        # トランスクリプト取得指示を生成
        transcript_instructions = generate_transcript_fetch_instructions(buzz_videos)

        # Script Writer向けプロンプト生成（トランスクリプトなし版）
        script_writer_prompt = format_buzz_videos_for_script_writer(buzz_videos)

        return {
            "transcript_instructions": transcript_instructions,
            "script_writer_prompt": script_writer_prompt,
            "video_count": len(buzz_videos[:5]),
            "videos": [
                {
                    "video_id": v.get("video_id"),
                    "title": v.get("title"),
                    "pr": v.get("performance_ratio")
                }
                for v in buzz_videos[:5]
            ]
        }

    async def send_to_script_writer(
        self,
        buzz_videos: List[Dict[str, Any]],
        transcripts: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Script Writer Agentにタスクを送信
        """
        return await send_buzz_to_script_writer(
            buzz_videos,
            transcripts,
            self.script_writer_url
        )


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Buzz to Script Pipeline")
    parser.add_argument("command", choices=["test", "instructions"])
    parser.add_argument("--video-id", "-v", help="Test video ID")
    args = parser.parse_args()

    if args.command == "test":
        # テスト用のダミーデータ
        test_videos = [
            {
                "video_id": "dQw4w9WgXcQ",
                "title": "テスト動画タイトル",
                "channel_name": "テストチャンネル",
                "view_count": 100000,
                "performance_ratio": 5.5
            }
        ]

        pipeline = BuzzToScriptPipeline()
        result = pipeline.process_buzz_videos(test_videos)

        print("=== Transcript Instructions ===")
        print(result["transcript_instructions"])
        print("\n=== Script Writer Prompt ===")
        print(result["script_writer_prompt"])

    elif args.command == "instructions":
        print("MCP Tool Call Format:")
        print(json.dumps(get_transcript_mcp_call(args.video_id or "VIDEO_ID"), indent=2))
