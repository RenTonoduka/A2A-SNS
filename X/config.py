"""
X Post Extractor - 設定
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

# パス設定
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
SESSION_DIR = SCRIPT_DIR / "sessions"
LOGS_DIR = SCRIPT_DIR / "logs"

# ディレクトリ作成
DATA_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


@dataclass
class ExtractorConfig:
    """ポスト抽出設定"""
    # ターゲットアカウント
    target_accounts: List[str] = field(default_factory=list)

    # 抽出設定
    max_posts_per_account: int = 50       # アカウントごとの最大取得数
    include_replies: bool = False          # リプライを含めるか
    include_retweets: bool = False         # リツイートを含めるか
    min_likes: int = 0                     # 最小いいね数フィルタ
    min_retweets: int = 0                  # 最小RT数フィルタ

    # スクロール設定
    scroll_delay_ms: int = 1000            # スクロール間隔(ms)
    max_scroll_attempts: int = 100         # 最大スクロール回数

    # 出力設定
    output_format: str = "json"            # json, csv, markdown
    save_media: bool = False               # 画像/動画を保存するか


@dataclass
class BrowserConfig:
    """ブラウザ設定"""
    headless: bool = False                 # ヘッドレスモード（初回ログイン時はFalse推奨）
    slow_mo: int = 50                      # 操作間隔(ms)
    viewport_width: int = 1280
    viewport_height: int = 800
    user_agent: Optional[str] = None       # カスタムUser-Agent

    # セッション設定
    session_name: str = "default"          # セッション名
    session_file: Optional[Path] = None    # セッションファイルパス

    def __post_init__(self):
        if self.session_file is None:
            self.session_file = SESSION_DIR / f"{self.session_name}_session.json"


@dataclass
class A2AConfig:
    """A2Aサーバー設定"""
    host: str = "0.0.0.0"
    port: int = 8120
    agent_name: str = "X Post Extractor"
    agent_description: str = "X（Twitter）の特定アカウントからポストを抽出するエージェント"
    version: str = "1.0.0"


# 環境変数からの設定読み込み
def load_config_from_env() -> dict:
    """環境変数から設定を読み込み"""
    return {
        "target_accounts": os.getenv("X_TARGET_ACCOUNTS", "").split(",") if os.getenv("X_TARGET_ACCOUNTS") else [],
        "headless": os.getenv("X_HEADLESS", "false").lower() == "true",
        "max_posts": int(os.getenv("X_MAX_POSTS", "50")),
        "a2a_port": int(os.getenv("X_A2A_PORT", "8120")),
    }
