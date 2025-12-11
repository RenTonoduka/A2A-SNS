"""
Master Coordinator Agent - A2A Server
全Phase（0-4）を統括するオーケストレーター
人間の介入なしで完全自動化を実現
"""

import sys
import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import logging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YOUTUBE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
SNS_DIR = os.path.dirname(YOUTUBE_DIR)
sys.path.insert(0, SNS_DIR)

from _shared.a2a_base_server import A2ABaseServer, TaskSendRequest, Task, Part, Message, TaskStatus, Artifact
from _shared.a2a_client import A2AClient, AgentRegistry

# 通知システム（Google OAuth - フォールバック用）
try:
    from _shared.google_notifier import (
        notify_buzz_videos,
        notify_script_completed,
        notify_pipeline_error,
        notify,
        get_notifier
    )
    NOTIFIER_AVAILABLE = True
except ImportError:
    NOTIFIER_AVAILABLE = False

# MCP経由通知（OAuth不要 - 推奨）
try:
    from _shared.mcp_email_sender import (
        prepare_script_completion_email,
        prepare_buzz_detection_email,
        prepare_script_with_doc_and_email,
        NOTIFY_EMAIL
    )
    MCP_NOTIFIER_AVAILABLE = True
except ImportError:
    MCP_NOTIFIER_AVAILABLE = False

# 出力ディレクトリ
OUTPUT_DIR = os.path.join(YOUTUBE_DIR, "output")
FINAL_DIR = os.path.join(OUTPUT_DIR, "final")
os.makedirs(FINAL_DIR, exist_ok=True)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# スケジューラ（オプション）
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Run: pip install apscheduler")


@dataclass
class OrchestratorConfig:
    """オーケストレーター設定"""
    # 定期実行
    buzz_check_interval_minutes: int = 30
    daily_run_hour: int = 9
    daily_run_minute: int = 0

    # バズ判定
    buzz_threshold: float = 5.0
    buzz_min_views: int = 10000
    buzz_days: int = 7

    # 台本生成
    max_daily_scripts: int = 3
    target_score: int = 90
    max_improve_iterations: int = 3

    # 通知
    notify_on_buzz: bool = True
    notify_on_complete: bool = True


class MasterCoordinator(A2ABaseServer):
    """
    Master Coordinator - 全Phase統括

    機能:
    1. 定期トリガー: バズ監視、デイリーパイプライン
    2. A2A連携: 各Phaseエージェントを呼び出し
    3. Phase間データ受け渡し: 結果を次Phaseに引き継ぎ
    4. 状態管理: 実行履歴、日次制限
    """

    # エージェントURL
    AGENTS = {
        # Phase 1: Data Collection
        "channel_monitor": "http://localhost:8110",
        "video_collector": "http://localhost:8111",
        "trend_analyzer": "http://localhost:8112",
        "self_analyzer": "http://localhost:8114",
        "marketing_analytics": "http://localhost:8115",
        "style_learner": "http://localhost:8116",
        # Phase 2: Script Generation
        "research": "http://localhost:8101",
        "hook": "http://localhost:8102",
        "concept": "http://localhost:8103",
        "script_writer": "http://localhost:8113",
        # Phase 3-4: Review & Improve
        "reviewer": "http://localhost:8104",
        "improver": "http://localhost:8105",
    }

    def __init__(self, port: int = 8099, config: Optional[OrchestratorConfig] = None):
        super().__init__(
            name="master-coordinator",
            description="全Phase（0-4）を統括し、完全自動でYouTube台本生成を実行",
            port=port,
            workspace=YOUTUBE_DIR,
            timeout=600  # 10分タイムアウト
        )

        self.config = config or OrchestratorConfig()
        self.registry = AgentRegistry()
        self._register_agents()

        # スケジューラ
        self.scheduler = AsyncIOScheduler() if SCHEDULER_AVAILABLE else None

        # 状態
        self.daily_script_count = 0
        self.last_reset_date = datetime.now().date()
        self.running = False
        self._scheduler_enabled = False  # 起動時に設定

        # 追加ルート
        self._setup_orchestrator_routes()

        # FastAPI起動時にスケジューラを開始
        @self.app.on_event("startup")
        async def on_startup():
            if self._scheduler_enabled:
                self.start_scheduler()

    def _register_agents(self):
        """エージェントを登録"""
        for name, url in self.AGENTS.items():
            self.registry.register(name, url)

    def _setup_orchestrator_routes(self):
        """オーケストレーター専用ルート"""

        @self.app.get("/status")
        async def get_status():
            """システム状態を取得"""
            agents_status = await self.check_all_agents()
            return {
                "running": self.running,
                "daily_script_count": self.daily_script_count,
                "max_daily_scripts": self.config.max_daily_scripts,
                "last_reset_date": self.last_reset_date.isoformat(),
                "agents": agents_status,
                "config": asdict(self.config)
            }

        @self.app.post("/trigger/buzz-check")
        async def trigger_buzz_check():
            """バズチェックを手動トリガー"""
            result = await self.run_phase1_buzz_check()
            return result

        @self.app.post("/trigger/full-pipeline")
        async def trigger_full_pipeline():
            """フルパイプラインを手動トリガー"""
            result = await self.run_full_pipeline()
            return result

    def get_agent_card(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "url": f"http://localhost:{self.port}",
            "version": "1.0.0",
            "capabilities": {
                "streaming": False,
                "pushNotifications": False,
                "orchestration": True
            },
            "skills": [
                {
                    "id": "full-pipeline",
                    "name": "フルパイプライン実行",
                    "description": "Phase 0-4を自動実行し、台本を完成"
                },
                {
                    "id": "buzz-check",
                    "name": "バズチェック",
                    "description": "Phase 1のバズ動画検出を実行"
                },
                {
                    "id": "script-generation",
                    "name": "台本生成",
                    "description": "Phase 2-4の台本生成パイプラインを実行"
                },
                {
                    "id": "scheduled-run",
                    "name": "定期実行",
                    "description": "30分ごとバズ監視、毎日9時デイリー実行"
                }
            ]
        }

    def get_system_prompt(self) -> str:
        return """あなたはMaster Coordinator Agentです。

## 役割
YouTube台本生成システム全体（Phase 0-4）を統括し、完全自動で台本を生成します。

## 利用可能なエージェント（A2Aで呼び出し）

### Phase 1: データ収集
| Agent | Port | 役割 |
|-------|------|------|
| channel_monitor | 8110 | チャンネル監視 |
| video_collector | 8111 | 動画データ収集 |
| trend_analyzer | 8112 | バズ検出・トレンド分析 |
| self_analyzer | 8114 | 自チャンネル分析 |
| marketing_analytics | 8115 | KPI分析 |
| style_learner | 8116 | スタイル学習 |

### Phase 2: 台本生成
| Agent | Port | 役割 |
|-------|------|------|
| research | 8101 | 競合分析 |
| hook | 8102 | フック文生成 |
| concept | 8103 | 台本コンセプト |
| script_writer | 8113 | 本編作成 |

### Phase 3-4: レビュー・改善
| Agent | Port | 役割 |
|-------|------|------|
| reviewer | 8104 | 100点満点評価 |
| improver | 8105 | 台本改善 |

## コマンド

### フルパイプライン
「フルパイプラインを実行」「台本を自動生成」

### バズチェックのみ
「バズチェック」「バズ動画を探して」

### 台本生成（テーマ指定）
「[テーマ]で台本を作って」

## 実行フロー

```
1. Phase 1: バズチェック
   └─ trend_analyzer → バズ動画リスト

2. Phase 2: 台本生成
   └─ research → hook → concept → script_writer

3. Phase 3: レビュー
   └─ reviewer → スコア判定

4. Phase 4: 改善（スコア < 90 の場合）
   └─ improver → Phase 3 に戻る（最大3回）

5. 完成
   └─ メール通知、ファイル保存
```

## 出力フォーマット

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬 Master Coordinator Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Phase 1] Data Collection
├─ 🔍 trend_analyzer: バズ3件検出
│   └─ Top: 「AIで副業」PR=8.5x
└─ 所要時間: 2分

[Phase 2] Script Generation
├─ 📝 research: 競合10件分析
├─ 🪝 hook: フック3案生成
├─ 💡 concept: コンセプト確定
├─ ✍️ script_writer: 台本v1生成
└─ 所要時間: 15分

[Phase 3] Review #1
├─ 📊 スコア: 78/100
├─ 改善点: フック力、具体性
└─ 判定: → Phase 4

[Phase 4] Improve #1
├─ ✅ 改善完了: 台本v2
└─ 変更: フック強化、数値追加

[Phase 3] Review #2
├─ 📊 スコア: 92/100
└─ 判定: ✅ 採用

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Pipeline Completed
最終スコア: 92/100
イテレーション: 2回
出力: output/final/20241211_AI副業_92pts.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```"""

    # ==========================================
    # A2A エージェント呼び出し
    # ==========================================

    async def call_agent(self, agent_name: str, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        エージェントをA2Aで呼び出す

        Args:
            agent_name: エージェント名
            message: 送信メッセージ
            context: 前Phaseからのコンテキストデータ

        Returns:
            エージェントの応答
        """
        client = self.registry.get(agent_name)
        if not client:
            return {"error": f"Agent {agent_name} not registered"}

        # コンテキストがあれば付加
        if context:
            full_message = f"{message}\n\n## 前Phase結果\n```json\n{json.dumps(context, ensure_ascii=False, indent=2)}\n```"
        else:
            full_message = message

        try:
            logger.info(f"📤 Calling {agent_name}...")
            result = await client.send_task(full_message)
            logger.info(f"📥 {agent_name} responded")
            return result
        except Exception as e:
            logger.error(f"❌ {agent_name} failed: {e}")
            return {"error": str(e), "status": {"state": "failed"}}

    async def check_all_agents(self) -> Dict[str, bool]:
        """全エージェントの稼働状況を確認"""
        status = {}
        for name, client in self.registry.agents.items():
            try:
                await client.get_agent_card()
                status[name] = True
            except:
                status[name] = False
        return status

    # ==========================================
    # Phase 1: データ収集・バズ検出
    # ==========================================

    async def run_phase1_buzz_check(self) -> Dict[str, Any]:
        """Phase 1: バズ動画検出"""
        logger.info("🔍 [Phase 1] Starting buzz check...")

        # Trend Analyzer を呼び出し
        result = await self.call_agent(
            "trend_analyzer",
            f"""バズ動画を検出してください。

条件:
- PR（performance_ratio）>= {self.config.buzz_threshold}
- 再生数 >= {self.config.buzz_min_views:,}
- 直近{self.config.buzz_days}日間

出力形式:
1. バズ動画リスト（最大10件）
2. トレンドキーワード
3. 推奨テーマ"""
        )

        phase1_result = {
            "phase": "1",
            "agent": "trend_analyzer",
            "result": result
        }

        # バズ動画検出時に通知（MCP経由 + フォールバック）
        if self.config.notify_on_buzz:
            try:
                buzz_videos = self._extract_buzz_videos_list(phase1_result)
                if buzz_videos:
                    # MCP経由で通知準備（推奨）
                    if MCP_NOTIFIER_AVAILABLE:
                        mcp_data = prepare_buzz_detection_email(
                            videos=buzz_videos,
                            threshold=self.config.buzz_threshold
                        )
                        # MCPコマンドをJSONファイルとして保存
                        mcp_json_file = os.path.join(
                            OUTPUT_DIR,
                            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_buzz_email.json"
                        )
                        with open(mcp_json_file, 'w', encoding='utf-8') as f:
                            json.dump(mcp_data['mcp_params'], f, ensure_ascii=False, indent=2)

                        logger.info(f"📄 Buzz MCP notification prepared: {mcp_json_file}")
                        phase1_result["notification"] = {
                            "type": "mcp",
                            "status": "prepared",
                            "file": mcp_json_file,
                            "video_count": len(buzz_videos)
                        }

                    # Google OAuth認証フォールバック
                    elif NOTIFIER_AVAILABLE:
                        notify_result = notify_buzz_videos(
                            videos=buzz_videos,
                            threshold=self.config.buzz_threshold
                        )
                        logger.info(f"📧 Buzz OAuth notification sent: {len(buzz_videos)} videos")
                        phase1_result["notification"] = notify_result
            except Exception as e:
                logger.error(f"❌ Buzz notification failed: {e}")

        return phase1_result

    # ==========================================
    # Phase 2: 台本生成
    # ==========================================

    async def run_phase2_script_generation(self, theme: str, phase1_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Phase 2: 台本生成パイプライン"""
        logger.info(f"📝 [Phase 2] Starting script generation for: {theme}")

        results = {}

        # 2.1 Research
        logger.info("  └─ research...")
        research_result = await self.call_agent(
            "research",
            f"「{theme}」に関する競合動画を分析してください",
            phase1_context
        )
        results["research"] = research_result

        # 2.2 Hook
        logger.info("  └─ hook...")
        hook_result = await self.call_agent(
            "hook",
            f"「{theme}」のフック文を3案生成してください",
            {"research": self._extract_text(research_result)}
        )
        results["hook"] = hook_result

        # 2.3 Concept
        logger.info("  └─ concept...")
        concept_result = await self.call_agent(
            "concept",
            f"「{theme}」の台本コンセプトを作成してください",
            {
                "research": self._extract_text(research_result),
                "hook": self._extract_text(hook_result)
            }
        )
        results["concept"] = concept_result

        # 2.4 Script Writer
        logger.info("  └─ script_writer...")
        script_result = await self.call_agent(
            "script_writer",
            f"「{theme}」の台本を作成してください",
            {
                "research": self._extract_text(research_result),
                "hook": self._extract_text(hook_result),
                "concept": self._extract_text(concept_result)
            }
        )
        results["script_writer"] = script_result

        return {
            "phase": "2",
            "theme": theme,
            "results": results,
            "draft_script": self._extract_text(script_result)
        }

    # ==========================================
    # Phase 3-4: レビュー・改善ループ
    # ==========================================

    async def run_phase3_review(self, script: str, iteration: int = 1) -> Dict[str, Any]:
        """Phase 3: 台本レビュー"""
        logger.info(f"📊 [Phase 3] Review #{iteration}...")

        result = await self.call_agent(
            "reviewer",
            f"""以下の台本を100点満点で評価してください。

## 台本
{script}

## 評価軸
- フック力: /25
- 構成力: /25
- 具体性: /20
- 差別化: /15
- CTA: /15

必ずJSONで総合スコアを出力してください:
{{"score": 数値, "details": {{...}}}}"""
        )

        return {
            "phase": "3",
            "iteration": iteration,
            "result": result
        }

    async def run_phase4_improve(self, script: str, review_result: Dict, iteration: int = 1) -> Dict[str, Any]:
        """Phase 4: 台本改善"""
        logger.info(f"🔧 [Phase 4] Improve #{iteration}...")

        result = await self.call_agent(
            "improver",
            f"""以下の台本を改善してください。

## 現在の台本
{script}

## レビュー結果
{json.dumps(review_result, ensure_ascii=False, indent=2)}

低スコアの軸を重点的に改善してください。"""
        )

        return {
            "phase": "4",
            "iteration": iteration,
            "result": result,
            "improved_script": self._extract_text(result)
        }

    # ==========================================
    # フルパイプライン
    # ==========================================

    async def run_full_pipeline(self, theme: Optional[str] = None) -> Dict[str, Any]:
        """フルパイプライン実行（Phase 1-4）"""
        logger.info("🚀 Starting Full Pipeline...")

        pipeline_result = {
            "started_at": datetime.now().isoformat(),
            "phases": {}
        }

        # Phase 1: バズチェック
        phase1 = await self.run_phase1_buzz_check()
        pipeline_result["phases"]["1"] = phase1

        # テーマ決定（指定がなければPhase 1から推測）
        if not theme:
            theme = self._extract_theme_from_phase1(phase1)
            if not theme:
                theme = "AI活用術"  # フォールバック

        logger.info(f"📌 Theme: {theme}")

        # Phase 2: 台本生成
        phase2 = await self.run_phase2_script_generation(theme, phase1)
        pipeline_result["phases"]["2"] = phase2

        current_script = phase2.get("draft_script", "")

        # Phase 3-4: レビュー・改善ループ
        iteration = 0
        final_score = 0

        while iteration < self.config.max_improve_iterations:
            iteration += 1

            # Phase 3: レビュー
            phase3 = await self.run_phase3_review(current_script, iteration)
            pipeline_result["phases"][f"3_{iteration}"] = phase3

            # スコア抽出
            score = self._extract_score(phase3)
            final_score = score

            if score >= self.config.target_score:
                logger.info(f"✅ Score {score} >= {self.config.target_score}, ACCEPTED!")
                break

            if iteration >= self.config.max_improve_iterations:
                logger.warning(f"⚠️ Max iterations reached, score: {score}")
                break

            # Phase 4: 改善
            phase4 = await self.run_phase4_improve(current_script, phase3, iteration)
            pipeline_result["phases"][f"4_{iteration}"] = phase4
            current_script = phase4.get("improved_script", current_script)

        # 完了
        pipeline_result["completed_at"] = datetime.now().isoformat()
        pipeline_result["final_score"] = final_score
        pipeline_result["iterations"] = iteration
        pipeline_result["final_script"] = current_script
        pipeline_result["status"] = "success" if final_score >= self.config.target_score else "needs_review"

        # 日次カウント更新
        self.daily_script_count += 1

        # 台本をファイルに保存
        output_file = None
        if current_script:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_theme = theme.replace("/", "_").replace(" ", "_")[:30] if theme else "unknown"
            output_file = os.path.join(FINAL_DIR, f"{timestamp}_{safe_theme}_{final_score}pts.md")
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {theme}\n\n")
                    f.write(f"**スコア**: {final_score}/100\n")
                    f.write(f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"**イテレーション**: {iteration}回\n\n")
                    f.write("---\n\n")
                    f.write(current_script)
                logger.info(f"📁 Script saved: {output_file}")
                pipeline_result["output_file"] = output_file
            except Exception as e:
                logger.error(f"❌ Failed to save script: {e}")

        # 通知送信（MCP経由 + フォールバック）
        if self.config.notify_on_complete and output_file:
            try:
                # バズ動画情報を抽出（Phase 1から）
                buzz_video = self._extract_buzz_video_from_phase1(phase1)

                # MCP経由で通知準備（推奨 - OAuth不要）
                if MCP_NOTIFIER_AVAILABLE:
                    # Google Docs作成 + メール送信の準備
                    mcp_data = prepare_script_with_doc_and_email(
                        theme=theme,
                        score=final_score,
                        output_file=output_file,
                        buzz_video=buzz_video
                    )

                    # MCPコマンドをJSONファイルとして保存
                    mcp_json_file = os.path.join(
                        OUTPUT_DIR,
                        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{theme[:20].replace('/', '_')}_mcp.json"
                    )
                    with open(mcp_json_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "google_doc": mcp_data['google_doc']['mcp_params'],
                            "email": mcp_data['email']['mcp_params']
                        }, f, ensure_ascii=False, indent=2)

                    logger.info(f"📄 MCP notification prepared: {mcp_json_file}")
                    pipeline_result["mcp_notification_file"] = mcp_json_file
                    pipeline_result["notification"] = {
                        "type": "mcp",
                        "status": "prepared",
                        "file": mcp_json_file,
                        "google_doc_title": mcp_data['google_doc']['title'],
                        "email_subject": mcp_data['email']['subject']
                    }

                # Google OAuth認証フォールバック
                elif NOTIFIER_AVAILABLE:
                    notify_result = notify_script_completed(
                        theme=theme,
                        score=final_score,
                        output_file=output_file,
                        buzz_video=buzz_video,
                        include_script_content=True
                    )
                    logger.info(f"📧 OAuth notification sent: {notify_result.get('email', {})}")
                    pipeline_result["notification"] = notify_result

            except Exception as e:
                logger.error(f"❌ Notification failed: {e}")
                pipeline_result["notification_error"] = str(e)

        logger.info(f"🎉 Pipeline completed! Score: {final_score}, Iterations: {iteration}")

        return pipeline_result

    # ==========================================
    # ユーティリティ
    # ==========================================

    def _extract_text(self, result: Dict) -> str:
        """A2A結果からテキストを抽出"""
        try:
            if "artifacts" in result:
                for artifact in result["artifacts"]:
                    for part in artifact.get("parts", []):
                        if part.get("text"):
                            return part["text"]
            if "status" in result and "message" in result["status"]:
                for part in result["status"]["message"].get("parts", []):
                    if part.get("text"):
                        return part["text"]
        except:
            pass
        return str(result)

    def _extract_score(self, review_result: Dict) -> int:
        """レビュー結果からスコアを抽出"""
        try:
            text = self._extract_text(review_result)
            # JSONを探す
            import re
            match = re.search(r'"score"\s*:\s*(\d+)', text)
            if match:
                return int(match.group(1))
            # 数字を探す
            match = re.search(r'(\d+)\s*/\s*100', text)
            if match:
                return int(match.group(1))
        except:
            pass
        return 0

    def _extract_theme_from_phase1(self, phase1_result: Dict) -> Optional[str]:
        """Phase 1結果から推奨テーマを抽出"""
        try:
            text = self._extract_text(phase1_result.get("result", {}))
            # "推奨テーマ" や "おすすめ" を探す
            import re
            match = re.search(r'[「『](.*?)[」』]', text)
            if match:
                return match.group(1)
        except:
            pass
        return None

    def _extract_buzz_video_from_phase1(self, phase1_result: Dict) -> Optional[Dict]:
        """Phase 1結果からバズ動画情報を抽出"""
        try:
            text = self._extract_text(phase1_result.get("result", {}))
            import re

            # タイトルを探す
            title_match = re.search(r'タイトル[：:]\s*(.+?)(?:\n|$)', text)
            title = title_match.group(1).strip() if title_match else None

            # チャンネル名を探す
            channel_match = re.search(r'チャンネル[：:]\s*(.+?)(?:\n|$)', text)
            channel = channel_match.group(1).strip() if channel_match else None

            # PRを探す
            pr_match = re.search(r'PR[：:\s]*(\d+\.?\d*)', text)
            pr = float(pr_match.group(1)) if pr_match else 0

            # 再生数を探す
            views_match = re.search(r'再生[数回][：:\s]*([0-9,]+)', text)
            views = int(views_match.group(1).replace(',', '')) if views_match else 0

            # video_idを探す
            vid_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})', text)
            video_id = vid_match.group(1) if vid_match else None

            if title or video_id:
                return {
                    "title": title or "不明",
                    "channel_name": channel or "不明",
                    "performance_ratio": pr,
                    "view_count": views,
                    "video_id": video_id or ""
                }
        except Exception as e:
            logger.warning(f"Failed to extract buzz video: {e}")
        return None

    def _extract_buzz_videos_list(self, phase1_result: Dict) -> List[Dict]:
        """Phase 1結果からバズ動画リストを抽出"""
        videos = []
        try:
            text = self._extract_text(phase1_result.get("result", {}))
            import re

            # JSONブロックを探す
            json_match = re.search(r'\[[\s\S]*?\]', text)
            if json_match:
                try:
                    videos = json.loads(json_match.group(0))
                except:
                    pass

            # JSONが見つからない場合、テキストからパース
            if not videos:
                # 「【N位】」パターンで分割
                blocks = re.split(r'【\d+位】', text)
                for block in blocks[1:]:  # 最初の空ブロックをスキップ
                    video = {}
                    title_match = re.search(r'タイトル[：:]\s*(.+?)(?:\n|$)', block)
                    if title_match:
                        video["title"] = title_match.group(1).strip()
                    pr_match = re.search(r'PR[：:\s]*(\d+\.?\d*)', block)
                    if pr_match:
                        video["pr"] = float(pr_match.group(1))
                    if video:
                        videos.append(video)
        except Exception as e:
            logger.warning(f"Failed to extract buzz videos list: {e}")
        return videos

    # ==========================================
    # タスクハンドリング（A2Aオーバーライド）
    # ==========================================

    async def handle_task(self, request: TaskSendRequest) -> Task:
        """タスクを処理（オーケストレーション）"""
        # メッセージ抽出
        user_text = ""
        for part in request.message.parts:
            if part.text:
                user_text += part.text

        user_text_lower = user_text.lower()

        # コマンド判定
        if "フルパイプライン" in user_text or "台本を自動生成" in user_text or "full" in user_text_lower:
            result = await self.run_full_pipeline()
        elif "バズチェック" in user_text or "バズ動画" in user_text or "buzz" in user_text_lower:
            result = await self.run_phase1_buzz_check()
        elif "で台本" in user_text or "の台本" in user_text:
            # テーマ抽出
            import re
            match = re.search(r'[「『](.*?)[」』]', user_text)
            theme = match.group(1) if match else user_text.split("で")[0].strip()
            result = await self.run_full_pipeline(theme)
        else:
            # デフォルト: Claude Code で判断
            result = await super().handle_task(request)
            return result

        # 結果をTaskとして返却
        task_id = request.id or str(id(result))
        task = Task(
            id=task_id,
            contextId=request.contextId,
            status=TaskStatus(
                state="completed",
                message=Message(
                    role="agent",
                    parts=[Part(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
                )
            ),
            artifacts=[
                Artifact(
                    name="pipeline_result",
                    parts=[Part(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
                )
            ],
            history=[request.message]
        )
        self.tasks[task_id] = task
        return task

    # ==========================================
    # スケジューラ
    # ==========================================

    def setup_scheduler(self):
        """定期実行スケジュールを設定"""
        if not self.scheduler:
            logger.warning("Scheduler not available")
            return

        # 30分ごとバズチェック
        self.scheduler.add_job(
            self._scheduled_buzz_check,
            IntervalTrigger(minutes=self.config.buzz_check_interval_minutes),
            id="buzz_check",
            name="Buzz Check",
            replace_existing=True
        )

        # 毎日9時デイリーパイプライン
        self.scheduler.add_job(
            self._scheduled_daily_pipeline,
            CronTrigger(hour=self.config.daily_run_hour, minute=self.config.daily_run_minute),
            id="daily_pipeline",
            name="Daily Pipeline",
            replace_existing=True
        )

        logger.info(f"📅 Scheduled: Buzz check every {self.config.buzz_check_interval_minutes} min")
        logger.info(f"📅 Scheduled: Daily pipeline at {self.config.daily_run_hour:02d}:{self.config.daily_run_minute:02d}")

    async def _scheduled_buzz_check(self):
        """定期バズチェック"""
        logger.info("⏰ [Scheduled] Buzz check started")
        result = await self.run_phase1_buzz_check()

        # バズが見つかったら自動で台本生成
        text = self._extract_text(result.get("result", {}))
        if "バズ" in text and "検出" in text:
            theme = self._extract_theme_from_phase1(result)
            if theme and self.daily_script_count < self.config.max_daily_scripts:
                await self.run_full_pipeline(theme)

    async def _scheduled_daily_pipeline(self):
        """デイリーパイプライン"""
        logger.info("⏰ [Scheduled] Daily pipeline started")
        self._reset_daily_count()
        await self.run_full_pipeline()

    def _reset_daily_count(self):
        """日次カウントリセット"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_script_count = 0
            self.last_reset_date = today
            logger.info("📊 Daily count reset")

    def start_scheduler(self):
        """スケジューラ開始"""
        if self.scheduler:
            self.setup_scheduler()
            self.scheduler.start()
            self.running = True
            logger.info("✅ Scheduler started")

    def stop_scheduler(self):
        """スケジューラ停止"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            self.running = False
            logger.info("🛑 Scheduler stopped")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Master Coordinator Agent")
    parser.add_argument("--port", type=int, default=8099, help="Server port")
    parser.add_argument("--with-scheduler", action="store_true", help="Start with scheduler")
    args = parser.parse_args()

    # 環境変数でもスケジューラ有効化可能（SSH経由での引数問題回避）
    enable_scheduler = args.with_scheduler or os.environ.get("ENABLE_SCHEDULER", "").lower() in ("1", "true", "yes")

    coordinator = MasterCoordinator(port=args.port)

    print("=" * 60)
    print("🎬 Master Coordinator Agent")
    print("=" * 60)
    print(f"  Port: {args.port}")
    print(f"  Scheduler: {'Enabled' if enable_scheduler else 'Disabled'}")
    print(f"  (env ENABLE_SCHEDULER={os.environ.get('ENABLE_SCHEDULER', 'not set')})")
    print("")
    print("Endpoints:")
    print(f"  GET  /.well-known/agent.json  - Agent Card")
    print(f"  POST /a2a/tasks/send          - Send Task")
    print(f"  GET  /status                  - System Status")
    print(f"  POST /trigger/buzz-check      - Manual Buzz Check")
    print(f"  POST /trigger/full-pipeline   - Manual Full Pipeline")
    print("=" * 60)

    if enable_scheduler:
        coordinator._scheduler_enabled = True

    coordinator.run()
