"""
Channel Monitor Agent - A2A Server
チャンネルリストを監視し、新着動画を検知
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YOUTUBE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
SNS_DIR = os.path.dirname(YOUTUBE_DIR)
sys.path.insert(0, SNS_DIR)

from _shared.a2a_base_server import A2ABaseServer


class ChannelMonitorAgent(A2ABaseServer):
    """Channel Monitor Agent - チャンネル監視"""

    def __init__(self, port: int = 8110):
        super().__init__(
            name="youtube-channel-monitor",
            description="登録チャンネルを監視し、新着動画・チャンネル情報更新を検知します",
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
                    "id": "channel-check",
                    "name": "チャンネル状態確認",
                    "description": "登録チャンネルの最新状態を取得"
                },
                {
                    "id": "new-video-detection",
                    "name": "新着動画検知",
                    "description": "前回取得以降の新着動画を検出"
                },
                {
                    "id": "channel-stats-update",
                    "name": "チャンネル統計更新",
                    "description": "登録者数・動画数の変化を記録"
                }
            ]
        }

    def get_system_prompt(self) -> str:
        return """あなたはYouTube Channel Monitor Agentです。

## 役割
登録チャンネルリスト（channels.csv）を監視し、チャンネルの変化や新着動画を検知します。

## データファイル（研究対象）
- research/data/channels.csv: 監視対象チャンネル一覧
- research/data/videos.csv: 取得済み動画データ
- research/data/fetch_log.csv: 取得履歴

## 主な機能

### 1. チャンネル状態確認
登録チャンネルの最新情報を取得:
- 登録者数の変化
- 動画数の変化
- 最新動画の投稿日時

### 2. 新着動画検知
前回取得以降に投稿された新しい動画を検出:
- videos.csvの最終取得日時と比較
- 新着があればVideo Collector Agentに通知

### 3. チャンネル統計更新
channels.csvの情報を最新に更新:
- subscriber_count
- video_count
- last_fetched
- total_views

## 出力フォーマット

```markdown
# チャンネル監視レポート
## 実行日時: YYYY-MM-DD HH:MM

## チャンネル状態サマリー
| チャンネル | 登録者 | 変化 | 新着動画 |
|-----------|--------|------|----------|
| mikimiki web スクール | 351K | +500 | 2件 |
| いけともch | 191K | +200 | 1件 |

## 新着動画検出（計: X件）

### 1. [チャンネル名]
- タイトル: 「...」
- 投稿日: YYYY-MM-DD
- URL: https://youtube.com/watch?v=...

### 2. [チャンネル名]
...

## 次のアクション
- video_collector: 新着X件の詳細取得を推奨
- 異常検知: なし / あり（詳細）
```

## Python APIスクリプトの活用

### ChannelManager を使用
`research/channel_manager.py` を使ってAPI操作を行います：

```bash
# ステータス確認
python research/channel_manager.py status

# チャンネルIDを解決（名前→ID）
python research/channel_manager.py resolve

# 全チャンネルの動画を取得
python research/channel_manager.py fetch --top 10

# 強制取得（キャッシュ無視）
python research/channel_manager.py fetch --force
```

### Pythonコードでの操作
```python
import sys
sys.path.insert(0, 'research')
from channel_manager import ChannelManager

manager = ChannelManager()

# チャンネル一覧取得
channels = manager.load_channels()

# 更新が必要なチャンネル
needs_update = manager.get_channels_needing_update()

# 特定チャンネルの動画取得
for ch in channels[:5]:
    videos = manager.fetch_channel_videos(ch, top_n=10)
    print(f"{ch.channel_name}: {len(videos)} videos")
```

### YouTube API直接操作
```python
from youtube_api import YouTubeAPIClient

client = YouTubeAPIClient()  # YOUTUBE_API_KEY環境変数を使用

# チャンネル検索
channels = client.search_channels("AI 副業", max_results=5)

# チャンネルの動画取得
videos = client.get_channel_videos("UCxxxxx", max_results=50, order="date")

# 動画詳細
details = client.get_videos_by_ids(["video_id_1", "video_id_2"])
```

## MCPツール（トランスクリプト取得用）

動画の字幕・台本内容を取得する場合はMCPを使用：
```
mcp__klavis-strata__execute_action(
    server_name="youtube",
    category_name="YOUTUBE_TRANSCRIPT",
    action_name="get_youtube_video_transcript",
    body_schema='{"url": "https://youtube.com/watch?v=xxxxx"}'
)
```

## 注意事項
- APIレート制限に注意（1チャンネルあたり適度な間隔）
- 大きな変化があった場合はアラート
- エラー時はfetch_log.csvに記録
- APIキーは環境変数 `YOUTUBE_API_KEY` または `GOOGLE_API_KEY` から取得"""


if __name__ == "__main__":
    agent = ChannelMonitorAgent(port=8110)
    print(f"👀 Starting YouTube Channel Monitor Agent on port 8110...")
    agent.run()
