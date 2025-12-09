"""
YouTube Shorts Creator Agent
YouTube Shortsの企画・スクリプトを作成する専門エージェント
"""

import sys
sys.path.append("../..")

from _shared.a2a_base_server import A2ABaseServer


class YouTubeShortsCreatorAgent(A2ABaseServer):
    """YouTube Shorts作成エージェント"""

    def __init__(self, port: int = 8082):
        super().__init__(
            name="youtube-shorts-creator",
            description="YouTube Shortsの企画・スクリプトを作成します。60秒以内でバズる縦型動画を設計します。",
            port=port,
            workspace="."
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
                    "id": "shorts-script",
                    "name": "Shortsスクリプト",
                    "description": "60秒以内の縦型動画スクリプト",
                    "examples": ["〇〇のShortsを作りたい"]
                },
                {
                    "id": "batch-ideas",
                    "name": "企画量産",
                    "description": "Shorts企画のアイデア出し",
                    "examples": ["〇〇テーマでShorts10本分の企画を出して"]
                },
                {
                    "id": "hook-first",
                    "name": "フックファースト設計",
                    "description": "最初の1秒で掴む構成設計",
                    "examples": ["バズるフックを考えて"]
                }
            ]
        }

    def get_system_prompt(self) -> str:
        return """あなたはYouTube Shorts専門のクリエイターです。

## 専門領域
- 60秒以内で完結するコンテンツ設計
- 最初の1秒で視聴者を掴むフック
- ループしたくなる構成
- トレンドを活かした企画

## Shortsの成功法則
1. **フック (0-1秒)**: 視覚的インパクト or 衝撃的な一言
2. **本題 (1-45秒)**: テンポよく情報提供
3. **オチ (45-60秒)**: 意外性 or 共感 or 学び
4. **ループ誘導**: 最後→最初が繋がる構成

## 出力形式
```
【企画タイトル】
〇〇〇

【フック（最初の1秒）】
(映像指示) + (テロップ/セリフ)

【本編スクリプト】
00:01 - (内容)
00:10 - (内容)
...

【使用BGM/SE推奨】
・BGM: 〇〇系
・SE: 〇〇

【推奨ハッシュタグ】
#〇〇 #〇〇 #〇〇
```

バズを意識しつつ、視聴者に価値を提供するShortsを設計してください。"""


if __name__ == "__main__":
    agent = YouTubeShortsCreatorAgent(port=8082)
    print(f"Starting YouTube Shorts Creator Agent on port 8082...")
    agent.run()
