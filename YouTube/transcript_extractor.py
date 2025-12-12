"""
YouTube Transcript Extractor - バズ動画からトランスクリプトを抽出
youtube-transcript-api を使用して日本語字幕を取得
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
    )
    # RequestBlocked may not exist in all versions
    try:
        from youtube_transcript_api._errors import RequestBlocked
    except ImportError:
        RequestBlocked = Exception

    TRANSCRIPT_API_AVAILABLE = True
    # v1.2+ はインスタンスメソッドを使用
    _api_instance = YouTubeTranscriptApi()
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False
    _api_instance = None
    TranscriptsDisabled = Exception
    NoTranscriptFound = Exception
    VideoUnavailable = Exception
    RequestBlocked = Exception
    print("⚠️ youtube-transcript-api not installed. Run: pip install youtube-transcript-api")

SCRIPT_DIR = Path(__file__).parent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeTranscriptExtractor:
    """YouTubeトランスクリプト抽出クラス"""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or SCRIPT_DIR / "data" / "transcripts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # キャッシュ用
        self.cache_file = self.output_dir / "transcript_cache.json"
        self._cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """キャッシュを読み込み"""
        if self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text())
            except:
                pass
        return {}

    def _save_cache(self):
        """キャッシュを保存"""
        self.cache_file.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2))

    def extract_video_id(self, url_or_id: str) -> str:
        """URLまたはIDからvideo_idを抽出"""
        # 既にIDの場合
        if len(url_or_id) == 11 and not url_or_id.startswith("http"):
            return url_or_id

        # URLパターン
        patterns = [
            r'(?:v=|\/videos\/|embed\/|youtu\.be\/|\/v\/|\/e\/|watch\?v%3D|watch\?feature=player_embedded&v=|%2Fvideos%2F|embed%\u200C\u200B2F|youtu\.be%2F|%2Fv%2F)([^#\&\?\n]*)',
            r'([a-zA-Z0-9_-]{11})'
        ]

        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)

        return url_or_id

    def get_transcript(
        self,
        video_id: str,
        languages: List[str] = ['ja', 'en'],
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        トランスクリプトを取得

        Args:
            video_id: YouTube動画ID
            languages: 優先言語リスト（デフォルト: 日本語 → 英語）
            use_cache: キャッシュを使用するか

        Returns:
            {
                "video_id": str,
                "language": str,
                "transcript": [{"text": str, "start": float, "duration": float}, ...],
                "full_text": str,
                "word_count": int,
                "duration_seconds": float,
                "fetched_at": str
            }
        """
        if not TRANSCRIPT_API_AVAILABLE:
            return {"error": "youtube-transcript-api not installed"}

        video_id = self.extract_video_id(video_id)

        # キャッシュチェック
        if use_cache and video_id in self._cache:
            logger.info(f"📦 Cache hit: {video_id}")
            return self._cache[video_id]

        try:
            # v1.2+ API: インスタンスメソッドを使用
            # まずlistで利用可能な言語を確認
            transcript_list = _api_instance.list(video_id)

            used_language = None
            transcript_data = None

            # 指定された言語で取得を試みる
            for lang in languages:
                try:
                    # 手動字幕を優先
                    transcript = transcript_list.find_manually_created_transcript([lang])
                    transcript_data = list(transcript.fetch())
                    used_language = lang
                    logger.info(f"✅ Found manual transcript ({lang}): {video_id}")
                    break
                except NoTranscriptFound:
                    pass

                try:
                    # 自動生成字幕にフォールバック
                    transcript = transcript_list.find_generated_transcript([lang])
                    transcript_data = list(transcript.fetch())
                    used_language = f"{lang} (auto)"
                    logger.info(f"✅ Found auto transcript ({lang}): {video_id}")
                    break
                except NoTranscriptFound:
                    continue

            if transcript_data is None:
                logger.warning(f"❌ No transcript found: {video_id}")
                return {"error": "No transcript available", "video_id": video_id}

            # フルテキストを生成 (v1.2ではsnippetオブジェクト)
            full_text = " ".join([snippet.text for snippet in transcript_data])

            # 総再生時間を計算
            if transcript_data:
                last_snippet = transcript_data[-1]
                duration = last_snippet.start + getattr(last_snippet, 'duration', 0)
            else:
                duration = 0

            result = {
                "video_id": video_id,
                "language": used_language,
                "transcript": [{"text": s.text, "start": s.start, "duration": getattr(s, 'duration', 0)} for s in transcript_data],
                "full_text": full_text,
                "word_count": len(full_text),
                "duration_seconds": round(duration, 2),
                "fetched_at": datetime.now().isoformat()
            }

            # キャッシュに保存
            self._cache[video_id] = result
            self._save_cache()

            return result

        except TranscriptsDisabled:
            logger.warning(f"❌ Transcripts disabled: {video_id}")
            return {"error": "Transcripts disabled", "video_id": video_id}
        except VideoUnavailable:
            logger.warning(f"❌ Video unavailable: {video_id}")
            return {"error": "Video unavailable", "video_id": video_id}
        except RequestBlocked:
            logger.warning(f"❌ Request blocked (IP blocked by YouTube): {video_id}")
            return {"error": "Request blocked - YouTube is blocking this IP (common for cloud providers)", "video_id": video_id}
        except Exception as e:
            logger.error(f"❌ Error fetching transcript: {video_id} - {e}")
            return {"error": str(e), "video_id": video_id}

    def get_transcripts_batch(
        self,
        video_ids: List[str],
        languages: List[str] = ['ja', 'en']
    ) -> Dict[str, Any]:
        """
        複数動画のトランスクリプトを一括取得

        Returns:
            {
                "success": [結果リスト],
                "failed": [失敗リスト],
                "summary": {統計情報}
            }
        """
        success = []
        failed = []

        for i, video_id in enumerate(video_ids, 1):
            logger.info(f"📥 [{i}/{len(video_ids)}] Fetching: {video_id}")
            result = self.get_transcript(video_id, languages)

            if result and "error" not in result:
                success.append(result)
            else:
                failed.append(result or {"video_id": video_id, "error": "Unknown error"})

        return {
            "success": success,
            "failed": failed,
            "summary": {
                "total": len(video_ids),
                "success_count": len(success),
                "failed_count": len(failed),
                "total_words": sum(r.get("word_count", 0) for r in success)
            }
        }

    def extract_from_buzz_videos(
        self,
        buzz_file: Optional[Path] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        バズ動画データからトランスクリプトを抽出

        Args:
            buzz_file: バズ動画JSONファイル（デフォルト: sheets_cache/バズ動画.json）
            limit: 取得する動画数の上限
        """
        # バズ動画データを探す
        if buzz_file is None:
            possible_paths = [
                SCRIPT_DIR / "data" / "sheets_cache" / "バズ動画.json",
                SCRIPT_DIR / "research" / "data" / "analysis_20251209_025306.json",
            ]
            for path in possible_paths:
                if path.exists():
                    buzz_file = path
                    break

        if buzz_file is None or not buzz_file.exists():
            return {"error": "バズ動画データが見つかりません"}

        # データを読み込み
        data = json.loads(buzz_file.read_text())

        # 動画IDを抽出
        video_ids = []

        # analysis_*.json 形式
        if "outstanding_videos" in data:
            for video in data["outstanding_videos"][:limit]:
                # titleからvideo_idを推測するか、URLがあれば使用
                # この形式にはvideo_idがないので、別のソースが必要
                pass

        # sheets_cache形式
        if isinstance(data, list):
            for record in data[:limit]:
                if "video_id" in record:
                    video_ids.append(record["video_id"])
                elif "url" in record:
                    video_ids.append(self.extract_video_id(record["url"]))

        if not video_ids:
            return {"error": "動画IDが見つかりません", "data_format": type(data).__name__}

        logger.info(f"🎬 Extracting transcripts from {len(video_ids)} buzz videos...")
        return self.get_transcripts_batch(video_ids)

    def save_transcripts_for_reference(
        self,
        transcripts: List[Dict[str, Any]],
        output_file: Optional[Path] = None
    ) -> Path:
        """
        台本生成の参考用にトランスクリプトを保存

        Args:
            transcripts: トランスクリプトリスト
            output_file: 出力ファイルパス

        Returns:
            保存したファイルパス
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"reference_transcripts_{timestamp}.md"

        lines = [
            "# バズ動画トランスクリプト - 台本作成参考資料",
            f"\n生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            f"収録動画数: {len(transcripts)}本\n",
            "---\n"
        ]

        for i, t in enumerate(transcripts, 1):
            if "error" in t:
                continue

            lines.append(f"## {i}. 動画ID: {t.get('video_id', 'unknown')}\n")
            lines.append(f"- 言語: {t.get('language', 'unknown')}")
            lines.append(f"- 文字数: {t.get('word_count', 0):,}文字")
            lines.append(f"- 動画時間: {t.get('duration_seconds', 0):.0f}秒")
            lines.append(f"\n### トランスクリプト全文\n")
            lines.append(f"```\n{t.get('full_text', '')}\n```\n")
            lines.append("---\n")

        output_file.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"📝 Saved reference transcripts: {output_file}")
        return output_file


# ==========================================
# シングルトンインスタンス
# ==========================================

_extractor_instance: Optional[YouTubeTranscriptExtractor] = None


def get_transcript_extractor() -> YouTubeTranscriptExtractor:
    """シングルトンインスタンスを取得"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = YouTubeTranscriptExtractor()
    return _extractor_instance


# ==========================================
# CLI
# ==========================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Transcript Extractor")
    parser.add_argument("command", choices=["get", "batch", "buzz", "test"],
                       help="get: 単一動画, batch: 複数動画, buzz: バズ動画, test: テスト")
    parser.add_argument("--video-id", "-v", help="動画ID or URL")
    parser.add_argument("--video-ids", "-vs", nargs="+", help="複数の動画ID")
    parser.add_argument("--limit", type=int, default=10, help="取得上限")
    parser.add_argument("--output", "-o", help="出力ファイルパス")

    args = parser.parse_args()

    extractor = YouTubeTranscriptExtractor()

    if args.command == "test":
        # テスト用: 有名な日本語動画
        test_ids = [
            "dQw4w9WgXcQ",  # Rick Astley (英語)
        ]
        print("🧪 Testing transcript extraction...")
        for vid in test_ids:
            result = extractor.get_transcript(vid)
            if "error" in result:
                print(f"  ❌ {vid}: {result['error']}")
            else:
                print(f"  ✅ {vid}: {result['word_count']} chars ({result['language']})")

    elif args.command == "get":
        if not args.video_id:
            print("❌ --video-id required")
            return

        result = extractor.get_transcript(args.video_id)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Transcript fetched:")
            print(f"   Language: {result['language']}")
            print(f"   Words: {result['word_count']:,}")
            print(f"   Duration: {result['duration_seconds']:.0f}s")
            print(f"\n📜 Preview (first 500 chars):")
            print(result['full_text'][:500])

    elif args.command == "batch":
        if not args.video_ids:
            print("❌ --video-ids required")
            return

        results = extractor.get_transcripts_batch(args.video_ids)
        print(f"\n📊 Batch Results:")
        print(f"   Success: {results['summary']['success_count']}")
        print(f"   Failed: {results['summary']['failed_count']}")
        print(f"   Total words: {results['summary']['total_words']:,}")

        if args.output:
            output_path = extractor.save_transcripts_for_reference(
                results['success'],
                Path(args.output)
            )
            print(f"\n📝 Saved to: {output_path}")

    elif args.command == "buzz":
        results = extractor.extract_from_buzz_videos(limit=args.limit)

        if "error" in results:
            print(f"❌ Error: {results['error']}")
            return

        print(f"\n📊 Buzz Video Transcripts:")
        print(f"   Success: {results['summary']['success_count']}")
        print(f"   Failed: {results['summary']['failed_count']}")
        print(f"   Total words: {results['summary']['total_words']:,}")

        # 参考資料として保存
        output_path = extractor.save_transcripts_for_reference(results['success'])
        print(f"\n📝 Reference file: {output_path}")


if __name__ == "__main__":
    main()
