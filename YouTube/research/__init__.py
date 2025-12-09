"""
YouTube Research Agent
TubeAIのコア機能を抽出したリサーチエージェント

構成:
- agent.py: Claude Codeベースのリサーチ（APIなし、想像ベース）
- youtube_api.py: YouTube Data API クライアント（実データ取得）
- analyzer.py: 実データ + Claude Code分析（推奨）
"""

from .agent import (
    YouTubeResearchAgent,
    ResearchResult,
    KeywordData,
    ChannelData
)

from .youtube_api import (
    YouTubeAPIClient,
    VideoData,
    ChannelData as APIChannelData
)

from .analyzer import (
    YouTubeAnalyzer,
    VideoAnalysis,
    CompetitorAnalysis
)

__all__ = [
    # Agent (Claude Code only)
    "YouTubeResearchAgent",
    "ResearchResult",
    "KeywordData",
    "ChannelData",

    # API Client
    "YouTubeAPIClient",
    "VideoData",
    "APIChannelData",

    # Analyzer (API + Claude Code)
    "YouTubeAnalyzer",
    "VideoAnalysis",
    "CompetitorAnalysis"
]
