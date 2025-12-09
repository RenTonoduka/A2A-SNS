"""
YouTube SEO Optimizer Agent
YouTube動画のタイトル・説明・タグを最適化する専門エージェント
"""

import sys
sys.path.append("../..")

from _shared.a2a_base_server import A2ABaseServer


class YouTubeSEOOptimizerAgent(A2ABaseServer):
    """YouTube SEO最適化エージェント"""

    def __init__(self, port: int = 8083):
        super().__init__(
            name="youtube-seo-optimizer",
            description="YouTube動画のSEOを最適化します。タイトル、説明文、タグ、チャプターを検索・レコメンド最適化します。",
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
                    "id": "title-optimization",
                    "name": "タイトル最適化",
                    "description": "CTR最大化するタイトル作成",
                    "examples": ["この動画のタイトル案を出して"]
                },
                {
                    "id": "description-writing",
                    "name": "説明文作成",
                    "description": "SEO最適化された説明文",
                    "examples": ["動画の説明文を作成して"]
                },
                {
                    "id": "tag-research",
                    "name": "タグ設計",
                    "description": "効果的なタグ選定",
                    "examples": ["最適なタグを提案して"]
                },
                {
                    "id": "chapter-design",
                    "name": "チャプター設計",
                    "description": "検索に強いチャプター構成",
                    "examples": ["チャプターを設定して"]
                }
            ]
        }

    def get_system_prompt(self) -> str:
        return """あなたはYouTube SEOの専門家です。

## 専門領域
- 検索アルゴリズム最適化
- クリック率(CTR)最大化タイトル
- 説明文のSEO対策
- タグ戦略
- チャプター最適化

## タイトル作成の原則
1. **キーワード**: 主要キーワードを前方に配置
2. **数字**: 具体的な数字で興味を引く
3. **感情**: 好奇心・緊急性・共感を喚起
4. **長さ**: 40-60文字（モバイル表示を考慮）

## 出力形式
```
【タイトル案】（5パターン）
1. 〇〇〇〇（CTR重視）
2. 〇〇〇〇（SEO重視）
3. 〇〇〇〇（感情訴求）
4. 〇〇〇〇（数字活用）
5. 〇〇〇〇（ベストバランス）★推奨

【説明文】
(最初の2行が検索結果に表示されるため重要)

〇〇〇〇...

▼目次
00:00 はじめに
00:30 〇〇
...

▼関連動画
・〇〇〇〇

▼SNS
・Twitter: 〇〇
・Instagram: 〇〇

#タグ1 #タグ2 #タグ3

【タグ一覧】（15-20個）
メインキーワード, 関連キーワード, ロングテール, ...

【チャプター】
00:00 はじめに
00:30 〇〇のポイント
...
```

検索流入とCTRの両方を最大化する提案をしてください。"""


if __name__ == "__main__":
    agent = YouTubeSEOOptimizerAgent(port=8083)
    print(f"Starting YouTube SEO Optimizer Agent on port 8083...")
    agent.run()
