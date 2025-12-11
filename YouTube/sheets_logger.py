"""
YouTube Sheets Logger - バズ動画・チャンネルデータをスプレッドシートに記録
MCP経由でGoogle Sheetsに書き込み
"""

import json
import os
import csv
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeSheetsLogger:
    """
    YouTube データを Google Sheets に記録

    使用方法:
    1. MCP経由: Claude Code CLIのMCPツールを使用
    2. ローカルキャッシュ: MCP未使用時はJSONに保存
    """

    def __init__(self, spreadsheet_id: Optional[str] = None):
        self.spreadsheet_id = spreadsheet_id or os.getenv("YOUTUBE_SHEETS_ID", "")
        self.cache_dir = SCRIPT_DIR / "data" / "sheets_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # シート名
        self.buzz_sheet = "バズ動画"
        self.videos_sheet = "動画一覧"
        self.channels_sheet = "チャンネル一覧"

    def _get_cache_file(self, sheet_name: str) -> Path:
        """キャッシュファイルパスを取得"""
        safe_name = sheet_name.replace("/", "_").replace(" ", "_")
        return self.cache_dir / f"{safe_name}.json"

    def _load_cache(self, sheet_name: str) -> List[Dict]:
        """キャッシュを読み込み"""
        cache_file = self._get_cache_file(sheet_name)
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text())
            except:
                pass
        return []

    def _save_cache(self, sheet_name: str, data: List[Dict]):
        """キャッシュに保存"""
        cache_file = self._get_cache_file(sheet_name)
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # ==========================================
    # バズ動画記録
    # ==========================================

    def log_buzz_video(self, video: Dict[str, Any]) -> bool:
        """バズ動画を記録"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "video_id": video.get("video_id", ""),
            "title": video.get("title", "")[:200],
            "channel_name": video.get("channel_name", ""),
            "view_count": video.get("view_count", 0),
            "performance_ratio": round(video.get("performance_ratio", 0), 2),
            "published_at": video.get("published_at", ""),
            "url": f"https://www.youtube.com/watch?v={video.get('video_id', '')}"
        }

        # ローカルキャッシュに保存
        cache = self._load_cache(self.buzz_sheet)

        # 重複チェック（同じvideo_idは追加しない）
        existing_ids = {r.get("video_id") for r in cache}
        if record["video_id"] in existing_ids:
            logger.info(f"⏭️ Skipped duplicate: {record['title'][:30]}")
            return False

        cache.append(record)
        self._save_cache(self.buzz_sheet, cache)

        logger.info(f"📊 Logged buzz video: {record['title'][:40]}")
        return True

    def log_buzz_videos(self, videos: List[Dict[str, Any]]) -> int:
        """複数のバズ動画を記録"""
        count = 0
        for video in videos:
            if self.log_buzz_video(video):
                count += 1
        logger.info(f"📊 Total {count} new buzz videos logged")
        return count

    # ==========================================
    # videos.csv全体を記録
    # ==========================================

    def log_all_videos_from_csv(self, csv_path: Optional[str] = None) -> int:
        """videos.csvの全データを記録"""
        if csv_path is None:
            csv_path = SCRIPT_DIR / "research" / "data" / "videos.csv"

        csv_path = Path(csv_path)
        if not csv_path.exists():
            logger.error(f"❌ CSV not found: {csv_path}")
            return 0

        records = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    "video_id": row.get("video_id", ""),
                    "title": row.get("title", "")[:200],
                    "channel_name": row.get("channel_name", ""),
                    "view_count": int(row.get("view_count", 0) or 0),
                    "like_count": int(row.get("like_count", 0) or 0),
                    "comment_count": int(row.get("comment_count", 0) or 0),
                    "avg_view": float(row.get("avg_view", 0) or 0),
                    "performance_ratio": round(float(row.get("performance_ratio", 0) or 0), 2),
                    "published_at": row.get("published_at", ""),
                    "url": f"https://www.youtube.com/watch?v={row.get('video_id', '')}"
                })

        self._save_cache(self.videos_sheet, records)
        logger.info(f"📊 Logged {len(records)} videos from CSV")
        return len(records)

    # ==========================================
    # チャンネル一覧
    # ==========================================

    def log_channels_from_csv(self, csv_path: Optional[str] = None) -> int:
        """channels.csvのデータを記録"""
        if csv_path is None:
            csv_path = SCRIPT_DIR / "research" / "data" / "channels.csv"

        csv_path = Path(csv_path)
        if not csv_path.exists():
            logger.error(f"❌ CSV not found: {csv_path}")
            return 0

        records = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    "channel_id": row.get("channel_id", ""),
                    "channel_name": row.get("channel_name", ""),
                    "subscriber_count": int(row.get("subscriber_count", 0) or 0),
                    "video_count": int(row.get("video_count", 0) or 0),
                    "url": f"https://www.youtube.com/channel/{row.get('channel_id', '')}"
                })

        self._save_cache(self.channels_sheet, records)
        logger.info(f"📊 Logged {len(records)} channels from CSV")
        return len(records)

    # ==========================================
    # 取得
    # ==========================================

    def get_buzz_videos(self, limit: int = 50) -> List[Dict]:
        """記録されたバズ動画を取得"""
        cache = self._load_cache(self.buzz_sheet)
        return cache[-limit:]

    def get_all_videos(self) -> List[Dict]:
        """全動画データを取得"""
        return self._load_cache(self.videos_sheet)

    # ==========================================
    # MCP経由での書き込み
    # ==========================================

    def prepare_sheets_update(self, sheet_name: str, data: List[Dict]) -> Dict[str, Any]:
        """
        スプレッドシート更新用のMCPパラメータを生成
        """
        if not self.spreadsheet_id:
            return {"error": "スプレッドシートIDが設定されていません。環境変数 YOUTUBE_SHEETS_ID を設定してください。"}

        if not data:
            return {"error": "書き込むデータがありません"}

        headers = list(data[0].keys())
        rows = [[str(row.get(h, "")) for h in headers] for row in data]

        return {
            "spreadsheetId": self.spreadsheet_id,
            "range": f"{sheet_name}!A1",
            "data": [headers] + rows
        }

    def sync_buzz_to_sheets(self) -> Dict[str, Any]:
        """バズ動画をスプレッドシートに同期"""
        data = self._load_cache(self.buzz_sheet)
        return self.prepare_sheets_update(self.buzz_sheet, data)

    def sync_videos_to_sheets(self) -> Dict[str, Any]:
        """全動画をスプレッドシートに同期"""
        data = self._load_cache(self.videos_sheet)
        return self.prepare_sheets_update(self.videos_sheet, data)


# ==========================================
# シングルトンインスタンス
# ==========================================

_logger_instance: Optional[YouTubeSheetsLogger] = None


def get_sheets_logger() -> YouTubeSheetsLogger:
    """シングルトンインスタンスを取得"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = YouTubeSheetsLogger()
    return _logger_instance


# ==========================================
# CLI
# ==========================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Sheets Logger")
    parser.add_argument("command", choices=["list-buzz", "import-csv", "sync", "export"],
                       help="list-buzz: バズ一覧, import-csv: CSVをインポート, sync: スプシ同期, export: JSON出力")
    parser.add_argument("--limit", type=int, default=20, help="表示件数")
    parser.add_argument("--spreadsheet-id", help="スプレッドシートID")

    args = parser.parse_args()

    logger_instance = YouTubeSheetsLogger(args.spreadsheet_id)

    if args.command == "list-buzz":
        videos = logger_instance.get_buzz_videos(args.limit)
        print(f"📊 バズ動画 ({len(videos)}件):\n")
        for v in videos:
            print(f"  🔥 PR={v.get('performance_ratio', 0):.1f}x | {v.get('view_count', 0):,}再生")
            print(f"     {v.get('title', '')[:50]}...")
            print(f"     {v.get('channel_name', '')} | {v.get('published_at', '')[:10]}")
            print()

    elif args.command == "import-csv":
        count = logger_instance.log_all_videos_from_csv()
        print(f"✅ {count}件の動画をインポートしました")

    elif args.command == "sync":
        # バズ動画
        buzz_params = logger_instance.sync_buzz_to_sheets()
        if "error" in buzz_params:
            print(f"❌ {buzz_params['error']}")
        else:
            print("📊 バズ動画同期パラメータ:")
            print(json.dumps(buzz_params, ensure_ascii=False, indent=2)[:500] + "...")

        # 全動画
        videos_params = logger_instance.sync_videos_to_sheets()
        if "error" not in videos_params:
            print(f"\n📊 動画一覧同期パラメータ: {len(videos_params.get('data', []))}行")

    elif args.command == "export":
        buzz = logger_instance.get_buzz_videos(1000)
        videos = logger_instance.get_all_videos()
        print(json.dumps({
            "buzz_videos": buzz,
            "all_videos": videos
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
