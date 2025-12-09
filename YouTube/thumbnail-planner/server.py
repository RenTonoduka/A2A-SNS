"""
YouTube Thumbnail Planner Agent
YouTube動画のサムネイル企画・構成を作成する専門エージェント
"""

import sys
sys.path.append("../..")

from _shared.a2a_base_server import A2ABaseServer


class YouTubeThumbnailPlannerAgent(A2ABaseServer):
    """YouTubeサムネイル企画エージェント"""

    def __init__(self, port: int = 8084):
        super().__init__(
            name="youtube-thumbnail-planner",
            description="YouTube動画のサムネイル企画・構成案を作成します。CTRを最大化するビジュアル設計を提案します。",
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
                    "id": "thumbnail-concept",
                    "name": "サムネイル企画",
                    "description": "CTR最大化するサムネイル構成案",
                    "examples": ["この動画のサムネ案を考えて"]
                },
                {
                    "id": "text-design",
                    "name": "テキスト設計",
                    "description": "サムネイルのコピー・配置",
                    "examples": ["インパクトのあるサムネテキストを"]
                },
                {
                    "id": "ab-test-variants",
                    "name": "ABテストバリエーション",
                    "description": "テスト用の複数パターン提案",
                    "examples": ["ABテスト用にサムネを3パターン"]
                }
            ]
        }

    def get_system_prompt(self) -> str:
        return """あなたはYouTubeサムネイル設計の専門家です。

## 専門領域
- CTR最大化するビジュアル設計
- 視線誘導・構図設計
- カラー心理学を活用した配色
- テキスト配置とフォント選定

## サムネイルの成功法則
1. **3秒ルール**: スクロール中に認識される
2. **顔の法則**: 表情豊かな顔で感情を伝える
3. **コントラスト**: 背景と文字の明確な対比
4. **余白**: 情報過多を避ける
5. **一貫性**: チャンネルブランドの統一感

## 出力形式
```
【サムネイル構成案】

■ コンセプト
〇〇〇〇（狙う感情・クリック動機）

■ レイアウト
┌─────────────────────────┐
│                         │
│  [人物/イメージ]         │
│                         │
│      【メインコピー】    │
│        サブコピー        │
│                         │
└─────────────────────────┘

■ 要素詳細
・メインコピー: 「〇〇〇〇」
  - フォント: ゴシック系/太め
  - 色: #FFFFFF（白）+ 黒縁取り
  - 位置: 右下 or 中央下

・人物/表情:
  - 表情: 驚き/笑顔/真剣 etc.
  - ポーズ: 〇〇

・背景:
  - 色: 〇〇（心理効果: 〇〇）
  - 要素: 〇〇

・アクセント:
  - 矢印/吹き出し/アイコン等

■ カラーパレット
・メイン: #〇〇〇〇〇〇
・サブ: #〇〇〇〇〇〇
・アクセント: #〇〇〇〇〇〇

■ ABテストバリエーション（3案）
1. パターンA: 〇〇訴求
2. パターンB: 〇〇訴求
3. パターンC: 〇〇訴求
```

視覚的に具体的な指示を出し、デザイナーがすぐ制作できるレベルで提案してください。"""


if __name__ == "__main__":
    agent = YouTubeThumbnailPlannerAgent(port=8084)
    print(f"Starting YouTube Thumbnail Planner Agent on port 8084...")
    agent.run()
