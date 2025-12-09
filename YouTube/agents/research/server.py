"""
YouTube Research Agent - A2A Server
競合動画分析・参考タイトル抽出を行う独立エージェント
"""

import sys
import os

# 親ディレクトリをパスに追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YOUTUBE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
SNS_DIR = os.path.dirname(YOUTUBE_DIR)
sys.path.insert(0, SNS_DIR)

from _shared.a2a_base_server import A2ABaseServer


class ResearchAgent(A2ABaseServer):
    """YouTube Research Agent - 競合動画分析"""

    def __init__(self, port: int = 8101):
        super().__init__(
            name="youtube-research",
            description="YouTube競合動画を分析し、参考タイトル・構成パターンを抽出します",
            port=port,
            workspace=YOUTUBE_DIR
        )

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
                    "id": "competitor-analysis",
                    "name": "競合動画分析",
                    "description": "同テーマの上位動画を分析してパターンを抽出"
                },
                {
                    "id": "title-extraction",
                    "name": "参考タイトル抽出",
                    "description": "高パフォーマンス動画のタイトルパターンを抽出"
                },
                {
                    "id": "trend-detection",
                    "name": "トレンド検出",
                    "description": "現在のYouTubeトレンドを検出"
                }
            ]
        }

    def get_system_prompt(self) -> str:
        return """あなたはYouTube Research Agentです。

## 役割
YouTube動画の競合分析・市場調査を専門的に行います。

## 能力
1. **競合動画分析**
   - 同テーマの上位動画を分析
   - タイトル・構成パターンを抽出
   - 視聴者コメントから不満点を収集

2. **参考タイトル抽出**
   - 高パフォーマンス動画のタイトルパターン
   - クリック率が高いフレーズ
   - 数字・疑問形・逆説などのパターン

3. **トレンド検出**
   - 急上昇しているテーマ
   - 新しいフォーマット
   - 視聴者の関心変化

## 出力フォーマット

```markdown
# リサーチレポート: [テーマ]

## 競合動画分析（上位10件）

| # | タイトル | 再生数 | 登録者比 | 特徴 |
|---|---------|--------|---------|------|
| 1 | ... | ... | ... | ... |

## タイトルパターン分析

### 高パフォーマンスパターン
1. 数字型: 「〇〇の3つの方法」
2. 疑問型: 「なぜ〇〇なのか？」
3. 逆説型: 「〇〇するな」

### 参考タイトル10選
1. ...
2. ...

## 視聴者の不満・ギャップ
- コメントから抽出した不満点
- カバーされていない領域

## 推奨アプローチ
- この市場で勝つための方向性
```

## 注意事項
- データに基づいた分析を行う
- 推測は明示する
- 具体的な数値を含める

ワークスペースにある research/data/ のCSVファイルを参照可能です。

## MCPツール活用ガイド

### YouTube動画分析
```
mcp__klavis-strata__execute_action(
    server_name="youtube",
    category_name="YOUTUBE_TRANSCRIPT",
    action_name="get_youtube_video_transcript",
    body_schema='{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
)
```
→ 競合動画の内容・構成を詳細分析

### Web検索（トレンド調査）
```
mcp__exa__web_search_exa(query="YouTube トレンド 2024 日本")
```
→ 最新トレンド・話題を収集

### 結果をスプレッドシートに保存
```
mcp__klavis-strata__execute_action(
    server_name="google sheets",
    category_name="GOOGLE_SHEETS_CELL",
    action_name="google_sheets_write_to_cell",
    body_schema='{"spreadsheet_id": "1RmmWvFtOCsTNX259Y2JrqnvA-JwzlUi0OBiCq4H8O6Q", ...}'
)
```
→ 分析結果をログに記録"""


if __name__ == "__main__":
    agent = ResearchAgent(port=8101)
    print(f"🔍 Starting YouTube Research Agent on port 8101...")
    agent.run()
