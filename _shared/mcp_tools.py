"""
MCP Tools Integration for A2A Agents
各エージェントが使用できるMCPツールの統合モジュール
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class MCPService(Enum):
    """利用可能なMCPサービス"""
    # Google Workspace
    GMAIL = "gmail"
    GOOGLE_CALENDAR = "google calendar"
    GOOGLE_SHEETS = "google sheets"
    GOOGLE_DOCS = "google docs"
    GOOGLE_DRIVE = "google drive"

    # Collaboration
    SLACK = "slack"
    DISCORD = "discord"
    NOTION = "notion"
    LINEAR = "linear"

    # Development
    GITHUB = "github"
    VERCEL = "vercel"
    FIGMA = "figma"

    # Media
    YOUTUBE = "youtube"

    # Search
    EXA = "exa"


@dataclass
class MCPToolConfig:
    """MCPツール設定"""
    service: MCPService
    categories: List[str]
    description: str
    example_actions: List[str]


# ============================================
# エージェント別 MCP ツール定義
# ============================================

AGENT_MCP_TOOLS: Dict[str, List[MCPToolConfig]] = {
    # Research Agent - 情報収集・分析
    "research-agent": [
        MCPToolConfig(
            service=MCPService.YOUTUBE,
            categories=["YOUTUBE_TRANSCRIPT"],
            description="YouTube動画の分析（トランスクリプト取得）",
            example_actions=["get_youtube_video_transcript"]
        ),
        MCPToolConfig(
            service=MCPService.EXA,
            categories=["WEB_SEARCH", "CODE_CONTEXT"],
            description="Web検索とコード検索",
            example_actions=["web_search_exa", "get_code_context_exa"]
        ),
        MCPToolConfig(
            service=MCPService.GOOGLE_SHEETS,
            categories=["GOOGLE_SHEETS_SPREADSHEET", "GOOGLE_SHEETS_CELL"],
            description="スプレッドシートへのデータ保存",
            example_actions=["google_sheets_create_spreadsheet", "google_sheets_write_to_cell"]
        ),
    ],

    # Hook Agent - フック・タイトル作成
    "hook-agent": [
        MCPToolConfig(
            service=MCPService.YOUTUBE,
            categories=["YOUTUBE_TRANSCRIPT"],
            description="競合動画のフック分析",
            example_actions=["get_youtube_video_transcript"]
        ),
        MCPToolConfig(
            service=MCPService.EXA,
            categories=["WEB_SEARCH"],
            description="トレンドフック検索",
            example_actions=["web_search_exa"]
        ),
    ],

    # Concept Agent - 企画・構成
    "concept-agent": [
        MCPToolConfig(
            service=MCPService.GOOGLE_DOCS,
            categories=["GOOGLE_DOCS_DOCUMENT"],
            description="企画書の作成・保存",
            example_actions=["google_docs_create_document_from_text"]
        ),
        MCPToolConfig(
            service=MCPService.NOTION,
            categories=["NOTION_PAGES", "NOTION_DATABASES"],
            description="Notionへの企画保存",
            example_actions=["create_page", "query_database"]
        ),
    ],

    # Reviewer Agent - レビュー・品質チェック
    "reviewer-agent": [
        MCPToolConfig(
            service=MCPService.GITHUB,
            categories=["GITHUB_ISSUES", "GITHUB_PULLS"],
            description="GitHubイシュー・PR管理",
            example_actions=["create_issue", "create_pull_request"]
        ),
        MCPToolConfig(
            service=MCPService.LINEAR,
            categories=["LINEAR_ISSUE"],
            description="Linearタスク管理",
            example_actions=["create_issue", "update_issue"]
        ),
    ],

    # Improver Agent - 改善・最適化
    "improver-agent": [
        MCPToolConfig(
            service=MCPService.EXA,
            categories=["WEB_SEARCH", "CODE_CONTEXT"],
            description="改善アイデア検索",
            example_actions=["web_search_exa"]
        ),
    ],

    # Coordinator Agent - 統括・通知
    "coordinator-agent": [
        MCPToolConfig(
            service=MCPService.GMAIL,
            categories=["GMAIL_EMAIL"],
            description="メール送信・通知",
            example_actions=["gmail_send_email"]
        ),
        MCPToolConfig(
            service=MCPService.SLACK,
            categories=["SLACK_MESSAGE", "SLACK_CHANNEL"],
            description="Slack通知",
            example_actions=["send_message", "list_channels"]
        ),
        MCPToolConfig(
            service=MCPService.GOOGLE_CALENDAR,
            categories=["GOOGLE_CALENDAR_EVENT"],
            description="カレンダー予定作成",
            example_actions=["create_event"]
        ),
        MCPToolConfig(
            service=MCPService.DISCORD,
            categories=["DISCORD_CHANNELS_MESSAGES"],
            description="Discord通知",
            example_actions=["send_message"]
        ),
        MCPToolConfig(
            service=MCPService.GOOGLE_SHEETS,
            categories=["GOOGLE_SHEETS_SPREADSHEET", "GOOGLE_SHEETS_CELL"],
            description="ログ記録・レポート",
            example_actions=["google_sheets_write_to_cell"]
        ),
    ],
}


# ============================================
# MCP ツール使用ガイド生成
# ============================================

def generate_mcp_guide(agent_name: str) -> str:
    """
    エージェント用のMCPツール使用ガイドを生成

    Args:
        agent_name: エージェント名

    Returns:
        システムプロンプトに追加するMCPガイド文字列
    """
    tools = AGENT_MCP_TOOLS.get(agent_name, [])

    if not tools:
        return ""

    guide = """

## 利用可能なMCPツール

以下のMCPツールを使用してタスクを実行できます。
ツールを使う際は `mcp__klavis-strata__` プレフィックスを使用してください。

"""

    for tool in tools:
        guide += f"""
### {tool.service.value.upper()}
- 用途: {tool.description}
- カテゴリ: {', '.join(tool.categories)}
- 例: {', '.join(tool.example_actions)}
"""

    guide += """

### MCP ツール使用手順

1. **カテゴリ確認**: `discover_server_categories_or_actions` で利用可能なカテゴリを確認
2. **アクション確認**: `get_category_actions` でカテゴリ内のアクションを取得
3. **詳細確認**: `get_action_details` でパラメータ詳細を確認
4. **実行**: `execute_action` でアクションを実行

### 使用例

```
# YouTube動画のトランスクリプト取得
mcp__klavis-strata__execute_action(
    server_name="youtube",
    category_name="YOUTUBE_TRANSCRIPT",
    action_name="get_youtube_video_transcript",
    body_schema='{"url": "https://www.youtube.com/watch?v=..."}'
)

# スプレッドシートにデータ書き込み
mcp__klavis-strata__execute_action(
    server_name="google sheets",
    category_name="GOOGLE_SHEETS_CELL",
    action_name="google_sheets_write_to_cell",
    body_schema='{"spreadsheet_id": "...", "column": "A", "row": 1, "value": "データ"}'
)

# メール送信
mcp__klavis-strata__execute_action(
    server_name="gmail",
    category_name="GMAIL_EMAIL",
    action_name="gmail_send_email",
    body_schema='{"to": ["user@example.com"], "subject": "件名", "body": "本文"}'
)
```

"""
    return guide


def get_mcp_system_prompt_addition(agent_name: str) -> str:
    """
    エージェントのシステムプロンプトに追加するMCP関連の文字列を取得

    Args:
        agent_name: エージェント名

    Returns:
        システムプロンプト追加文字列
    """
    tools = AGENT_MCP_TOOLS.get(agent_name, [])

    if not tools:
        return ""

    services = [tool.service.value for tool in tools]

    return f"""

【MCPツール連携】
このエージェントは以下の外部サービスと連携できます: {', '.join(services)}

MCPツールを活用して:
- 外部サービスからデータを取得
- 結果を外部サービスに保存・通知
- 他のサービスとの連携を実現

詳細は get_mcp_guide() を参照してください。
"""


# ============================================
# 共通ユーティリティ
# ============================================

# ログ用スプレッドシートID（作成済み）
LOG_SPREADSHEET_ID = "1RmmWvFtOCsTNX259Y2JrqnvA-JwzlUi0OBiCq4H8O6Q"

# 通知先メール
NOTIFY_EMAIL = "tonoduka@h-bb.jp"


def get_log_spreadsheet_id() -> str:
    """ログ用スプレッドシートIDを取得"""
    return LOG_SPREADSHEET_ID


def get_notify_email() -> str:
    """通知先メールアドレスを取得"""
    return NOTIFY_EMAIL


# ============================================
# テスト
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("MCP Tools Integration Test")
    print("=" * 60)

    for agent_name in AGENT_MCP_TOOLS.keys():
        print(f"\n### {agent_name} ###")
        guide = generate_mcp_guide(agent_name)
        print(guide[:500] + "..." if len(guide) > 500 else guide)

    print("\n" + "=" * 60)
    print("✅ Test Complete")
    print("=" * 60)
