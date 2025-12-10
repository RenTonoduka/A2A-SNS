"""
X Post Generator - バズポストから自分のポストを生成
Claude Code CLIを使ってバズ要因を分析し、オリジナルポストを生成
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field

# パス設定
SCRIPT_DIR = Path(__file__).parent
SNS_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SNS_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from config import DATA_DIR, LOGS_DIR

# ログ設定
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# スプレッドシート連携
try:
    sys.path.insert(0, str(SNS_DIR / "_shared"))
    from sheets_logger import SheetsLogger
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    logger.info("Google Sheets integration not available")


@dataclass
class GeneratorConfig:
    """ポスト生成設定"""
    # 生成スタイル
    style: str = "informative"      # informative, entertaining, provocative, educational
    tone: str = "professional"       # professional, casual, humorous, inspirational
    language: str = "ja"             # ja, en

    # 制約
    max_length: int = 280            # 最大文字数
    include_hashtags: bool = True    # ハッシュタグを含める
    include_emoji: bool = True       # 絵文字を含める
    include_cta: bool = False        # CTA（Call to Action）を含める

    # 参照設定
    reference_count: int = 3         # 参考にするバズポスト数
    min_buzz_score: float = 2.0      # 最小バズスコア

    # 保存設定
    save_to_sheets: bool = True      # スプレッドシートに保存
    save_locally: bool = True        # ローカルに保存
    spreadsheet_id: Optional[str] = None  # スプレッドシートID


@dataclass
class GeneratedPost:
    """生成されたポスト"""
    content: str
    style: str
    tone: str
    hashtags: List[str] = field(default_factory=list)
    reference_posts: List[Dict] = field(default_factory=list)  # 参考にしたバズポスト
    buzz_patterns: List[str] = field(default_factory=list)     # 抽出したバズパターン
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    score: Optional[float] = None    # 予測エンゲージメントスコア


class PostGenerator:
    """
    バズポストからオリジナルポストを生成

    フロー:
    1. バズポストを読み込み
    2. バズ要因を分析（Claude Code CLI）
    3. パターンを抽出
    4. オリジナルポストを生成
    5. スプレッドシート/ローカルに保存
    """

    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        self.buzz_dir = DATA_DIR / "buzz"
        self.generated_dir = DATA_DIR / "generated"
        self.generated_dir.mkdir(parents=True, exist_ok=True)

        # スプレッドシートロガー
        self.sheets_logger = None
        if SHEETS_AVAILABLE and self.config.save_to_sheets:
            try:
                self.sheets_logger = SheetsLogger(self.config.spreadsheet_id)
            except Exception as e:
                logger.warning(f"Sheets logger init failed: {e}")

    # ==========================================
    # バズポスト読み込み
    # ==========================================

    def load_buzz_posts(self, limit: int = 10) -> List[Dict]:
        """保存されたバズポストを読み込み"""
        buzz_files = sorted(self.buzz_dir.glob("buzz_*.json"), reverse=True)

        all_posts = []
        for f in buzz_files:
            try:
                data = json.loads(f.read_text())
                posts = data.get("posts", [])
                all_posts.extend(posts)
            except Exception as e:
                logger.warning(f"Failed to load {f}: {e}")

        # バズスコアでフィルタ・ソート
        filtered = [
            p for p in all_posts
            if p.get("buzz_score", 0) >= self.config.min_buzz_score
        ]
        filtered.sort(key=lambda x: x.get("likes", 0), reverse=True)

        return filtered[:limit]

    def load_latest_buzz(self) -> List[Dict]:
        """最新のバズポストを読み込み"""
        return self.load_buzz_posts(limit=self.config.reference_count)

    # ==========================================
    # バズ分析（Claude Code CLI経由）
    # ==========================================

    def analyze_buzz_patterns(self, posts: List[Dict]) -> Dict[str, Any]:
        """
        バズポストのパターンを分析
        （この関数はClaude Code CLIから呼ばれることを想定）
        """
        if not posts:
            return {"patterns": [], "insights": []}

        analysis = {
            "total_posts": len(posts),
            "avg_likes": sum(p.get("likes", 0) for p in posts) / len(posts),
            "avg_retweets": sum(p.get("retweets", 0) for p in posts) / len(posts),
            "common_patterns": [],
            "content_themes": [],
            "posting_insights": []
        }

        # コンテンツ分析
        contents = [p.get("content", "") for p in posts]

        # 文字数分析
        lengths = [len(c) for c in contents]
        analysis["avg_length"] = sum(lengths) / len(lengths) if lengths else 0

        # 絵文字使用率
        emoji_count = sum(1 for c in contents if any(ord(ch) > 127 for ch in c))
        analysis["emoji_usage_rate"] = emoji_count / len(contents) if contents else 0

        # ハッシュタグ分析
        hashtags = []
        for c in contents:
            hashtags.extend([word for word in c.split() if word.startswith("#")])
        analysis["common_hashtags"] = list(set(hashtags))[:10]

        return analysis

    # ==========================================
    # ポスト生成プロンプト
    # ==========================================

    def get_generation_prompt(self, buzz_posts: List[Dict], topic: Optional[str] = None) -> str:
        """ポスト生成用のプロンプトを作成"""

        # バズポストサマリー
        buzz_summary = []
        for i, post in enumerate(buzz_posts[:5], 1):
            buzz_summary.append(
                f"{i}. @{post.get('author_username', 'unknown')}\n"
                f"   内容: {post.get('content', '')[:100]}...\n"
                f"   いいね: {post.get('likes', 0):,} / RT: {post.get('retweets', 0):,}\n"
                f"   バズスコア: {post.get('buzz_score', 0):.1f}x"
            )

        prompt = f"""以下のバズポストを参考に、オリジナルのXポストを生成してください。

## 参考バズポスト

{chr(10).join(buzz_summary)}

## 生成条件

- スタイル: {self.config.style}
- トーン: {self.config.tone}
- 言語: {self.config.language}
- 最大文字数: {self.config.max_length}
- ハッシュタグ: {"含める" if self.config.include_hashtags else "含めない"}
- 絵文字: {"含める" if self.config.include_emoji else "含めない"}
- CTA: {"含める" if self.config.include_cta else "含めない"}
"""

        if topic:
            prompt += f"\n## トピック/テーマ\n{topic}\n"

        prompt += """
## 出力形式

以下のJSON形式で出力してください:

```json
{
  "posts": [
    {
      "content": "生成したポスト本文",
      "hashtags": ["#タグ1", "#タグ2"],
      "buzz_patterns_used": ["使用したバズパターン1", "パターン2"],
      "predicted_engagement": "high/medium/low",
      "reasoning": "このポストがバズると予測した理由"
    }
  ],
  "analysis": {
    "common_patterns": ["発見したバズパターン"],
    "recommendations": ["改善提案"]
  }
}
```

3つのバリエーションを生成してください。
"""

        return prompt

    # ==========================================
    # 保存
    # ==========================================

    def save_generated_posts(
        self,
        posts: List[GeneratedPost],
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成したポストを保存"""
        result = {"local": None, "sheets": None}

        # ローカル保存
        if self.config.save_locally:
            filename = filename or f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            filepath = self.generated_dir / f"{filename}.json"

            data = {
                "generated_at": datetime.now().isoformat(),
                "config": asdict(self.config),
                "posts": [asdict(p) for p in posts]
            }
            filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            result["local"] = str(filepath)
            logger.info(f"💾 Saved to {filepath}")

        # スプレッドシート保存
        if self.config.save_to_sheets and self.sheets_logger:
            try:
                for post in posts:
                    self.sheets_logger.log_generated_post({
                        "content": post.content,
                        "style": post.style,
                        "tone": post.tone,
                        "hashtags": ", ".join(post.hashtags),
                        "buzz_patterns": ", ".join(post.buzz_patterns),
                        "generated_at": post.generated_at,
                        "score": post.score or ""
                    })
                result["sheets"] = "logged"
                logger.info("📊 Logged to Google Sheets")
            except Exception as e:
                logger.warning(f"Sheets logging failed: {e}")

        return result

    def save_buzz_to_sheets(self, posts: List[Dict]) -> bool:
        """バズポストをスプレッドシートに保存"""
        if not self.sheets_logger:
            logger.warning("Sheets logger not available")
            return False

        try:
            for post in posts:
                self.sheets_logger.log_buzz_post({
                    "post_id": post.get("post_id", ""),
                    "author": post.get("author_username", ""),
                    "content": post.get("content", "")[:500],
                    "likes": post.get("likes", 0),
                    "retweets": post.get("retweets", 0),
                    "buzz_score": post.get("buzz_score", 0),
                    "post_url": post.get("post_url", ""),
                    "detected_at": post.get("detected_at", "")
                })
            logger.info(f"📊 Saved {len(posts)} buzz posts to Sheets")
            return True
        except Exception as e:
            logger.error(f"Failed to save to sheets: {e}")
            return False

    # ==========================================
    # メインフロー
    # ==========================================

    def generate_from_buzz(
        self,
        topic: Optional[str] = None,
        count: int = 3
    ) -> Dict[str, Any]:
        """
        バズポストから新しいポストを生成

        Returns:
            {
                "prompt": "生成に使用したプロンプト",
                "buzz_posts": [...],  # 参考にしたバズポスト
                "analysis": {...},    # バズ分析結果
            }

        ※実際の生成はClaude Code CLIが行う
        """
        # バズポスト読み込み
        buzz_posts = self.load_latest_buzz()

        if not buzz_posts:
            return {
                "error": "バズポストが見つかりません。先に /monitor でバズポストを検出してください。",
                "buzz_posts": [],
                "prompt": None
            }

        # バズ分析
        analysis = self.analyze_buzz_patterns(buzz_posts)

        # プロンプト生成
        prompt = self.get_generation_prompt(buzz_posts, topic)

        return {
            "prompt": prompt,
            "buzz_posts": buzz_posts,
            "analysis": analysis,
            "config": asdict(self.config)
        }

    def get_recent_generated(self, limit: int = 10) -> List[Dict]:
        """最近生成したポストを取得"""
        files = sorted(self.generated_dir.glob("generated_*.json"), reverse=True)

        all_posts = []
        for f in files[:limit]:
            try:
                data = json.loads(f.read_text())
                all_posts.extend(data.get("posts", []))
            except:
                pass

        return all_posts[:limit]


# ==========================================
# CLI
# ==========================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="X Post Generator")
    parser.add_argument("command", choices=["generate", "analyze", "list", "save-buzz"],
                       help="generate: ポスト生成, analyze: バズ分析, list: 生成履歴, save-buzz: バズをスプシに保存")
    parser.add_argument("--topic", "-t", help="生成トピック")
    parser.add_argument("--style", choices=["informative", "entertaining", "provocative", "educational"],
                       default="informative", help="生成スタイル")
    parser.add_argument("--tone", choices=["professional", "casual", "humorous", "inspirational"],
                       default="professional", help="トーン")
    parser.add_argument("--count", type=int, default=3, help="生成数")
    parser.add_argument("--limit", type=int, default=10, help="表示件数")
    parser.add_argument("--spreadsheet-id", help="スプレッドシートID")
    parser.add_argument("--no-sheets", action="store_true", help="スプシ保存を無効化")

    args = parser.parse_args()

    config = GeneratorConfig(
        style=args.style,
        tone=args.tone,
        save_to_sheets=not args.no_sheets,
        spreadsheet_id=args.spreadsheet_id
    )

    generator = PostGenerator(config)

    if args.command == "generate":
        print("=" * 60)
        print("🚀 X Post Generator")
        print("=" * 60)

        result = generator.generate_from_buzz(topic=args.topic, count=args.count)

        if "error" in result:
            print(f"❌ {result['error']}")
            return

        print(f"\n📊 バズポスト分析:")
        print(f"  参照数: {len(result['buzz_posts'])}件")
        print(f"  平均いいね: {result['analysis'].get('avg_likes', 0):,.0f}")

        print(f"\n📝 生成プロンプト:")
        print("-" * 40)
        print(result["prompt"][:500] + "...")
        print("-" * 40)

        print("\n💡 このプロンプトをClaude Code CLIに渡してポストを生成してください")
        print("   または A2A経由で /generate コマンドを使用")

    elif args.command == "analyze":
        buzz_posts = generator.load_buzz_posts(limit=args.limit)

        if not buzz_posts:
            print("❌ バズポストが見つかりません")
            return

        analysis = generator.analyze_buzz_patterns(buzz_posts)

        print("=" * 60)
        print("📊 バズポスト分析")
        print("=" * 60)
        print(f"  総数: {analysis['total_posts']}件")
        print(f"  平均いいね: {analysis['avg_likes']:,.0f}")
        print(f"  平均RT: {analysis['avg_retweets']:,.0f}")
        print(f"  平均文字数: {analysis['avg_length']:.0f}")
        print(f"  絵文字使用率: {analysis['emoji_usage_rate']*100:.1f}%")

        if analysis["common_hashtags"]:
            print(f"\n📌 よく使われるハッシュタグ:")
            for tag in analysis["common_hashtags"][:5]:
                print(f"    {tag}")

    elif args.command == "list":
        posts = generator.get_recent_generated(limit=args.limit)

        if not posts:
            print("❌ 生成履歴がありません")
            return

        print("=" * 60)
        print("📝 生成履歴")
        print("=" * 60)

        for i, post in enumerate(posts, 1):
            content = post.get("content", "")[:80]
            print(f"\n{i}. {content}...")
            print(f"   スタイル: {post.get('style')} / トーン: {post.get('tone')}")
            print(f"   生成日時: {post.get('generated_at', '')[:19]}")

    elif args.command == "save-buzz":
        buzz_posts = generator.load_buzz_posts(limit=args.limit)

        if not buzz_posts:
            print("❌ バズポストが見つかりません")
            return

        if generator.save_buzz_to_sheets(buzz_posts):
            print(f"✅ {len(buzz_posts)}件のバズポストをスプレッドシートに保存しました")
        else:
            print("❌ スプレッドシート保存に失敗しました")


if __name__ == "__main__":
    main()
