"""
X Post Extractor - ポスト抽出モジュール
特定アカウントのポストを抽出してJSON/CSV/Markdownで出力
"""

import asyncio
import json
import csv
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field

from playwright.async_api import Page, Locator

from config import DATA_DIR, LOGS_DIR, ExtractorConfig
from session_manager import SessionManager, BrowserConfig

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "extractor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class XPost:
    """Xポストデータ"""
    post_id: str
    author_username: str
    author_name: str
    content: str
    timestamp: str
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0
    is_retweet: bool = False
    is_reply: bool = False
    media_urls: List[str] = field(default_factory=list)
    post_url: str = ""
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PostExtractor:
    """
    Xポスト抽出クラス

    機能:
    1. 特定アカウントのポストを抽出
    2. いいね数・RT数でフィルタリング
    3. JSON/CSV/Markdown形式で出力
    """

    def __init__(
        self,
        session_manager: SessionManager,
        config: Optional[ExtractorConfig] = None
    ):
        self.session = session_manager
        self.config = config or ExtractorConfig()
        self._extracted_posts: Dict[str, List[XPost]] = {}

    @property
    def page(self) -> Page:
        if not self.session.page:
            raise RuntimeError("Session not started")
        return self.session.page

    # ==========================================
    # ポスト抽出
    # ==========================================

    async def extract_from_account(
        self,
        username: str,
        max_posts: Optional[int] = None
    ) -> List[XPost]:
        """
        特定アカウントからポストを抽出

        Args:
            username: @なしのユーザー名
            max_posts: 最大取得数（Noneの場合はconfig値）
        """
        max_posts = max_posts or self.config.max_posts_per_account
        logger.info(f"📥 Extracting posts from @{username} (max: {max_posts})")

        # プロフィールページに移動
        profile_url = f"https://x.com/{username}"
        await self.page.goto(profile_url, wait_until="networkidle")
        await asyncio.sleep(2)

        # アカウントが存在するか確認
        if await self._check_account_not_found():
            logger.warning(f"⚠️ Account @{username} not found")
            return []

        posts: List[XPost] = []
        seen_ids: set = set()
        scroll_attempts = 0
        no_new_posts_count = 0

        while len(posts) < max_posts and scroll_attempts < self.config.max_scroll_attempts:
            # 現在表示されているポストを取得
            post_elements = await self.page.locator('article[data-testid="tweet"]').all()

            for element in post_elements:
                try:
                    post = await self._parse_post_element(element, username)

                    if post and post.post_id not in seen_ids:
                        # フィルタリング
                        if self._should_include_post(post):
                            posts.append(post)
                            seen_ids.add(post.post_id)
                            logger.debug(f"  ✅ Extracted: {post.content[:50]}...")

                            if len(posts) >= max_posts:
                                break

                except Exception as e:
                    logger.debug(f"  ⚠️ Failed to parse post: {e}")
                    continue

            # 新しいポストがなければカウント
            if len(posts) == len(seen_ids) - len(posts):
                no_new_posts_count += 1
                if no_new_posts_count >= 5:
                    logger.info("📭 No more new posts found")
                    break
            else:
                no_new_posts_count = 0

            # スクロール
            await self._scroll_down()
            scroll_attempts += 1

            logger.info(f"  📊 Progress: {len(posts)}/{max_posts} posts")

        logger.info(f"✅ Extracted {len(posts)} posts from @{username}")
        self._extracted_posts[username] = posts
        return posts

    async def _parse_post_element(
        self,
        element: Locator,
        target_username: str
    ) -> Optional[XPost]:
        """ポスト要素をパース"""
        try:
            # ポストID取得（URLから）
            post_link = element.locator('a[href*="/status/"]').first
            href = await post_link.get_attribute("href") if await post_link.count() > 0 else None

            if not href:
                return None

            # URLからポストIDを抽出
            match = re.search(r'/status/(\d+)', href)
            if not match:
                return None

            post_id = match.group(1)

            # 著者情報
            author_link = element.locator('a[role="link"]').first
            author_href = await author_link.get_attribute("href") if await author_link.count() > 0 else ""
            author_username = author_href.strip("/") if author_href else target_username

            # 著者名
            author_name_elem = element.locator('[data-testid="User-Name"]').first
            author_name = await author_name_elem.inner_text() if await author_name_elem.count() > 0 else ""
            # 改行で分割して最初の行を取得
            author_name = author_name.split("\n")[0] if author_name else author_username

            # コンテンツ
            content_elem = element.locator('[data-testid="tweetText"]').first
            content = await content_elem.inner_text() if await content_elem.count() > 0 else ""

            # タイムスタンプ
            time_elem = element.locator('time').first
            timestamp = await time_elem.get_attribute("datetime") if await time_elem.count() > 0 else ""

            # エンゲージメント数
            likes = await self._extract_engagement(element, "like")
            retweets = await self._extract_engagement(element, "retweet")
            replies = await self._extract_engagement(element, "reply")

            # ビュー数（存在する場合）
            views = 0
            views_elem = element.locator('a[href*="/analytics"]').first
            if await views_elem.count() > 0:
                views_text = await views_elem.inner_text()
                views = self._parse_number(views_text)

            # リツイート・リプライ判定
            is_retweet = "Reposted" in author_name or "がリポスト" in author_name
            is_reply = await element.locator('[data-testid="socialContext"]').count() > 0

            # メディアURL
            media_urls = []
            media_elements = await element.locator('img[src*="pbs.twimg.com/media"]').all()
            for media in media_elements:
                src = await media.get_attribute("src")
                if src:
                    media_urls.append(src)

            return XPost(
                post_id=post_id,
                author_username=author_username,
                author_name=author_name,
                content=content,
                timestamp=timestamp,
                likes=likes,
                retweets=retweets,
                replies=replies,
                views=views,
                is_retweet=is_retweet,
                is_reply=is_reply,
                media_urls=media_urls,
                post_url=f"https://x.com/{author_username}/status/{post_id}"
            )

        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None

    async def _extract_engagement(self, element: Locator, action: str) -> int:
        """エンゲージメント数を抽出"""
        try:
            btn = element.locator(f'[data-testid="{action}"]').first
            if await btn.count() > 0:
                text = await btn.inner_text()
                return self._parse_number(text)
        except:
            pass
        return 0

    def _parse_number(self, text: str) -> int:
        """数値文字列をパース（1.5K → 1500）"""
        if not text:
            return 0

        text = text.strip().upper()
        multiplier = 1

        if "K" in text:
            multiplier = 1000
            text = text.replace("K", "")
        elif "M" in text:
            multiplier = 1000000
            text = text.replace("M", "")
        elif "万" in text:
            multiplier = 10000
            text = text.replace("万", "")

        try:
            return int(float(text) * multiplier)
        except:
            return 0

    def _should_include_post(self, post: XPost) -> bool:
        """ポストをフィルタリング"""
        # リプライフィルタ
        if post.is_reply and not self.config.include_replies:
            return False

        # リツイートフィルタ
        if post.is_retweet and not self.config.include_retweets:
            return False

        # いいね数フィルタ
        if post.likes < self.config.min_likes:
            return False

        # RT数フィルタ
        if post.retweets < self.config.min_retweets:
            return False

        return True

    async def _check_account_not_found(self) -> bool:
        """アカウントが見つからないかチェック"""
        # 404ページまたは"doesn't exist"メッセージ
        not_found = await self.page.locator('text="doesn\'t exist"').count() > 0
        suspended = await self.page.locator('text="Account suspended"').count() > 0
        return not_found or suspended

    async def _scroll_down(self):
        """ページをスクロール"""
        await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(self.config.scroll_delay_ms / 1000)

    # ==========================================
    # 複数アカウント抽出
    # ==========================================

    async def extract_from_accounts(
        self,
        usernames: List[str],
        max_posts_per_account: Optional[int] = None
    ) -> Dict[str, List[XPost]]:
        """複数アカウントからポストを抽出"""
        results = {}

        for username in usernames:
            posts = await self.extract_from_account(username, max_posts_per_account)
            results[username] = posts
            await asyncio.sleep(2)  # レート制限対策

        return results

    # ==========================================
    # 出力
    # ==========================================

    def save_json(
        self,
        posts: List[XPost],
        filename: str,
        output_dir: Optional[Path] = None
    ) -> Path:
        """JSON形式で保存"""
        output_dir = output_dir or DATA_DIR
        filepath = output_dir / f"{filename}.json"

        data = [asdict(p) for p in posts]
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2))

        logger.info(f"💾 Saved {len(posts)} posts to {filepath}")
        return filepath

    def save_csv(
        self,
        posts: List[XPost],
        filename: str,
        output_dir: Optional[Path] = None
    ) -> Path:
        """CSV形式で保存"""
        output_dir = output_dir or DATA_DIR
        filepath = output_dir / f"{filename}.csv"

        if not posts:
            return filepath

        fieldnames = list(asdict(posts[0]).keys())

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for post in posts:
                row = asdict(post)
                row["media_urls"] = ";".join(row["media_urls"])  # リストを文字列に
                writer.writerow(row)

        logger.info(f"💾 Saved {len(posts)} posts to {filepath}")
        return filepath

    def save_markdown(
        self,
        posts: List[XPost],
        filename: str,
        output_dir: Optional[Path] = None
    ) -> Path:
        """Markdown形式で保存"""
        output_dir = output_dir or DATA_DIR
        filepath = output_dir / f"{filename}.md"

        lines = [
            f"# X Posts - {filename}",
            f"",
            f"Generated: {datetime.now().isoformat()}",
            f"Total: {len(posts)} posts",
            f"",
            "---",
            ""
        ]

        for post in posts:
            lines.extend([
                f"## @{post.author_username}",
                f"",
                f"> {post.content}",
                f"",
                f"- 📅 {post.timestamp}",
                f"- ❤️ {post.likes} | 🔄 {post.retweets} | 💬 {post.replies}",
                f"- 🔗 [{post.post_url}]({post.post_url})",
                f"",
                "---",
                ""
            ])

        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"💾 Saved {len(posts)} posts to {filepath}")
        return filepath

    def save(
        self,
        posts: List[XPost],
        filename: str,
        format: str = "json",
        output_dir: Optional[Path] = None
    ) -> Path:
        """指定形式で保存"""
        if format == "json":
            return self.save_json(posts, filename, output_dir)
        elif format == "csv":
            return self.save_csv(posts, filename, output_dir)
        elif format == "markdown" or format == "md":
            return self.save_markdown(posts, filename, output_dir)
        else:
            raise ValueError(f"Unsupported format: {format}")


# ==========================================
# CLI
# ==========================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="X Post Extractor")
    parser.add_argument("usernames", nargs="+", help="抽出するユーザー名（@なし）")
    parser.add_argument("--max", type=int, default=50, help="アカウントごとの最大取得数")
    parser.add_argument("--format", choices=["json", "csv", "markdown"], default="json",
                       help="出力形式")
    parser.add_argument("--output", help="出力ファイル名（拡張子なし）")
    parser.add_argument("--session", default="default", help="セッション名")
    parser.add_argument("--min-likes", type=int, default=0, help="最小いいね数")
    parser.add_argument("--include-replies", action="store_true", help="リプライを含める")
    parser.add_argument("--include-retweets", action="store_true", help="リツイートを含める")

    args = parser.parse_args()

    # 設定
    browser_config = BrowserConfig(session_name=args.session)
    extractor_config = ExtractorConfig(
        max_posts_per_account=args.max,
        min_likes=args.min_likes,
        include_replies=args.include_replies,
        include_retweets=args.include_retweets,
        output_format=args.format
    )

    print("=" * 60)
    print("📥 X Post Extractor")
    print("=" * 60)
    print(f"  Targets: {', '.join(['@' + u for u in args.usernames])}")
    print(f"  Max posts per account: {args.max}")
    print(f"  Output format: {args.format}")
    print("=" * 60)

    async with SessionManager(browser_config) as session:
        # ログイン確認
        if not await session.ensure_logged_in():
            print("❌ ログインが必要です")
            return

        extractor = PostExtractor(session, extractor_config)

        # 抽出
        all_posts = []
        for username in args.usernames:
            posts = await extractor.extract_from_account(username)
            all_posts.extend(posts)

        # 保存
        if all_posts:
            output_name = args.output or f"x_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            filepath = extractor.save(all_posts, output_name, args.format)
            print(f"\n✅ 完了! {len(all_posts)}件のポストを保存しました")
            print(f"   📁 {filepath}")
        else:
            print("\n❌ ポストが見つかりませんでした")


if __name__ == "__main__":
    asyncio.run(main())
