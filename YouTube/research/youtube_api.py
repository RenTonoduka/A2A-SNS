"""
YouTube Data API Client
実データ取得用のAPIクライアント
"""

import os
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


@dataclass
class VideoData:
    """動画データ"""
    video_id: str
    title: str
    channel_id: str
    channel_title: str
    view_count: int
    like_count: int
    comment_count: int
    published_at: str
    duration: str = ""
    description: str = ""
    tags: List[str] = None

    # 計算フィールド
    engagement_rate: float = 0.0

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        # エンゲージメント率計算（いいね+コメント / 再生数）
        if self.view_count > 0:
            self.engagement_rate = (self.like_count + self.comment_count) / self.view_count * 100


@dataclass
class ChannelData:
    """チャンネルデータ"""
    channel_id: str
    title: str
    description: str
    subscriber_count: int
    view_count: int
    video_count: int
    published_at: str
    thumbnail_url: str = ""

    # 計算フィールド
    avg_views_per_video: float = 0.0

    def __post_init__(self):
        if self.video_count > 0:
            self.avg_views_per_video = self.view_count / self.video_count


class YouTubeAPIClient:
    """
    YouTube Data API v3 クライアント

    実データ取得に特化
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YouTube API key required. Set YOUTUBE_API_KEY env var.")

        self.youtube = build("youtube", "v3", developerKey=self.api_key)

    def search_channels(self, query: str, max_results: int = 10) -> List[ChannelData]:
        """
        キーワードでチャンネル検索
        """
        try:
            response = self.youtube.search().list(
                q=query,
                type="channel",
                part="snippet",
                maxResults=max_results,
                relevanceLanguage="ja",
                regionCode="JP"
            ).execute()

            channel_ids = [item["snippet"]["channelId"] for item in response.get("items", [])]

            if not channel_ids:
                return []

            return self.get_channels_by_ids(channel_ids)

        except HttpError as e:
            print(f"YouTube API Error: {e}")
            return []

    def get_channels_by_ids(self, channel_ids: List[str]) -> List[ChannelData]:
        """
        チャンネルIDからチャンネル詳細取得
        """
        try:
            response = self.youtube.channels().list(
                id=",".join(channel_ids),
                part="snippet,statistics"
            ).execute()

            channels = []
            for item in response.get("items", []):
                snippet = item["snippet"]
                stats = item.get("statistics", {})

                channels.append(ChannelData(
                    channel_id=item["id"],
                    title=snippet.get("title", ""),
                    description=snippet.get("description", "")[:500],
                    subscriber_count=int(stats.get("subscriberCount", 0)),
                    view_count=int(stats.get("viewCount", 0)),
                    video_count=int(stats.get("videoCount", 0)),
                    published_at=snippet.get("publishedAt", ""),
                    thumbnail_url=snippet.get("thumbnails", {}).get("default", {}).get("url", "")
                ))

            return channels

        except HttpError as e:
            print(f"YouTube API Error: {e}")
            return []

    def get_channel_videos(
        self,
        channel_id: str,
        max_results: int = 50,
        order: str = "viewCount"  # viewCount, date, rating
    ) -> List[VideoData]:
        """
        チャンネルの動画一覧取得

        order:
        - viewCount: 再生回数順（人気動画）
        - date: 新着順
        - rating: 評価順
        """
        try:
            # チャンネルのアップロード動画を検索
            response = self.youtube.search().list(
                channelId=channel_id,
                type="video",
                part="snippet",
                maxResults=max_results,
                order=order
            ).execute()

            video_ids = [item["id"]["videoId"] for item in response.get("items", [])]

            if not video_ids:
                return []

            return self.get_videos_by_ids(video_ids)

        except HttpError as e:
            print(f"YouTube API Error: {e}")
            return []

    def get_videos_by_ids(self, video_ids: List[str]) -> List[VideoData]:
        """
        動画IDから動画詳細取得
        """
        try:
            response = self.youtube.videos().list(
                id=",".join(video_ids),
                part="snippet,statistics,contentDetails"
            ).execute()

            videos = []
            for item in response.get("items", []):
                snippet = item["snippet"]
                stats = item.get("statistics", {})
                content = item.get("contentDetails", {})

                videos.append(VideoData(
                    video_id=item["id"],
                    title=snippet.get("title", ""),
                    channel_id=snippet.get("channelId", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    view_count=int(stats.get("viewCount", 0)),
                    like_count=int(stats.get("likeCount", 0)),
                    comment_count=int(stats.get("commentCount", 0)),
                    published_at=snippet.get("publishedAt", ""),
                    duration=content.get("duration", ""),
                    description=snippet.get("description", "")[:500],
                    tags=snippet.get("tags", [])[:20]
                ))

            return videos

        except HttpError as e:
            print(f"YouTube API Error: {e}")
            return []

    def search_videos(
        self,
        query: str,
        max_results: int = 50,
        order: str = "viewCount"
    ) -> List[VideoData]:
        """
        キーワードで動画検索
        """
        try:
            response = self.youtube.search().list(
                q=query,
                type="video",
                part="snippet",
                maxResults=max_results,
                order=order,
                relevanceLanguage="ja",
                regionCode="JP"
            ).execute()

            video_ids = [item["id"]["videoId"] for item in response.get("items", [])]

            if not video_ids:
                return []

            return self.get_videos_by_ids(video_ids)

        except HttpError as e:
            print(f"YouTube API Error: {e}")
            return []

    def get_top_videos_with_channel_info(
        self,
        channel_id: str,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        チャンネルの上位動画 + チャンネル情報を取得

        Returns:
            {
                "channel": ChannelData,
                "top_videos": [VideoData],
                "metrics": {
                    "avg_views": float,
                    "views_to_subs_ratio": float,  # 再生/登録者
                    "top_video_performance": float  # 上位動画の登録者比
                }
            }
        """
        # チャンネル情報取得
        channels = self.get_channels_by_ids([channel_id])
        if not channels:
            return {}

        channel = channels[0]

        # 上位動画取得
        videos = self.get_channel_videos(channel_id, max_results=top_n, order="viewCount")

        # メトリクス計算
        if videos and channel.subscriber_count > 0:
            avg_views = sum(v.view_count for v in videos) / len(videos)
            views_to_subs = avg_views / channel.subscriber_count
            top_video_ratio = videos[0].view_count / channel.subscriber_count if videos else 0
        else:
            avg_views = 0
            views_to_subs = 0
            top_video_ratio = 0

        return {
            "channel": asdict(channel),
            "top_videos": [asdict(v) for v in videos],
            "metrics": {
                "avg_views": avg_views,
                "views_to_subs_ratio": views_to_subs,
                "top_video_performance": top_video_ratio
            }
        }


    def find_related_channels(
        self,
        channel_id: str,
        max_results: int = 10
    ) -> List[ChannelData]:
        """
        関連チャンネルを検索（チャンネルの動画タイトルからキーワード抽出して類似検索）

        YouTube APIには直接の関連チャンネル取得がないため、
        チャンネルの人気動画のキーワードで類似チャンネルを検索
        """
        try:
            # 対象チャンネルの人気動画を取得
            videos = self.get_channel_videos(channel_id, max_results=5, order="viewCount")
            if not videos:
                return []

            # タイトルからキーワード抽出
            keywords = set()
            for v in videos:
                # 簡易的なキーワード抽出（【】内、主要単語）
                import re
                brackets = re.findall(r'【(.+?)】', v.title)
                keywords.update(brackets)
                # 長い単語も追加
                words = re.findall(r'[A-Za-z]{4,}|[ぁ-んァ-ン一-龥]{2,}', v.title)
                keywords.update(words[:3])

            if not keywords:
                return []

            # キーワードで検索
            search_query = ' '.join(list(keywords)[:5])
            related = self.search_channels(search_query, max_results=max_results + 5)

            # 元のチャンネルを除外
            related = [ch for ch in related if ch.channel_id != channel_id]

            return related[:max_results]

        except HttpError as e:
            print(f"YouTube API Error: {e}")
            return []

    def get_recent_videos(
        self,
        channel_id: str,
        max_results: int = 20,
        days: int = 90  # 直近N日以内
    ) -> List[VideoData]:
        """
        チャンネルの直近N日以内の動画を取得
        """
        from datetime import datetime, timedelta

        try:
            # 日付フィルター
            after_date = (datetime.now() - timedelta(days=days)).isoformat() + "Z"

            response = self.youtube.search().list(
                channelId=channel_id,
                type="video",
                part="snippet",
                maxResults=max_results,
                order="date",
                publishedAfter=after_date
            ).execute()

            video_ids = [item["id"]["videoId"] for item in response.get("items", [])]

            if not video_ids:
                return []

            return self.get_videos_by_ids(video_ids)

        except HttpError as e:
            print(f"YouTube API Error: {e}")
            return []


def export_for_claude(data: Dict[str, Any]) -> str:
    """
    Claude Code分析用にデータを整形
    """
    return json.dumps(data, ensure_ascii=False, indent=2)


# テスト実行
if __name__ == "__main__":
    import sys

    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("❌ YOUTUBE_API_KEY not set")
        print("Set it with: export YOUTUBE_API_KEY='your-api-key'")
        sys.exit(1)

    client = YouTubeAPIClient(api_key)

    print("🔍 Testing YouTube API Client")
    print("=" * 50)

    # チャンネル検索テスト
    print("\n[1] Channel Search: 'AI 副業'")
    channels = client.search_channels("AI 副業", max_results=3)
    for ch in channels:
        print(f"  • {ch.title} ({ch.subscriber_count:,} subs)")

    if channels:
        # 上位動画取得テスト
        print(f"\n[2] Top Videos from: {channels[0].title}")
        data = client.get_top_videos_with_channel_info(channels[0].channel_id, top_n=5)

        if data:
            print(f"  Channel: {data['channel']['title']}")
            print(f"  Subscribers: {data['channel']['subscriber_count']:,}")
            print(f"  Views/Subs Ratio: {data['metrics']['views_to_subs_ratio']:.2f}")
            print(f"\n  Top Videos:")
            for v in data["top_videos"][:5]:
                ratio = v["view_count"] / data["channel"]["subscriber_count"] if data["channel"]["subscriber_count"] > 0 else 0
                print(f"    • {v['title'][:40]}...")
                print(f"      Views: {v['view_count']:,} (Ratio: {ratio:.2f}x)")

    print("\n" + "=" * 50)
    print("✅ API Client working")
