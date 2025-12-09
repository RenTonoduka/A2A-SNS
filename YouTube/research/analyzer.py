"""
YouTube Data Analyzer
実データをClaude Codeに渡して分析・評価させる

スクリプト: データ取得
Claude Code: 分析・評価・判断
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# パス設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SNS_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, SNS_DIR)

from _shared.claude_runner import ClaudeRunner
from youtube.research.youtube_api import YouTubeAPIClient, ChannelData, VideoData


@dataclass
class VideoAnalysis:
    """動画分析結果"""
    video_id: str
    title: str
    view_count: int
    subscriber_count: int
    performance_ratio: float  # 再生数 / 登録者数
    is_outstanding: bool  # 優秀判定
    analysis: str  # Claude Codeによる分析


@dataclass
class CompetitorAnalysis:
    """競合分析結果"""
    channel_id: str
    channel_title: str
    subscriber_count: int
    outstanding_videos: List[VideoAnalysis]
    content_patterns: List[str]
    success_factors: List[str]
    opportunities: List[str]


class YouTubeAnalyzer:
    """
    YouTubeデータ分析エージェント

    1. YouTube APIで実データ取得（スクリプト）
    2. Claude Codeに渡して分析・評価（AI判断）
    """

    def __init__(self, api_key: Optional[str] = None, workspace: str = "."):
        self.api = YouTubeAPIClient(api_key)
        self.claude = ClaudeRunner(workspace=workspace, timeout=180)

    def find_outstanding_videos(
        self,
        keyword: str,
        min_channels: int = 5,
        videos_per_channel: int = 10,
        performance_threshold: float = 2.0  # 登録者の2倍以上の再生数
    ) -> Dict[str, Any]:
        """
        キーワードで競合を探し、優秀な動画を発見

        「登録者数が少ないのに高い再生回数」= 優秀な動画

        Args:
            keyword: 検索キーワード
            min_channels: 分析するチャンネル数
            videos_per_channel: チャンネルごとの取得動画数
            performance_threshold: 優秀判定の閾値（再生数/登録者数）

        Returns:
            {
                "keyword": str,
                "channels_analyzed": int,
                "outstanding_videos": [...],  # 優秀な動画一覧
                "analysis": str  # Claude Codeによる総合分析
            }
        """
        print(f"🔍 Searching channels for: {keyword}")

        # 1. チャンネル検索
        channels = self.api.search_channels(keyword, max_results=min_channels)

        if not channels:
            return {"error": "No channels found", "keyword": keyword}

        print(f"📺 Found {len(channels)} channels")

        # 2. 各チャンネルの上位動画を取得
        all_data = []
        outstanding_videos = []

        for ch in channels:
            print(f"  Analyzing: {ch.title} ({ch.subscriber_count:,} subs)")

            data = self.api.get_top_videos_with_channel_info(
                ch.channel_id,
                top_n=videos_per_channel
            )

            if not data:
                continue

            all_data.append(data)

            # 優秀な動画を抽出（登録者数に対して高再生）
            for video in data["top_videos"]:
                if ch.subscriber_count > 0:
                    ratio = video["view_count"] / ch.subscriber_count
                    if ratio >= performance_threshold:
                        outstanding_videos.append({
                            "video_id": video["video_id"],
                            "title": video["title"],
                            "channel_title": ch.title,
                            "view_count": video["view_count"],
                            "subscriber_count": ch.subscriber_count,
                            "performance_ratio": round(ratio, 2),
                            "like_count": video["like_count"],
                            "comment_count": video["comment_count"],
                            "published_at": video["published_at"],
                            "tags": video.get("tags", [])[:10]
                        })

        # パフォーマンス比で降順ソート
        outstanding_videos.sort(key=lambda x: x["performance_ratio"], reverse=True)

        print(f"⭐ Found {len(outstanding_videos)} outstanding videos")

        # 3. Claude Codeに分析を依頼
        analysis = self._analyze_with_claude(keyword, all_data, outstanding_videos)

        return {
            "keyword": keyword,
            "analyzed_at": datetime.now().isoformat(),
            "channels_analyzed": len(channels),
            "total_videos_checked": sum(len(d["top_videos"]) for d in all_data),
            "outstanding_videos": outstanding_videos[:20],  # 上位20件
            "analysis": analysis
        }

    def _analyze_with_claude(
        self,
        keyword: str,
        channel_data: List[Dict],
        outstanding_videos: List[Dict]
    ) -> Dict[str, Any]:
        """
        Claude Codeにデータを渡して分析させる
        """
        # データを整形
        data_summary = {
            "keyword": keyword,
            "channels": [
                {
                    "title": d["channel"]["title"],
                    "subscribers": d["channel"]["subscriber_count"],
                    "total_views": d["channel"]["view_count"],
                    "videos_to_subs_ratio": d["metrics"]["views_to_subs_ratio"]
                }
                for d in channel_data
            ],
            "outstanding_videos": outstanding_videos[:15]  # 上位15件
        }

        prompt = f"""あなたはYouTubeマーケティングの専門アナリストです。

以下の実データを分析して、コンテンツ戦略の洞察を提供してください。

## 分析対象データ
```json
{json.dumps(data_summary, ensure_ascii=False, indent=2)}
```

## 分析観点

### 1. 優秀動画の共通パターン
「登録者数に対して再生数が異常に高い」動画の共通点を特定してください。
- タイトルのパターン（数字、疑問形、煽り等）
- テーマの傾向
- 投稿タイミング

### 2. 成功要因分析
なぜこれらの動画は登録者数以上のリーチを獲得できたのか？
- アルゴリズム的要因
- コンテンツ的要因
- タイミング要因

### 3. 再現可能な戦略
このデータから導き出せる、実行可能な戦略は？
- 狙うべきテーマ
- タイトル設計のポイント
- 差別化の方向性

### 4. 機会とリスク
- 参入機会（空いているニッチ）
- リスク（競争激化の兆候等）

## 出力形式（JSON）
{{
    "title_patterns": ["パターン1", "パターン2", ...],
    "success_factors": ["要因1", "要因2", ...],
    "recommended_themes": ["テーマ1", "テーマ2", ...],
    "recommended_title_templates": ["【数字】〇〇が△△する方法", ...],
    "differentiation_strategies": ["戦略1", "戦略2", ...],
    "opportunities": ["機会1", "機会2", ...],
    "risks": ["リスク1", "リスク2", ...],
    "action_items": ["アクション1", "アクション2", ...],
    "summary": "3文程度の総括"
}}

データに基づいた具体的な分析をJSON形式のみで出力してください。"""

        result = self.claude.run(prompt)

        if not result["success"]:
            return {"error": result["error"]}

        try:
            return json.loads(self._extract_json(result["output"]))
        except json.JSONDecodeError:
            return {"raw_analysis": result["output"]}

    def analyze_single_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        単一チャンネルの詳細分析
        """
        data = self.api.get_top_videos_with_channel_info(channel_id, top_n=20)

        if not data:
            return {"error": "Channel not found"}

        # Claude Codeに分析を依頼
        prompt = f"""以下のYouTubeチャンネルデータを分析してください。

## チャンネル情報
```json
{json.dumps(data, ensure_ascii=False, indent=2)}
```

## 分析項目
1. コンテンツ戦略の特徴
2. 成功している動画の共通点
3. 改善の余地がある点
4. このチャンネルから学べること

## 出力形式（JSON）
{{
    "channel_strategy": "戦略の説明",
    "content_pillars": ["柱1", "柱2", ...],
    "successful_patterns": ["パターン1", "パターン2", ...],
    "improvement_areas": ["改善点1", "改善点2", ...],
    "learnings": ["学び1", "学び2", ...],
    "competitive_advantage": "このチャンネルの強み",
    "vulnerability": "このチャンネルの弱点"
}}

JSONのみを出力してください。"""

        result = self.claude.run(prompt)

        if not result["success"]:
            return {"error": result["error"], "channel_data": data}

        try:
            analysis = json.loads(self._extract_json(result["output"]))
            return {
                "channel": data["channel"],
                "metrics": data["metrics"],
                "top_videos": data["top_videos"][:10],
                "analysis": analysis
            }
        except json.JSONDecodeError:
            return {"channel": data["channel"], "raw_analysis": result["output"]}

    def compare_channels(self, channel_ids: List[str]) -> Dict[str, Any]:
        """
        複数チャンネルの比較分析
        """
        channels_data = []

        for cid in channel_ids:
            data = self.api.get_top_videos_with_channel_info(cid, top_n=10)
            if data:
                channels_data.append(data)

        if not channels_data:
            return {"error": "No channels found"}

        # Claude Codeに比較分析を依頼
        prompt = f"""以下の複数YouTubeチャンネルを比較分析してください。

## チャンネルデータ
```json
{json.dumps(channels_data, ensure_ascii=False, indent=2)}
```

## 比較観点
1. 各チャンネルの特徴と強み
2. コンテンツ戦略の違い
3. パフォーマンス指標の比較
4. 最も学ぶべきチャンネルとその理由
5. 市場でのポジショニング

## 出力形式（JSON）
{{
    "comparison_matrix": {{
        "channel_name": {{
            "strengths": [...],
            "weaknesses": [...],
            "strategy": "戦略説明"
        }}
    }},
    "best_performer": {{
        "channel": "チャンネル名",
        "reason": "理由"
    }},
    "learnings": ["学び1", "学び2", ...],
    "market_gaps": ["ギャップ1", "ギャップ2", ...],
    "recommended_positioning": "推奨ポジショニング"
}}

JSONのみを出力してください。"""

        result = self.claude.run(prompt)

        if not result["success"]:
            return {"error": result["error"]}

        try:
            analysis = json.loads(self._extract_json(result["output"]))
            return {
                "channels_compared": len(channels_data),
                "analysis": analysis
            }
        except json.JSONDecodeError:
            return {"raw_analysis": result["output"]}

    def _extract_json(self, text: str) -> str:
        """テキストからJSON部分を抽出"""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        start = text.find("{")
        if start >= 0:
            depth = 0
            for i, c in enumerate(text[start:]):
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start:start + i + 1]

        return text

    def save_analysis(self, result: Dict[str, Any], output_dir: str = "./analysis_results"):
        """分析結果を保存"""
        os.makedirs(output_dir, exist_ok=True)

        keyword = result.get("keyword", "analysis")
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{keyword.replace(' ', '_')}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return filepath


# CLI実行用
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Data Analyzer")
    parser.add_argument("keyword", help="Search keyword")
    parser.add_argument("--channels", "-c", type=int, default=5, help="Number of channels to analyze")
    parser.add_argument("--threshold", "-t", type=float, default=2.0, help="Performance threshold (views/subs ratio)")
    parser.add_argument("--output", "-o", default="./analysis_results", help="Output directory")
    args = parser.parse_args()

    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("❌ YOUTUBE_API_KEY not set")
        print("Set it with: export YOUTUBE_API_KEY='your-api-key'")
        sys.exit(1)

    print(f"🔍 Analyzing: {args.keyword}")
    print(f"📊 Channels: {args.channels}, Threshold: {args.threshold}x")
    print("=" * 60)

    analyzer = YouTubeAnalyzer(api_key)

    result = analyzer.find_outstanding_videos(
        args.keyword,
        min_channels=args.channels,
        performance_threshold=args.threshold
    )

    if "error" in result:
        print(f"❌ Error: {result['error']}")
        sys.exit(1)

    print(f"\n📈 Results")
    print("-" * 60)
    print(f"Channels analyzed: {result['channels_analyzed']}")
    print(f"Total videos checked: {result['total_videos_checked']}")
    print(f"Outstanding videos found: {len(result['outstanding_videos'])}")

    print(f"\n⭐ Top Outstanding Videos:")
    for i, v in enumerate(result["outstanding_videos"][:10], 1):
        print(f"  {i}. {v['title'][:50]}...")
        print(f"     Channel: {v['channel_title']}")
        print(f"     Views: {v['view_count']:,} | Subs: {v['subscriber_count']:,} | Ratio: {v['performance_ratio']}x")
        print()

    if "analysis" in result and isinstance(result["analysis"], dict):
        analysis = result["analysis"]
        print(f"\n💡 Claude Code Analysis:")
        print("-" * 60)

        if "title_patterns" in analysis:
            print("Title Patterns:")
            for p in analysis["title_patterns"][:5]:
                print(f"  • {p}")

        if "success_factors" in analysis:
            print("\nSuccess Factors:")
            for f in analysis["success_factors"][:5]:
                print(f"  • {f}")

        if "action_items" in analysis:
            print("\nRecommended Actions:")
            for a in analysis["action_items"][:5]:
                print(f"  • {a}")

        if "summary" in analysis:
            print(f"\nSummary: {analysis['summary']}")

    # 保存
    filepath = analyzer.save_analysis(result, args.output)
    print(f"\n✅ Saved to: {filepath}")
