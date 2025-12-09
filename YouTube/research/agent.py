"""
YouTube Research Agent
TubeAIのコア機能を抽出したリサーチエージェント

機能:
1. キーワード市場分析
2. 競合チャンネル発見
3. トレンド分析
4. 機会スコアリング
"""

import os
import sys
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# 親ディレクトリをパスに追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SNS_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, SNS_DIR)

from _shared.claude_runner import ClaudeRunner


@dataclass
class ChannelData:
    """チャンネル情報"""
    channel_id: str
    title: str
    subscriber_count: int
    view_count: int
    video_count: int
    engagement_rate: float = 0.0
    opportunity_score: float = 0.0


@dataclass
class KeywordData:
    """キーワード情報"""
    keyword: str
    search_volume: int = 0
    competition: str = "medium"  # low, medium, high
    opportunity_score: float = 0.0
    related_keywords: List[str] = None

    def __post_init__(self):
        if self.related_keywords is None:
            self.related_keywords = []


@dataclass
class ResearchResult:
    """リサーチ結果"""
    theme: str
    timestamp: str
    keywords: List[KeywordData]
    channels: List[ChannelData]
    trends: List[str]
    content_ideas: List[str]
    strategy_suggestions: List[str]


class YouTubeResearchAgent:
    """
    YouTubeリサーチエージェント

    TubeAIのコア機能を抽出:
    - キーワード生成・分析
    - 競合チャンネル発見
    - 機会スコアリング
    - 戦略提案
    """

    def __init__(self, workspace: str = "."):
        self.workspace = workspace
        self.claude = ClaudeRunner(workspace=workspace, timeout=180)

        # システムプロンプト
        self.system_prompt = """あなたはYouTubeマーケットリサーチの専門家です。

## 役割
- キーワード市場分析
- 競合チャンネル発見と評価
- トレンド分析と機会特定
- コンテンツ戦略提案

## 分析の観点
1. 検索ボリューム（需要の大きさ）
2. 競争度（参入障壁）
3. 成長率（トレンド性）
4. 収益性（CPM、広告単価）
5. 視聴者エンゲージメント

## 出力形式
必ずJSON形式で出力してください。"""

    def research_theme(self, theme: str, language: str = "ja") -> ResearchResult:
        """
        テーマに基づく総合リサーチ

        Args:
            theme: リサーチテーマ（例: "AI副業", "プログラミング学習"）
            language: 言語コード

        Returns:
            ResearchResult: リサーチ結果
        """
        prompt = f"""{self.system_prompt}

## タスク
以下のテーマについてYouTube市場リサーチを行ってください。

テーマ: {theme}
言語: {language}

## 出力形式（JSON）
{{
    "keywords": [
        {{
            "keyword": "キーワード",
            "search_volume_estimate": "high/medium/low",
            "competition": "high/medium/low",
            "opportunity_score": 0-100,
            "related_keywords": ["関連1", "関連2"]
        }}
    ],
    "trending_topics": ["トレンド1", "トレンド2"],
    "content_ideas": [
        "動画アイデア1",
        "動画アイデア2"
    ],
    "competitor_channels": [
        {{
            "channel_name": "チャンネル名",
            "subscriber_estimate": "10万以上/1-10万/1万未満",
            "content_style": "教育系/エンタメ系/etc",
            "strength": "強み",
            "weakness": "弱み"
        }}
    ],
    "strategy_suggestions": [
        "戦略提案1",
        "戦略提案2"
    ],
    "market_summary": "市場の総合評価（2-3文）"
}}

JSONのみを出力してください。"""

        result = self.claude.run(prompt)

        if not result["success"]:
            raise Exception(f"Research failed: {result['error']}")

        return self._parse_research_result(theme, result["output"])

    def analyze_keyword(self, keyword: str) -> KeywordData:
        """
        単一キーワードの詳細分析
        """
        prompt = f"""{self.system_prompt}

## タスク
以下のキーワードについてYouTube市場分析を行ってください。

キーワード: {keyword}

## 出力形式（JSON）
{{
    "keyword": "{keyword}",
    "search_volume_estimate": "high/medium/low",
    "competition": "high/medium/low",
    "opportunity_score": 0-100,
    "related_keywords": ["関連キーワード1", "関連キーワード2", ...],
    "recommended_title_patterns": ["パターン1", "パターン2"],
    "content_angle_suggestions": ["切り口1", "切り口2"],
    "target_audience": "ターゲット視聴者の説明",
    "monetization_potential": "high/medium/low"
}}

JSONのみを出力してください。"""

        result = self.claude.run(prompt)

        if not result["success"]:
            raise Exception(f"Keyword analysis failed: {result['error']}")

        return self._parse_keyword_result(result["output"])

    def discover_competitors(self, niche: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        ニッチ分野の競合チャンネル発見
        """
        prompt = f"""{self.system_prompt}

## タスク
以下のニッチ分野で注目すべきYouTubeチャンネルを{limit}個発見してください。

ニッチ: {niche}

## 出力形式（JSON）
{{
    "competitors": [
        {{
            "channel_name": "チャンネル名",
            "niche_fit": "high/medium/low",
            "estimated_subscribers": "概算登録者数",
            "content_frequency": "投稿頻度",
            "content_style": "コンテンツスタイル",
            "unique_value": "独自の価値",
            "strengths": ["強み1", "強み2"],
            "weaknesses": ["弱み1"],
            "opportunity_to_beat": "勝てるポイント"
        }}
    ],
    "market_gaps": ["ギャップ1", "ギャップ2"],
    "differentiation_opportunities": ["差別化ポイント1", "差別化ポイント2"]
}}

JSONのみを出力してください。"""

        result = self.claude.run(prompt)

        if not result["success"]:
            raise Exception(f"Competitor discovery failed: {result['error']}")

        try:
            data = json.loads(self._extract_json(result["output"]))
            return data.get("competitors", [])
        except json.JSONDecodeError:
            return []

    def generate_content_ideas(self, theme: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        コンテンツアイデア生成
        """
        prompt = f"""{self.system_prompt}

## タスク
以下のテーマで視聴者を惹きつけるYouTube動画アイデアを{count}個生成してください。

テーマ: {theme}

## 出力形式（JSON）
{{
    "ideas": [
        {{
            "title": "動画タイトル案",
            "hook": "冒頭のフック（最初の5秒）",
            "target_audience": "ターゲット視聴者",
            "estimated_length": "想定尺（分）",
            "content_structure": ["セクション1", "セクション2", ...],
            "cta": "行動喚起",
            "thumbnail_concept": "サムネイルコンセプト",
            "viral_potential": "high/medium/low",
            "production_difficulty": "high/medium/low"
        }}
    ]
}}

JSONのみを出力してください。"""

        result = self.claude.run(prompt)

        if not result["success"]:
            raise Exception(f"Content idea generation failed: {result['error']}")

        try:
            data = json.loads(self._extract_json(result["output"]))
            return data.get("ideas", [])
        except json.JSONDecodeError:
            return []

    def analyze_trends(self, category: str = "technology") -> Dict[str, Any]:
        """
        カテゴリ別トレンド分析
        """
        prompt = f"""{self.system_prompt}

## タスク
YouTubeの{category}カテゴリにおける最新トレンドを分析してください。

## 出力形式（JSON）
{{
    "category": "{category}",
    "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
    "rising_topics": [
        {{
            "topic": "トピック名",
            "growth_rate": "急上昇/上昇中/安定",
            "peak_timing": "ピーク予測",
            "content_opportunity": "コンテンツ機会の説明"
        }}
    ],
    "declining_topics": ["下降トピック1", "下降トピック2"],
    "evergreen_topics": ["常緑トピック1", "常緑トピック2"],
    "format_trends": {{
        "popular_formats": ["ショート", "解説", "Vlog", ...],
        "emerging_formats": ["新形式1", "新形式2"]
    }},
    "audience_behavior": {{
        "preferred_length": "好まれる動画尺",
        "engagement_patterns": "エンゲージメントパターン",
        "peak_viewing_times": "視聴ピーク時間"
    }},
    "recommendations": ["推奨アクション1", "推奨アクション2"]
}}

JSONのみを出力してください。"""

        result = self.claude.run(prompt)

        if not result["success"]:
            raise Exception(f"Trend analysis failed: {result['error']}")

        try:
            return json.loads(self._extract_json(result["output"]))
        except json.JSONDecodeError:
            return {"error": "Failed to parse trends"}

    def _extract_json(self, text: str) -> str:
        """テキストからJSON部分を抽出"""
        # ```json ... ``` を除去
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        # ```を除去
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        # { から始まる部分を探す
        start = text.find("{")
        if start >= 0:
            # 対応する } を探す
            depth = 0
            for i, c in enumerate(text[start:]):
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start:start + i + 1]

        return text

    def _parse_research_result(self, theme: str, output: str) -> ResearchResult:
        """リサーチ結果をパース"""
        try:
            data = json.loads(self._extract_json(output))

            keywords = []
            for kw in data.get("keywords", []):
                keywords.append(KeywordData(
                    keyword=kw.get("keyword", ""),
                    search_volume=self._estimate_volume(kw.get("search_volume_estimate", "medium")),
                    competition=kw.get("competition", "medium"),
                    opportunity_score=kw.get("opportunity_score", 50),
                    related_keywords=kw.get("related_keywords", [])
                ))

            channels = []
            for ch in data.get("competitor_channels", []):
                channels.append(ChannelData(
                    channel_id="",
                    title=ch.get("channel_name", ""),
                    subscriber_count=self._estimate_subscribers(ch.get("subscriber_estimate", "")),
                    view_count=0,
                    video_count=0
                ))

            return ResearchResult(
                theme=theme,
                timestamp=datetime.now().isoformat(),
                keywords=keywords,
                channels=channels,
                trends=data.get("trending_topics", []),
                content_ideas=data.get("content_ideas", []),
                strategy_suggestions=data.get("strategy_suggestions", [])
            )

        except json.JSONDecodeError:
            return ResearchResult(
                theme=theme,
                timestamp=datetime.now().isoformat(),
                keywords=[],
                channels=[],
                trends=[],
                content_ideas=[],
                strategy_suggestions=[]
            )

    def _parse_keyword_result(self, output: str) -> KeywordData:
        """キーワード結果をパース"""
        try:
            data = json.loads(self._extract_json(output))
            return KeywordData(
                keyword=data.get("keyword", ""),
                search_volume=self._estimate_volume(data.get("search_volume_estimate", "medium")),
                competition=data.get("competition", "medium"),
                opportunity_score=data.get("opportunity_score", 50),
                related_keywords=data.get("related_keywords", [])
            )
        except json.JSONDecodeError:
            return KeywordData(keyword="", search_volume=0)

    def _estimate_volume(self, estimate: str) -> int:
        """検索ボリュームの概算値"""
        mapping = {
            "high": 100000,
            "medium": 10000,
            "low": 1000
        }
        return mapping.get(estimate.lower(), 10000)

    def _estimate_subscribers(self, estimate: str) -> int:
        """登録者数の概算値"""
        if "10万" in estimate or "100k" in estimate.lower():
            return 100000
        elif "1万" in estimate or "10k" in estimate.lower():
            return 10000
        elif "1-10万" in estimate:
            return 50000
        return 5000

    def save_result(self, result: ResearchResult, output_dir: str = "./research_results"):
        """リサーチ結果を保存"""
        os.makedirs(output_dir, exist_ok=True)

        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{result.theme.replace(' ', '_')}.json"
        filepath = os.path.join(output_dir, filename)

        # dataclassをdictに変換
        data = {
            "theme": result.theme,
            "timestamp": result.timestamp,
            "keywords": [asdict(kw) for kw in result.keywords],
            "channels": [asdict(ch) for ch in result.channels],
            "trends": result.trends,
            "content_ideas": result.content_ideas,
            "strategy_suggestions": result.strategy_suggestions
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath


# CLI実行用
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Research Agent")
    parser.add_argument("theme", help="Research theme")
    parser.add_argument("--output", "-o", default="./research_results", help="Output directory")
    args = parser.parse_args()

    print(f"🔍 Researching: {args.theme}")
    print("=" * 50)

    agent = YouTubeResearchAgent()

    try:
        result = agent.research_theme(args.theme)

        print(f"\n📊 Keywords ({len(result.keywords)}):")
        for kw in result.keywords[:5]:
            print(f"  • {kw.keyword} (Score: {kw.opportunity_score})")

        print(f"\n📈 Trends ({len(result.trends)}):")
        for trend in result.trends[:5]:
            print(f"  • {trend}")

        print(f"\n💡 Content Ideas ({len(result.content_ideas)}):")
        for idea in result.content_ideas[:5]:
            print(f"  • {idea}")

        print(f"\n🎯 Strategy Suggestions ({len(result.strategy_suggestions)}):")
        for suggestion in result.strategy_suggestions[:3]:
            print(f"  • {suggestion}")

        # 結果を保存
        filepath = agent.save_result(result, args.output)
        print(f"\n✅ Saved to: {filepath}")

    except Exception as e:
        print(f"❌ Error: {e}")
