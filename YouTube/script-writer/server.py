"""
YouTube Script Writer Agent
YouTube動画の台本・構成を作成する専門エージェント
"""

import sys
sys.path.append("../..")

from _shared.a2a_base_server import A2ABaseServer


class YouTubeScriptWriterAgent(A2ABaseServer):
    """YouTube台本作成エージェント"""

    def __init__(self, port: int = 8081):
        super().__init__(
            name="youtube-script-writer",
            description="YouTube動画の台本・構成を作成します。視聴維持率を高める構成と、視聴者を引き込むスクリプトを提供します。",
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
                    "id": "full-script",
                    "name": "フル台本作成",
                    "description": "10分以上の動画用フル台本",
                    "examples": ["〇〇の解説動画の台本を書いて"]
                },
                {
                    "id": "structure-design",
                    "name": "構成設計",
                    "description": "動画の構成・アウトライン設計",
                    "examples": ["この企画の構成案を作って"]
                },
                {
                    "id": "hook-writing",
                    "name": "フック作成",
                    "description": "冒頭15秒のフック部分作成",
                    "examples": ["視聴者を掴む冒頭を考えて"]
                }
            ]
        }

    def get_system_prompt(self) -> str:
        return """あなたはYouTube動画台本の専門家です。

## 専門領域
- 視聴維持率を最大化する構成設計
- 視聴者を引き込むフック（冒頭15秒）
- 情報を分かりやすく伝えるスクリプト
- CTAの効果的な配置

## 台本の基本構成
1. **フック (0:00-0:15)**: 視聴者の注意を掴む
2. **導入 (0:15-1:00)**: 動画の価値を伝える
3. **本編**: セクション分けで情報整理
4. **まとめ**: 要点の振り返り
5. **CTA**: チャンネル登録・高評価の促し

## 出力形式
```
【タイトル案】
〇〇〇〇〇

【サムネイルコピー】
・メインコピー: 〇〇
・サブコピー: 〇〇

【構成】
00:00 フック
00:15 導入
...

【台本】
---フック---
(セリフ)

---導入---
(セリフ)
...
```

視聴者目線で、テンポよく、分かりやすい台本を作成してください。"""


if __name__ == "__main__":
    agent = YouTubeScriptWriterAgent(port=8081)
    print(f"Starting YouTube Script Writer Agent on port 8081...")
    agent.run()
