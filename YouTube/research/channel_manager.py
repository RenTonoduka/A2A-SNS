"""
Channel Manager
保存済みチャンネルの管理 + APIキャッシュ

- CSVでチャンネルリスト管理
- APIは必要な時だけ叩く（キャッシュ期間設定）
- 動画データもCSVに保存
- Claude Codeが分析・評価
"""

import os
import sys
import csv
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field

# パス設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SNS_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, SNS_DIR)

DATA_DIR = os.path.join(SCRIPT_DIR, "data")

from _shared.claude_runner import ClaudeRunner


@dataclass
class Channel:
    """チャンネル情報"""
    channel_id: str
    channel_name: str
    subscriber_count: int
    video_count: int
    saved_date: str
    last_fetched: str = ""
    notes: str = ""
    total_views: int = 0


@dataclass
class Video:
    """動画情報"""
    video_id: str
    channel_id: str
    channel_name: str
    title: str
    view_count: int
    like_count: int
    comment_count: int
    published_at: str
    fetched_at: str
    subscriber_count_at_fetch: int = 0
    performance_ratio: float = 0.0  # 再生数/登録者数
    duration: str = ""  # ISO 8601形式 (PT1M30S = 1分30秒)

    def get_duration_seconds(self) -> int:
        """動画の長さを秒数で取得"""
        if not self.duration:
            return 0
        # ISO 8601形式をパース (PT1H2M30S → 3750秒)
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', self.duration)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    def is_short(self) -> bool:
        """ショート動画かどうか（60秒以下）"""
        return 0 < self.get_duration_seconds() <= 60


class ChannelManager:
    """
    チャンネル管理クラス

    - チャンネルリストCSV管理
    - 動画データCSV管理
    - キャッシュ制御（更新間隔設定）
    """

    def __init__(
        self,
        data_dir: str = DATA_DIR,
        cache_days: int = 7,  # 7日ごとに更新
        api_key: Optional[str] = None
    ):
        self.data_dir = data_dir
        self.cache_days = cache_days
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")

        # ファイルパス
        self.channels_file = os.path.join(data_dir, "channels.csv")
        self.videos_file = os.path.join(data_dir, "videos.csv")
        self.fetch_log_file = os.path.join(data_dir, "fetch_log.csv")

        os.makedirs(data_dir, exist_ok=True)

        # APIクライアント（遅延初期化）
        self._api = None

        # Claude Runner
        self.claude = ClaudeRunner(timeout=180)

    @property
    def api(self):
        """APIクライアントの遅延初期化"""
        if self._api is None:
            if not self.api_key:
                raise ValueError("YouTube API key required")
            from youtube_api import YouTubeAPIClient
            self._api = YouTubeAPIClient(self.api_key)
        return self._api

    # ==========================================
    # チャンネル管理
    # ==========================================

    def load_channels(self) -> List[Channel]:
        """チャンネルリスト読み込み"""
        if not os.path.exists(self.channels_file):
            return []

        channels = []
        with open(self.channels_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                channels.append(Channel(
                    channel_id=row.get("channel_id", ""),
                    channel_name=row.get("channel_name", ""),
                    subscriber_count=int(row.get("subscriber_count", 0)),
                    video_count=int(row.get("video_count", 0)),
                    saved_date=row.get("saved_date", ""),
                    last_fetched=row.get("last_fetched", ""),
                    notes=row.get("notes", ""),
                    total_views=int(row.get("total_views", 0))
                ))
        return channels

    def save_channels(self, channels: List[Channel]):
        """チャンネルリスト保存"""
        with open(self.channels_file, "w", encoding="utf-8", newline="") as f:
            fieldnames = ["channel_id", "channel_name", "subscriber_count", "video_count",
                         "saved_date", "last_fetched", "total_views", "notes"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for ch in channels:
                writer.writerow(asdict(ch))

    def add_channel(self, channel_name: str, notes: str = "") -> Optional[Channel]:
        """チャンネルを追加（名前で検索してIDを取得）"""
        print(f"🔍 Searching for: {channel_name}")

        results = self.api.search_channels(channel_name, max_results=1)
        if not results:
            print(f"❌ Channel not found: {channel_name}")
            return None

        ch_data = results[0]
        channel = Channel(
            channel_id=ch_data.channel_id,
            channel_name=ch_data.title,
            subscriber_count=ch_data.subscriber_count,
            video_count=ch_data.video_count,
            saved_date=datetime.now().strftime("%Y-%m-%d"),
            last_fetched=datetime.now().strftime("%Y-%m-%d"),
            total_views=ch_data.view_count,
            notes=notes
        )

        # 既存リストに追加
        channels = self.load_channels()
        # 重複チェック
        if any(c.channel_id == channel.channel_id for c in channels):
            print(f"⚠️ Channel already exists: {channel_name}")
            return None

        channels.append(channel)
        self.save_channels(channels)

        self._log_fetch("add_channel", channel.channel_id, channel.channel_name)

        print(f"✅ Added: {channel.channel_name} ({channel.subscriber_count:,} subs)")
        return channel

    def resolve_channel_ids(self) -> int:
        """
        channel_idが空のチャンネルを検索してIDを取得
        """
        channels = self.load_channels()
        resolved = 0

        for ch in channels:
            if not ch.channel_id:
                print(f"🔍 Resolving: {ch.channel_name}")
                results = self.api.search_channels(ch.channel_name, max_results=1)

                if results:
                    ch.channel_id = results[0].channel_id
                    ch.subscriber_count = results[0].subscriber_count
                    ch.video_count = results[0].video_count
                    ch.total_views = results[0].view_count
                    ch.last_fetched = datetime.now().strftime("%Y-%m-%d")
                    resolved += 1
                    print(f"  ✅ Found: {ch.channel_id}")
                    self._log_fetch("resolve_id", ch.channel_id, ch.channel_name)
                else:
                    print(f"  ❌ Not found")

        self.save_channels(channels)
        return resolved

    def needs_update(self, channel: Channel) -> bool:
        """更新が必要か判定"""
        if not channel.last_fetched:
            return True

        try:
            last = datetime.strptime(channel.last_fetched, "%Y-%m-%d")
            return datetime.now() - last > timedelta(days=self.cache_days)
        except:
            return True

    def get_channels_needing_update(self) -> List[Channel]:
        """更新が必要なチャンネル一覧"""
        return [ch for ch in self.load_channels() if self.needs_update(ch)]

    # ==========================================
    # 動画データ管理
    # ==========================================

    def load_videos(self, channel_id: Optional[str] = None, exclude_shorts: bool = False) -> List[Video]:
        """動画データ読み込み

        Args:
            channel_id: 特定チャンネルのみ取得
            exclude_shorts: ショート動画（60秒以下）を除外
        """
        if not os.path.exists(self.videos_file):
            return []

        videos = []
        with open(self.videos_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if channel_id and row.get("channel_id") != channel_id:
                    continue
                video = Video(
                    video_id=row.get("video_id", ""),
                    channel_id=row.get("channel_id", ""),
                    channel_name=row.get("channel_name", ""),
                    title=row.get("title", ""),
                    view_count=int(row.get("view_count", 0)),
                    like_count=int(row.get("like_count", 0)),
                    comment_count=int(row.get("comment_count", 0)),
                    published_at=row.get("published_at", ""),
                    fetched_at=row.get("fetched_at", ""),
                    subscriber_count_at_fetch=int(row.get("subscriber_count_at_fetch", 0)),
                    performance_ratio=float(row.get("performance_ratio", 0)),
                    duration=row.get("duration", "")
                )
                # ショート除外
                if exclude_shorts and video.is_short():
                    continue
                videos.append(video)
        return videos

    def save_videos(self, videos: List[Video], append: bool = False):
        """動画データ保存"""
        mode = "a" if append else "w"
        file_exists = os.path.exists(self.videos_file) and append

        with open(self.videos_file, mode, encoding="utf-8", newline="") as f:
            fieldnames = ["video_id", "channel_id", "channel_name", "title",
                         "view_count", "like_count", "comment_count",
                         "published_at", "fetched_at", "subscriber_count_at_fetch",
                         "performance_ratio", "duration"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            for v in videos:
                data = asdict(v)
                # メソッドは除外（asdictには含まれないが念のため）
                data.pop('get_duration_seconds', None)
                data.pop('is_short', None)
                writer.writerow(data)

    def fetch_channel_videos(
        self,
        channel: Channel,
        top_n: int = 10,
        force: bool = False
    ) -> List[Video]:
        """
        チャンネルの上位動画を取得

        Args:
            channel: 対象チャンネル
            top_n: 取得する動画数
            force: キャッシュを無視して強制取得
        """
        if not channel.channel_id:
            print(f"⚠️ No channel_id for: {channel.channel_name}")
            return []

        if not force and not self.needs_update(channel):
            print(f"📦 Using cached data for: {channel.channel_name}")
            return self.load_videos(channel.channel_id)

        print(f"📡 Fetching videos for: {channel.channel_name}")

        raw_videos = self.api.get_channel_videos(
            channel.channel_id,
            max_results=top_n,
            order="viewCount"
        )

        if not raw_videos:
            return []

        videos = []
        fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for v in raw_videos:
            ratio = v.view_count / channel.subscriber_count if channel.subscriber_count > 0 else 0
            videos.append(Video(
                video_id=v.video_id,
                channel_id=channel.channel_id,
                channel_name=channel.channel_name,
                title=v.title,
                view_count=v.view_count,
                like_count=v.like_count,
                comment_count=v.comment_count,
                published_at=v.published_at,
                fetched_at=fetched_at,
                subscriber_count_at_fetch=channel.subscriber_count,
                performance_ratio=round(ratio, 2),
                duration=v.duration  # ISO 8601形式 (PT1M30S)
            ))

        # 既存データから該当チャンネル以外を残す
        existing = [v for v in self.load_videos() if v.channel_id != channel.channel_id]
        self.save_videos(existing + videos)

        # チャンネルの最終取得日を更新
        channels = self.load_channels()
        for ch in channels:
            if ch.channel_id == channel.channel_id:
                ch.last_fetched = datetime.now().strftime("%Y-%m-%d")
                break
        self.save_channels(channels)

        self._log_fetch("fetch_videos", channel.channel_id, channel.channel_name, len(videos))

        return videos

    def fetch_all_channels(self, top_n: int = 10, force: bool = False) -> Dict[str, List[Video]]:
        """全チャンネルの動画を取得"""
        channels = self.load_channels()
        result = {}

        for ch in channels:
            if not ch.channel_id:
                continue
            videos = self.fetch_channel_videos(ch, top_n, force)
            if videos:
                result[ch.channel_name] = videos

        return result

    # ==========================================
    # 優秀動画の発見
    # ==========================================

    def find_outstanding_videos(
        self,
        threshold: float = 2.0,
        min_views: int = 1000,
        exclude_shorts: bool = True  # デフォルトでショート除外
    ) -> List[Video]:
        """
        優秀な動画を発見（ショート動画はデフォルトで除外）

        Args:
            threshold: PRしきい値（デフォルト2.0 = 登録者の2倍以上）
            min_views: 最小再生数
            exclude_shorts: ショート動画（60秒以下）を除外

        基準: 登録者数に対して再生数が異常に高い
        threshold=2.0 → 登録者の2倍以上の再生数
        """
        all_videos = self.load_videos(exclude_shorts=exclude_shorts)

        outstanding = [
            v for v in all_videos
            if v.performance_ratio >= threshold and v.view_count >= min_views
        ]

        # パフォーマンス比で降順ソート
        outstanding.sort(key=lambda x: x.performance_ratio, reverse=True)

        return outstanding

    def analyze_outstanding_videos(self, threshold: float = 2.0) -> Dict[str, Any]:
        """
        優秀動画をClaude Codeに分析させる

        スクリプト: データ抽出
        Claude Code: 分析・評価・判断
        """
        outstanding = self.find_outstanding_videos(threshold)

        if not outstanding:
            return {"error": "No outstanding videos found"}

        # データ整形
        data = {
            "threshold": threshold,
            "total_videos": len(self.load_videos()),
            "outstanding_count": len(outstanding),
            "videos": [
                {
                    "title": v.title,
                    "channel": v.channel_name,
                    "views": v.view_count,
                    "subscribers": v.subscriber_count_at_fetch,
                    "ratio": v.performance_ratio,
                    "likes": v.like_count,
                    "comments": v.comment_count,
                    "published": v.published_at[:10] if v.published_at else ""
                }
                for v in outstanding[:30]  # 上位30件
            ]
        }

        # Claude Codeに分析を依頼
        prompt = f"""あなたはYouTubeマーケティングの専門アナリストです。

以下は「登録者数に対して再生数が異常に高い」優秀な動画のデータです。
（performance_ratio = 再生数 / 登録者数）

## データ
```json
{json.dumps(data, ensure_ascii=False, indent=2)}
```

## 分析タスク

### 1. タイトルパターン分析
優秀動画のタイトルに共通するパターンを特定してください：
- 数字の使い方
- フックワード（「衝撃」「完全」「最新」等）
- 構造パターン（【】、｜の使い方）

### 2. 成功要因分析
なぜこれらの動画は登録者数以上のリーチを獲得できたのか？
- コンテンツ要因
- タイミング要因
- アルゴリズム要因（推測）

### 3. 再現可能なテンプレート
このデータから導き出せる、実行可能なタイトルテンプレートを5つ提示してください。

### 4. 狙い目テーマ
どのチャンネルのどのテーマが特に成功しているか？

## 出力形式（JSON）
{{
    "title_patterns": {{
        "number_usage": ["パターン1", "パターン2"],
        "hook_words": ["フック1", "フック2"],
        "structure_patterns": ["構造1", "構造2"]
    }},
    "success_factors": ["要因1", "要因2", "要因3"],
    "title_templates": [
        "【数字】〇〇が△△する方法",
        "テンプレート2",
        ...
    ],
    "hot_themes": [
        {{"theme": "テーマ", "channel": "チャンネル", "reason": "理由"}}
    ],
    "actionable_insights": ["インサイト1", "インサイト2"],
    "summary": "2-3文の総括"
}}

JSONのみを出力してください。"""

        result = self.claude.run(prompt)

        if not result["success"]:
            return {"error": result["error"], "data": data}

        try:
            analysis = json.loads(self._extract_json(result["output"]))
            return {
                "outstanding_videos": data["videos"],
                "analysis": analysis,
                "analyzed_at": datetime.now().isoformat()
            }
        except json.JSONDecodeError:
            return {"raw_analysis": result["output"], "data": data}

    # ==========================================
    # ユーティリティ
    # ==========================================

    def _log_fetch(self, action: str, channel_id: str, channel_name: str, count: int = 0):
        """API呼び出しログ"""
        file_exists = os.path.exists(self.fetch_log_file)

        with open(self.fetch_log_file, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "action", "channel_id", "channel_name", "count"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                action,
                channel_id,
                channel_name,
                count
            ])

    def _extract_json(self, text: str) -> str:
        """JSONを抽出"""
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

    def get_stats(self) -> Dict[str, Any]:
        """統計情報"""
        channels = self.load_channels()
        videos = self.load_videos()

        return {
            "total_channels": len(channels),
            "channels_with_id": len([c for c in channels if c.channel_id]),
            "channels_needing_update": len(self.get_channels_needing_update()),
            "total_videos": len(videos),
            "outstanding_videos_2x": len(self.find_outstanding_videos(2.0)),
            "outstanding_videos_5x": len(self.find_outstanding_videos(5.0)),
            "cache_days": self.cache_days
        }

    # ==========================================
    # 自動探索（バズ動画がなければ関連チャンネルを探索）
    # ==========================================

    def auto_discover_buzz(
        self,
        threshold: float = 5.0,
        min_views: int = 10000,
        days: int = 90,
        max_new_channels: int = 10
    ) -> Dict[str, Any]:
        """
        バズ動画を自動探索

        1. 登録済みチャンネルからバズ動画を検索
        2. 見つからなければ、関連チャンネルを探索
        3. 直近N日以内のバズ動画のみ対象

        Args:
            threshold: PRしきい値（デフォルト5.0）
            min_views: 最小再生数
            days: 直近N日以内（デフォルト90日=3ヶ月）
            max_new_channels: 探索する新規チャンネル数

        Returns:
            {
                "buzz_videos": [...],
                "new_channels_discovered": [...],
                "source": "registered" | "related"
            }
        """
        from datetime import datetime, timedelta

        result = {
            "buzz_videos": [],
            "new_channels_discovered": [],
            "source": "registered",
            "searched_at": datetime.now().isoformat()
        }

        cutoff_date = datetime.now() - timedelta(days=days)

        # Step 1: 登録済みチャンネルからバズ動画を探す
        print(f"🔍 Step 1: 登録チャンネルから直近{days}日のバズ動画を検索...")
        outstanding = self.find_outstanding_videos(
            threshold=threshold,
            min_views=min_views,
            exclude_shorts=True
        )

        # 直近N日以内にフィルタ
        recent_buzz = []
        for v in outstanding:
            try:
                pub_date = datetime.fromisoformat(v.published_at.replace('Z', '+00:00'))
                if pub_date.replace(tzinfo=None) >= cutoff_date:
                    recent_buzz.append(v)
            except:
                pass

        if recent_buzz:
            print(f"  ✅ {len(recent_buzz)}件のバズ動画を発見！")
            result["buzz_videos"] = [
                {
                    "video_id": v.video_id,
                    "title": v.title,
                    "channel_name": v.channel_name,
                    "view_count": v.view_count,
                    "performance_ratio": v.performance_ratio,
                    "published_at": v.published_at
                }
                for v in recent_buzz[:20]
            ]
            return result

        # Step 2: バズ動画がなければ関連チャンネルを探索
        print(f"  ⚠️ 登録チャンネルにバズ動画なし")
        print(f"🔍 Step 2: 関連チャンネルを探索...")

        result["source"] = "related"
        channels = self.load_channels()
        discovered_channels = []
        all_buzz = []

        for ch in channels[:5]:  # 上位5チャンネルから関連を探索
            if not ch.channel_id:
                continue

            print(f"  📡 {ch.channel_name} の関連チャンネルを検索...")
            related = self.api.find_related_channels(ch.channel_id, max_results=5)

            for rel_ch in related:
                # 既に登録済みなら飛ばす
                if any(c.channel_id == rel_ch.channel_id for c in channels):
                    continue
                if any(d["channel_id"] == rel_ch.channel_id for d in discovered_channels):
                    continue

                # 直近N日の動画を取得
                recent_videos = self.api.get_recent_videos(
                    rel_ch.channel_id,
                    max_results=20,
                    days=days
                )

                # バズ動画を検出
                for v in recent_videos:
                    if rel_ch.subscriber_count > 0:
                        pr = v.view_count / rel_ch.subscriber_count
                        # ショート除外（60秒以下）
                        duration_match = None
                        if v.duration:
                            import re
                            duration_match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', v.duration)
                        if duration_match:
                            hours = int(duration_match.group(1) or 0)
                            minutes = int(duration_match.group(2) or 0)
                            seconds = int(duration_match.group(3) or 0)
                            total_seconds = hours * 3600 + minutes * 60 + seconds
                            if 0 < total_seconds <= 60:
                                continue  # ショートはスキップ

                        if pr >= threshold and v.view_count >= min_views:
                            all_buzz.append({
                                "video_id": v.video_id,
                                "title": v.title,
                                "channel_id": rel_ch.channel_id,
                                "channel_name": rel_ch.title,
                                "view_count": v.view_count,
                                "subscriber_count": rel_ch.subscriber_count,
                                "performance_ratio": round(pr, 2),
                                "published_at": v.published_at
                            })

                            # この新チャンネルを記録
                            if not any(d["channel_id"] == rel_ch.channel_id for d in discovered_channels):
                                discovered_channels.append({
                                    "channel_id": rel_ch.channel_id,
                                    "channel_name": rel_ch.title,
                                    "subscriber_count": rel_ch.subscriber_count,
                                    "video_count": rel_ch.video_count
                                })

                if len(discovered_channels) >= max_new_channels:
                    break
            if len(discovered_channels) >= max_new_channels:
                break

        # PR順にソート
        all_buzz.sort(key=lambda x: x["performance_ratio"], reverse=True)

        result["buzz_videos"] = all_buzz[:20]
        result["new_channels_discovered"] = discovered_channels

        if all_buzz:
            print(f"  ✅ 関連チャンネルから{len(all_buzz)}件のバズ動画を発見！")
            print(f"  📌 新規チャンネル{len(discovered_channels)}件を発見")
        else:
            print(f"  ❌ バズ動画が見つかりませんでした")

        return result

    def add_discovered_channels(self, discovered: List[Dict]) -> int:
        """
        発見したチャンネルをchannels.csvに追加

        Args:
            discovered: auto_discover_buzz()で返されたnew_channels_discovered

        Returns:
            追加した件数
        """
        channels = self.load_channels()
        added = 0

        for d in discovered:
            # 重複チェック
            if any(c.channel_id == d["channel_id"] for c in channels):
                continue

            channels.append(Channel(
                channel_id=d["channel_id"],
                channel_name=d["channel_name"],
                subscriber_count=d["subscriber_count"],
                video_count=d["video_count"],
                saved_date=datetime.now().strftime("%Y-%m-%d"),
                last_fetched=datetime.now().strftime("%Y-%m-%d"),
                notes="auto-discovered"
            ))
            added += 1
            print(f"  ✅ 追加: {d['channel_name']} ({d['subscriber_count']:,} subs)")

        if added > 0:
            self.save_channels(channels)

        return added

    def print_status(self):
        """ステータス表示"""
        stats = self.get_stats()
        print("\n📊 Channel Manager Status")
        print("=" * 50)
        print(f"Total Channels: {stats['total_channels']}")
        print(f"  - With ID: {stats['channels_with_id']}")
        print(f"  - Needs Update: {stats['channels_needing_update']}")
        print(f"Total Videos: {stats['total_videos']}")
        print(f"Outstanding Videos:")
        print(f"  - 2x+ ratio: {stats['outstanding_videos_2x']}")
        print(f"  - 5x+ ratio: {stats['outstanding_videos_5x']}")
        print(f"Cache Period: {stats['cache_days']} days")
        print("=" * 50)


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Channel Manager")
    parser.add_argument("command", choices=["status", "resolve", "fetch", "outstanding", "analyze", "add", "discover"])
    parser.add_argument("--channel", "-c", help="Channel name (for add command)")
    parser.add_argument("--force", "-f", action="store_true", help="Force fetch (ignore cache)")
    parser.add_argument("--threshold", "-t", type=float, default=2.0, help="Outstanding threshold")
    parser.add_argument("--top", "-n", type=int, default=10, help="Videos per channel")
    args = parser.parse_args()

    manager = ChannelManager()

    if args.command == "status":
        manager.print_status()

    elif args.command == "resolve":
        print("🔍 Resolving channel IDs...")
        count = manager.resolve_channel_ids()
        print(f"✅ Resolved {count} channels")

    elif args.command == "fetch":
        print(f"📡 Fetching videos (top {args.top} per channel)...")
        result = manager.fetch_all_channels(top_n=args.top, force=args.force)
        print(f"✅ Fetched from {len(result)} channels")

    elif args.command == "outstanding":
        print(f"⭐ Finding outstanding videos (threshold: {args.threshold}x)...")
        videos = manager.find_outstanding_videos(args.threshold)
        print(f"\nFound {len(videos)} outstanding videos:\n")
        for i, v in enumerate(videos[:20], 1):
            print(f"{i:2}. {v.title[:50]}...")
            print(f"    Channel: {v.channel_name}")
            print(f"    Views: {v.view_count:,} | Subs: {v.subscriber_count_at_fetch:,} | Ratio: {v.performance_ratio}x")
            print()

    elif args.command == "analyze":
        print(f"🔬 Analyzing outstanding videos (threshold: {args.threshold}x)...")
        result = manager.analyze_outstanding_videos(args.threshold)

        if "error" in result:
            print(f"❌ Error: {result['error']}")
        elif "analysis" in result:
            analysis = result["analysis"]
            print("\n💡 Analysis Results")
            print("-" * 50)

            if "title_templates" in analysis:
                print("\nTitle Templates:")
                for t in analysis["title_templates"][:5]:
                    print(f"  • {t}")

            if "success_factors" in analysis:
                print("\nSuccess Factors:")
                for f in analysis["success_factors"][:5]:
                    print(f"  • {f}")

            if "actionable_insights" in analysis:
                print("\nActionable Insights:")
                for a in analysis["actionable_insights"][:5]:
                    print(f"  • {a}")

            if "summary" in analysis:
                print(f"\nSummary: {analysis['summary']}")

            # 結果を保存
            output_file = os.path.join(DATA_DIR, f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n✅ Saved to: {output_file}")

    elif args.command == "add":
        if not args.channel:
            print("❌ Please specify channel name with --channel")
        else:
            manager.add_channel(args.channel)

    elif args.command == "discover":
        print(f"🚀 Auto-discovering buzz videos (threshold: {args.threshold}x, last 90 days)...")
        result = manager.auto_discover_buzz(
            threshold=args.threshold,
            min_views=10000,
            days=90
        )

        if result["buzz_videos"]:
            print(f"\n🔥 Found {len(result['buzz_videos'])} buzz videos:")
            for i, v in enumerate(result["buzz_videos"][:10], 1):
                print(f"\n{i:2}. {v['title'][:50]}...")
                print(f"    Channel: {v['channel_name']}")
                print(f"    Views: {v['view_count']:,} | PR: {v['performance_ratio']}x")

            # 新規チャンネルがあれば追加提案
            if result["new_channels_discovered"]:
                print(f"\n📌 New channels discovered: {len(result['new_channels_discovered'])}")
                for ch in result["new_channels_discovered"]:
                    print(f"  • {ch['channel_name']} ({ch['subscriber_count']:,} subs)")

                # 追加するか確認
                add = input("\n追加しますか？ (y/n): ").strip().lower()
                if add == "y":
                    added = manager.add_discovered_channels(result["new_channels_discovered"])
                    print(f"✅ {added}件のチャンネルを追加しました")

            # メール通知
            if result["buzz_videos"] and args.threshold >= 5.0:
                try:
                    sys.path.insert(0, os.path.join(SNS_DIR, "_shared"))
                    from google_notifier import notify_buzz_videos
                    notify_buzz_videos(result["buzz_videos"], args.threshold)
                    print("📧 メール通知を送信しました")
                except Exception as e:
                    print(f"⚠️ メール通知エラー: {e}")

            # 台本生成パイプライン起動
            print("\n" + "=" * 50)
            print("📝 台本生成パイプラインを起動します...")
            print("=" * 50)

            try:
                sys.path.insert(0, os.path.join(SNS_DIR, "_shared"))
                from buzz_to_script_pipeline import BuzzToScriptPipeline

                pipeline = BuzzToScriptPipeline()
                pipeline_result = pipeline.process_buzz_videos(result["buzz_videos"])

                print("\n📋 トランスクリプト取得指示:")
                print("-" * 40)
                print(pipeline_result["transcript_instructions"])

                # 結果をファイルに保存
                output_file = os.path.join(DATA_DIR, f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "buzz_videos": result["buzz_videos"],
                        "pipeline": pipeline_result,
                        "generated_at": datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)
                print(f"\n✅ パイプライン情報を保存: {output_file}")
                print("\n💡 次のステップ: MCPでトランスクリプトを取得後、Script Writer Agent (port 8113) に送信")

            except Exception as e:
                print(f"⚠️ パイプラインエラー: {e}")
        else:
            print("❌ バズ動画が見つかりませんでした")
