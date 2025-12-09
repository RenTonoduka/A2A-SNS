# バズ動画トランスクリプト取得指示

以下の動画のトランスクリプトをMCPツールで取得してください：

## 1. 【完全版】2025年12月、AIスライド作成が革命的に変わる、プロの手順を全て見せます。
video_id: Y5gsr8ynves

```
mcp__klavis-strata__execute_action(
    server_name="youtube",
    category_name="YOUTUBE_TRANSCRIPT",
    action_name="get_youtube_video_transcript",
    body_schema='{"url": "https://youtube.com/watch?v=Y5gsr8ynves"}'
)
```

## 次のステップ

トランスクリプト取得後、Script Writer Agent (port 8113) に以下を送信：
- バズ動画タイトル・URL・PR情報
- 取得したトランスクリプト

Script Writer Agentが構成分析と台本テンプレート生成を行います。