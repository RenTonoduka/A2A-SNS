"""
Google Sheets Logger - バズポスト・生成ポストをスプレッドシートに記録
MCP経由でGoogle Sheetsに書き込み
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SheetsLogger:
    """
    Google Sheetsにデータを記録

    使用方法:
    1. MCP経由: Claude Code CLIのMCPツールを使用
    2. ローカルキャッシュ: MCP未使用時はJSONに保存
    """

    def __init__(self, spreadsheet_id: Optional[str] = None):
        self.spreadsheet_id = spreadsheet_id or os.getenv("X_SHEETS_ID", "")
        self.cache_dir = SCRIPT_DIR / "data" / "sheets_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # シート名
        self.buzz_sheet = "バズポスト"
        self.generated_sheet = "生成ポスト"

    def _get_cache_file(self, sheet_name: str) -> Path:
        """キャッシュファイルパスを取得"""
        return self.cache_dir / f"{sheet_name}.json"

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
    # バズポスト記録
    # ==========================================

    def log_buzz_post(self, post: Dict[str, Any]) -> bool:
        """バズポストを記録"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "post_id": post.get("post_id", ""),
            "author": post.get("author", ""),
            "content": post.get("content", "")[:500],
            "likes": post.get("likes", 0),
            "retweets": post.get("retweets", 0),
            "buzz_score": post.get("buzz_score", 0),
            "post_url": post.get("post_url", ""),
            "detected_at": post.get("detected_at", "")
        }

        # ローカルキャッシュに保存
        cache = self._load_cache(self.buzz_sheet)
        cache.append(record)
        self._save_cache(self.buzz_sheet, cache)

        logger.info(f"📊 Logged buzz post: @{record['author']}")
        return True

    def log_buzz_posts(self, posts: List[Dict[str, Any]]) -> int:
        """複数のバズポストを記録"""
        count = 0
        for post in posts:
            if self.log_buzz_post(post):
                count += 1
        return count

    # ==========================================
    # 生成ポスト記録
    # ==========================================

    def log_generated_post(self, post: Dict[str, Any]) -> bool:
        """生成ポストを記録"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "content": post.get("content", ""),
            "style": post.get("style", ""),
            "tone": post.get("tone", ""),
            "hashtags": post.get("hashtags", ""),
            "buzz_patterns": post.get("buzz_patterns", ""),
            "generated_at": post.get("generated_at", ""),
            "score": post.get("score", ""),
            "status": "draft"  # draft, scheduled, posted
        }

        # ローカルキャッシュに保存
        cache = self._load_cache(self.generated_sheet)
        cache.append(record)
        self._save_cache(self.generated_sheet, cache)

        logger.info(f"📝 Logged generated post")
        return True

    # ==========================================
    # 取得
    # ==========================================

    def get_buzz_posts(self, limit: int = 50) -> List[Dict]:
        """記録されたバズポストを取得"""
        cache = self._load_cache(self.buzz_sheet)
        return cache[-limit:]

    def get_generated_posts(self, limit: int = 50) -> List[Dict]:
        """記録された生成ポストを取得"""
        cache = self._load_cache(self.generated_sheet)
        return cache[-limit:]

    # ==========================================
    # MCP経由での書き込み（Claude Code CLIから呼び出し）
    # ==========================================

    def get_sheets_write_prompt(self, data: List[Dict], sheet_name: str) -> str:
        """
        スプレッドシート書き込み用のプロンプトを生成
        Claude Code CLIがMCPツールを使って実行
        """
        if not self.spreadsheet_id:
            return "❌ スプレッドシートIDが設定されていません。環境変数 X_SHEETS_ID を設定してください。"

        # データを2D配列に変換
        if not data:
            return "❌ 書き込むデータがありません"

        headers = list(data[0].keys())
        rows = [[str(row.get(h, "")) for h in headers] for row in data]

        prompt = f"""Google Sheetsに以下のデータを書き込んでください。

スプレッドシートID: {self.spreadsheet_id}
シート名: {sheet_name}

データ:
ヘッダー: {headers}
行数: {len(rows)}件

MCP ツール mcp__google-drive__updateGoogleSheet を使用して書き込んでください。

```json
{{
  "spreadsheetId": "{self.spreadsheet_id}",
  "range": "{sheet_name}!A1",
  "data": {json.dumps([headers] + rows, ensure_ascii=False)}
}}
```
"""
        return prompt

    def sync_to_sheets(self) -> Dict[str, str]:
        """
        ローカルキャッシュをスプレッドシートに同期するためのプロンプトを生成
        """
        prompts = {}

        # バズポスト
        buzz_data = self._load_cache(self.buzz_sheet)
        if buzz_data:
            prompts["buzz"] = self.get_sheets_write_prompt(buzz_data, self.buzz_sheet)

        # 生成ポスト
        gen_data = self._load_cache(self.generated_sheet)
        if gen_data:
            prompts["generated"] = self.get_sheets_write_prompt(gen_data, self.generated_sheet)

        return prompts


# ==========================================
# CLI
# ==========================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sheets Logger")
    parser.add_argument("command", choices=["list-buzz", "list-generated", "sync", "export"],
                       help="list-buzz: バズ一覧, list-generated: 生成一覧, sync: スプシ同期プロンプト, export: JSON出力")
    parser.add_argument("--limit", type=int, default=20, help="表示件数")
    parser.add_argument("--spreadsheet-id", help="スプレッドシートID")

    args = parser.parse_args()

    logger_instance = SheetsLogger(args.spreadsheet_id)

    if args.command == "list-buzz":
        posts = logger_instance.get_buzz_posts(args.limit)
        print(f"📊 バズポスト ({len(posts)}件):\n")
        for p in posts:
            print(f"  @{p.get('author', '')} - ❤️ {p.get('likes', 0):,}")
            print(f"    {p.get('content', '')[:60]}...")
            print()

    elif args.command == "list-generated":
        posts = logger_instance.get_generated_posts(args.limit)
        print(f"📝 生成ポスト ({len(posts)}件):\n")
        for p in posts:
            print(f"  [{p.get('style', '')}] {p.get('content', '')[:60]}...")
            print(f"    生成: {p.get('timestamp', '')[:19]}")
            print()

    elif args.command == "sync":
        prompts = logger_instance.sync_to_sheets()
        if prompts:
            print("📊 スプレッドシート同期プロンプト:\n")
            for key, prompt in prompts.items():
                print(f"=== {key} ===")
                print(prompt[:500] + "...")
                print()
        else:
            print("❌ 同期するデータがありません")

    elif args.command == "export":
        buzz = logger_instance.get_buzz_posts(1000)
        gen = logger_instance.get_generated_posts(1000)
        print(json.dumps({
            "buzz_posts": buzz,
            "generated_posts": gen
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
