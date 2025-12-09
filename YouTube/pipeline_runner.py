"""
YouTube Pipeline Runner - 自動パイプライン実行
チャンネルリストから自動で台本生成を行う
"""

import os
import sys
import json
import asyncio
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path

# パス設定
SCRIPT_DIR = Path(__file__).parent
SNS_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SNS_DIR))

from _shared.mcp_tools import LOG_SPREADSHEET_ID, NOTIFY_EMAIL

# 出力ディレクトリ
OUTPUT_DIR = SCRIPT_DIR / "output"
SCRIPTS_DIR = OUTPUT_DIR / "scripts"      # 生成中の台本
CONCEPTS_DIR = OUTPUT_DIR / "concepts"    # コンセプト
REVIEWS_DIR = OUTPUT_DIR / "reviews"      # レビュー結果
FINAL_DIR = OUTPUT_DIR / "final"          # 完成台本（90点以上）

# エージェントURL
AGENTS = {
    # Phase 1: Data Collection
    "channel_monitor": "http://localhost:8110",
    "video_collector": "http://localhost:8111",
    "trend_analyzer": "http://localhost:8112",
    # Phase 2: Script Generation
    "coordinator": "http://localhost:8100",
    "research": "http://localhost:8101",
    "hook": "http://localhost:8102",
    "concept": "http://localhost:8103",
    "reviewer": "http://localhost:8104",
    "improver": "http://localhost:8105",
    "script_writer": "http://localhost:8113",  # 本編作成エージェント
}


@dataclass
class PipelineResult:
    """パイプライン実行結果"""
    theme: str
    status: str  # success, failed, in_progress
    final_score: int
    iterations: int
    started_at: str
    completed_at: str
    output_files: Dict[str, str]
    error: Optional[str] = None


class PipelineRunner:
    """
    自動パイプライン実行クラス

    機能:
    - チャンネルリストから優秀動画を分析
    - テーマを自動生成
    - 台本パイプラインを実行
    - 完成台本を保存・通知
    """

    def __init__(self, timeout: int = 600):
        self.timeout = timeout

        # ディレクトリ作成
        for d in [OUTPUT_DIR, SCRIPTS_DIR, CONCEPTS_DIR, REVIEWS_DIR, FINAL_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    async def close(self):
        pass  # urllib doesn't need cleanup

    # ==========================================
    # エージェント通信
    # ==========================================

    async def call_agent(self, agent: str, message: str) -> Dict[str, Any]:
        """エージェントを呼び出す"""
        url = f"{AGENTS[agent]}/a2a/tasks/send"

        payload = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": message}]
            }
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {"error": str(e), "status": {"state": "failed"}}

    async def check_agents(self) -> Dict[str, bool]:
        """全エージェントの稼働状況を確認"""
        status = {}
        for name, base_url in AGENTS.items():
            try:
                req = urllib.request.Request(f"{base_url}/.well-known/agent.json")
                with urllib.request.urlopen(req, timeout=5) as response:
                    status[name] = response.status == 200
            except:
                status[name] = False
        return status

    # ==========================================
    # パイプライン実行
    # ==========================================

    async def run_pipeline(
        self,
        theme: str,
        max_iterations: int = 3,
        target_score: int = 90
    ) -> PipelineResult:
        """
        完全パイプライン実行

        Args:
            theme: 動画テーマ
            max_iterations: 最大改善回数
            target_score: 目標スコア

        Returns:
            PipelineResult
        """
        started_at = datetime.now()
        timestamp = started_at.strftime("%Y%m%d_%H%M%S")
        safe_theme = theme.replace("/", "_").replace(" ", "_")[:30]

        output_files = {}
        current_score = 0
        iterations = 0

        print(f"\n{'='*60}")
        print(f"🎬 Pipeline Start: {theme}")
        print(f"{'='*60}")

        try:
            # Phase 1: Research
            print("\n[Phase 1] Research...")
            research_result = await self.call_agent(
                "research",
                f"以下のテーマで競合分析を行ってください:\n\nテーマ: {theme}\n\n"
                "・上位動画10件の分析\n"
                "・タイトルパターン抽出\n"
                "・視聴者の不満・ギャップ"
            )

            research_output = self._extract_output(research_result)
            research_file = SCRIPTS_DIR / f"{timestamp}_{safe_theme}_1_research.md"
            research_file.write_text(research_output, encoding="utf-8")
            output_files["research"] = str(research_file)
            print(f"  ✅ Research complete: {research_file.name}")

            # Phase 2: Hook + Concept (並列)
            print("\n[Phase 2] Hook & Concept...")
            hook_task = self.call_agent(
                "hook",
                f"テーマ: {theme}\n\nリサーチ結果:\n{research_output[:2000]}\n\n"
                "上記を踏まえてフック文を3案生成してください。"
            )
            concept_task = self.call_agent(
                "concept",
                f"テーマ: {theme}\n\nリサーチ結果:\n{research_output[:2000]}\n\n"
                "上記を踏まえて15分台本コンセプトを生成してください。"
            )

            hook_result, concept_result = await asyncio.gather(hook_task, concept_task)

            hook_output = self._extract_output(hook_result)
            hook_file = CONCEPTS_DIR / f"{timestamp}_{safe_theme}_2_hook.md"
            hook_file.write_text(hook_output, encoding="utf-8")
            output_files["hook"] = str(hook_file)
            print(f"  ✅ Hook complete: {hook_file.name}")

            concept_output = self._extract_output(concept_result)
            concept_file = CONCEPTS_DIR / f"{timestamp}_{safe_theme}_2_concept.md"
            concept_file.write_text(concept_output, encoding="utf-8")
            output_files["concept"] = str(concept_file)
            print(f"  ✅ Concept complete: {concept_file.name}")

            # 台本統合
            current_script = f"# {theme}\n\n## フック\n{hook_output}\n\n## 台本\n{concept_output}"

            # Phase 3-4: Review & Improve ループ
            while iterations < max_iterations:
                iterations += 1
                print(f"\n[Phase 3] Review #{iterations}...")

                review_result = await self.call_agent(
                    "reviewer",
                    f"以下の台本を100点満点で評価してください:\n\n{current_script}"
                )

                review_output = self._extract_output(review_result)
                review_file = REVIEWS_DIR / f"{timestamp}_{safe_theme}_3_review_{iterations}.md"
                review_file.write_text(review_output, encoding="utf-8")
                output_files[f"review_{iterations}"] = str(review_file)

                # スコア抽出
                current_score = self._extract_score(review_output)
                print(f"  📊 Score: {current_score}/100")

                if current_score >= target_score:
                    print(f"  ✅ Target achieved! ({current_score} >= {target_score})")
                    break

                if iterations < max_iterations:
                    print(f"\n[Phase 4] Improve #{iterations}...")
                    improve_result = await self.call_agent(
                        "improver",
                        f"以下の台本を改善してください:\n\n"
                        f"## 現在の台本\n{current_script}\n\n"
                        f"## レビュー結果\n{review_output}"
                    )

                    improve_output = self._extract_output(improve_result)
                    current_script = improve_output

                    improve_file = SCRIPTS_DIR / f"{timestamp}_{safe_theme}_4_improve_{iterations}.md"
                    improve_file.write_text(improve_output, encoding="utf-8")
                    output_files[f"improve_{iterations}"] = str(improve_file)
                    print(f"  ✅ Improvement complete")

            # Phase 5: Script Writer（本編作成 - 競合トランスクリプト分析）
            print(f"\n[Phase 5] Script Writer (本編作成)...")
            script_writer_result = await self.call_agent(
                "script_writer",
                f"""以下のコンセプトを元に、本編台本を作成してください。

## テーマ
{theme}

## コンセプト
{concept_output[:3000]}

## フック
{hook_output[:1000]}

## 指示
1. 競合動画のトランスクリプトを取得して構成を分析してください
2. モデリング先の成功パターンをトレースしてください
3. 自分用にカスタマイズした本編台本を作成してください

MCPツールを使って競合トランスクリプトを取得:
```
mcp__klavis-strata__execute_action(
    server_name="youtube",
    category_name="YOUTUBE_TRANSCRIPT",
    action_name="get_youtube_video_transcript",
    body_schema='{{"url": "競合動画URL"}}'
)
```
"""
            )

            script_output = self._extract_output(script_writer_result)
            script_file = SCRIPTS_DIR / f"{timestamp}_{safe_theme}_5_script.md"
            script_file.write_text(script_output, encoding="utf-8")
            output_files["script"] = str(script_file)
            print(f"  ✅ Script complete: {script_file.name}")

            # 台本統合（本編含む）
            full_script = f"# {theme}\n\n## フック\n{hook_output}\n\n## コンセプト\n{concept_output}\n\n## 本編台本\n{script_output}"

            # 最終台本保存
            final_file = FINAL_DIR / f"{timestamp}_{safe_theme}_FINAL_{current_score}pts.md"
            final_content = f"""# {theme}
## 最終スコア: {current_score}/100
## イテレーション: {iterations}回
## 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{full_script}
"""
            final_file.write_text(final_content, encoding="utf-8")
            output_files["final"] = str(final_file)

            print(f"\n{'='*60}")
            print(f"✅ Pipeline Complete!")
            print(f"   Theme: {theme}")
            print(f"   Score: {current_score}/100")
            print(f"   Iterations: {iterations}")
            print(f"   Final: {final_file.name}")
            print(f"{'='*60}")

            # 台本完成通知 + Google Docs作成用データを準備（MCPで実行）
            try:
                sys.path.insert(0, str(SNS_DIR / "_shared"))
                from mcp_email_sender import prepare_script_with_doc_and_email
                output_data = prepare_script_with_doc_and_email(
                    theme=theme,
                    score=current_score,
                    output_file=str(final_file)
                )

                # 統合JSONを保存（Google Docs + メール）
                mcp_json_file = FINAL_DIR / f"{timestamp}_{safe_theme}_mcp.json"
                with open(mcp_json_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "google_doc": output_data['google_doc']['mcp_params'],
                        "email": output_data['email']['mcp_params']
                    }, f, ensure_ascii=False, indent=2)

                print(f"📄 Google Docs + メール準備完了: {mcp_json_file.name}")
                print(f"   → MCP経由で実行してください")
            except Exception as notify_err:
                print(f"⚠️ 出力準備エラー: {notify_err}")

            return PipelineResult(
                theme=theme,
                status="success" if current_score >= target_score else "below_target",
                final_score=current_score,
                iterations=iterations,
                started_at=started_at.isoformat(),
                completed_at=datetime.now().isoformat(),
                output_files=output_files
            )

        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")

            # エラー通知
            try:
                sys.path.insert(0, str(SNS_DIR / "_shared"))
                from google_notifier import notify_pipeline_error
                notify_pipeline_error("Script Generation", str(e), f"Theme: {theme}")
                print("📧 エラー通知メール送信")
            except Exception as notify_err:
                print(f"⚠️ 通知エラー: {notify_err}")

            return PipelineResult(
                theme=theme,
                status="failed",
                final_score=current_score,
                iterations=iterations,
                started_at=started_at.isoformat(),
                completed_at=datetime.now().isoformat(),
                output_files=output_files,
                error=str(e)
            )

    # ==========================================
    # チャンネルベース自動実行
    # ==========================================

    async def run_from_channels(
        self,
        theme_prompt: Optional[str] = None,
        count: int = 1
    ) -> List[PipelineResult]:
        """
        チャンネルリストから優秀動画を分析してテーマを生成し、パイプライン実行

        Args:
            theme_prompt: テーマ生成のヒント（なければ自動分析）
            count: 生成する台本数
        """
        # 1. 優秀動画分析でテーマ候補を取得
        print("\n🔍 Analyzing outstanding videos for theme ideas...")

        research_result = await self.call_agent(
            "research",
            f"""チャンネルリスト（research/data/channels.csv）と
動画データ（research/data/videos.csv）を分析して、
今すぐ作るべき動画テーマを{count}つ提案してください。

追加ヒント: {theme_prompt or "AI・テクノロジー系で、視聴者の不満を解決するもの"}

## 出力形式
以下のJSON形式で出力してください:
```json
{{
    "themes": [
        {{
            "theme": "テーマタイトル",
            "reason": "このテーマを選んだ理由",
            "target_audience": "ターゲット",
            "differentiator": "差別化ポイント"
        }}
    ]
}}
```"""
        )

        research_output = self._extract_output(research_result)

        # テーマ抽出
        themes = self._extract_themes(research_output)

        if not themes:
            print("❌ Could not generate themes. Using default.")
            themes = [{"theme": theme_prompt or "AI活用で業務効率化する方法"}]

        # 2. 各テーマでパイプライン実行
        results = []
        for i, t in enumerate(themes[:count], 1):
            theme = t.get("theme", t) if isinstance(t, dict) else t
            print(f"\n{'='*60}")
            print(f"📹 Running pipeline {i}/{count}: {theme}")
            print(f"{'='*60}")

            result = await self.run_pipeline(theme)
            results.append(result)

            # 結果をログに保存
            await self._save_to_log(result)

        return results

    # ==========================================
    # ユーティリティ
    # ==========================================

    def _extract_output(self, result: Dict) -> str:
        """エージェント結果からテキスト抽出"""
        if "error" in result:
            return f"Error: {result['error']}"

        try:
            if "artifacts" in result and result["artifacts"]:
                for artifact in result["artifacts"]:
                    for part in artifact.get("parts", []):
                        if part.get("text"):
                            return part["text"]

            if "status" in result and "message" in result["status"]:
                msg = result["status"]["message"]
                for part in msg.get("parts", []):
                    if part.get("text"):
                        return part["text"]
        except:
            pass

        return str(result)

    def _extract_score(self, review_text: str) -> int:
        """レビュー結果からスコア抽出"""
        import re

        # パターン: "XX/100" or "合計: XX" or "総合スコア: XX"
        patterns = [
            r"(\d+)\s*/\s*100",
            r"合計[:\s]*\*?\*?(\d+)",
            r"総合スコア[:\s]*(\d+)",
            r"Score[:\s]*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, review_text)
            if match:
                score = int(match.group(1))
                if 0 <= score <= 100:
                    return score

        return 0

    def _extract_themes(self, text: str) -> List[Dict]:
        """テーマリストを抽出"""
        import re

        # JSON抽出
        json_match = re.search(r'\{[\s\S]*"themes"[\s\S]*\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return data.get("themes", [])
            except:
                pass

        # フォールバック: 箇条書きからテーマ抽出
        themes = []
        for line in text.split("\n"):
            if line.strip().startswith(("1.", "2.", "3.", "-", "•")):
                theme = line.strip().lstrip("0123456789.-•) ").strip()
                if theme and len(theme) > 5:
                    themes.append({"theme": theme})

        return themes[:5]

    async def _save_to_log(self, result: PipelineResult):
        """結果をスプレッドシートに保存"""
        # ローカルログに保存
        log_dir = SNS_DIR / "logs"
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d')}.json"

        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except:
                pass

        logs.append(asdict(result))
        log_file.write_text(json.dumps(logs, ensure_ascii=False, indent=2))

        print(f"📝 Logged to: {log_file}")

    # ==========================================
    # バズ動画ベースパイプライン（Phase1 → Phase2連携）
    # ==========================================

    async def run_from_buzz(
        self,
        threshold: float = 5.0,
        days: int = 90,
        count: int = 1
    ) -> List[PipelineResult]:
        """
        バズ動画を検出 → トランスクリプト取得 → 台本生成

        フロー:
        1. ChannelManager.auto_discover_buzz() でバズ動画検出
        2. MCPでトランスクリプト取得
        3. Script Writer Agent に送信
        4. 台本生成パイプライン実行

        Args:
            threshold: PRしきい値（デフォルト5.0）
            days: 直近N日以内（デフォルト90日）
            count: 生成する台本数
        """
        print("\n" + "=" * 60)
        print("🔥 Buzz Video → Script Generation Pipeline")
        print("=" * 60)

        # Phase 1: バズ動画検出
        print("\n[Phase 1] Detecting buzz videos...")

        try:
            sys.path.insert(0, str(SCRIPT_DIR / "research"))
            from channel_manager import ChannelManager

            manager = ChannelManager()

            # データがなければ自動fetch
            videos = manager.load_videos()
            if not videos:
                print("  📡 No video data found. Fetching from YouTube API...")
                channels = manager.load_channels()
                if not channels:
                    print("  ❌ No channels registered. Add channels first:")
                    print("     python research/channel_manager.py add --channel \"チャンネル名\"")
                    return []

                # チャンネルIDがなければ解決
                needs_resolve = [c for c in channels if not c.channel_id]
                if needs_resolve:
                    print(f"  🔍 Resolving {len(needs_resolve)} channel IDs...")
                    manager.resolve_channel_ids()

                # 動画データをfetch
                print(f"  📥 Fetching videos from {len(channels)} channels...")
                manager.fetch_all_channels(top_n=20, force=True)
                videos = manager.load_videos()
                print(f"  ✅ Fetched {len(videos)} videos")

            discover_result = manager.auto_discover_buzz(
                threshold=threshold,
                min_views=10000,
                days=days
            )
        except Exception as e:
            print(f"❌ ChannelManager error: {e}")
            import traceback
            traceback.print_exc()
            return []

        buzz_videos = discover_result.get("buzz_videos", [])

        if not buzz_videos:
            print("❌ No buzz videos found with current threshold")
            print(f"  → Threshold: PR >= {threshold}x, Last {days} days")
            print("  → Try lowering threshold: --threshold 2.0")

            # しきい値を下げて再検索を提案
            lower_result = manager.find_outstanding_videos(threshold=2.0, min_views=1000)
            if lower_result:
                print(f"  💡 Found {len(lower_result)} videos with PR >= 2.0")
                print(f"     Top: {lower_result[0].title[:40]}... (PR: {lower_result[0].performance_ratio:.1f}x)")
            return []

        print(f"✅ Found {len(buzz_videos)} buzz videos")
        for i, v in enumerate(buzz_videos[:5], 1):
            print(f"  {i}. {v['title'][:40]}... (PR: {v['performance_ratio']}x)")

        # バズ動画検出通知用データを準備（MCPで送信）
        try:
            sys.path.insert(0, str(SNS_DIR / "_shared"))
            from mcp_email_sender import prepare_buzz_detection_email
            buzz_email = prepare_buzz_detection_email(buzz_videos, threshold)

            # メール送信用JSONを保存（Claude Codeが実行）
            email_json_file = OUTPUT_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_buzz_email.json"
            import json
            with open(email_json_file, 'w', encoding='utf-8') as f:
                json.dump(buzz_email['mcp_params'], f, ensure_ascii=False, indent=2)

            print(f"📧 バズ動画検出メール準備完了: {email_json_file.name}")
            print(f"   → MCP経由で送信してください")
        except Exception as e:
            print(f"⚠️ Email prep error: {e}")

        # Phase 2: トランスクリプト取得指示を生成
        print("\n[Phase 2] Generating transcript fetch instructions...")

        try:
            sys.path.insert(0, str(SNS_DIR / "_shared"))
            from buzz_to_script_pipeline import BuzzToScriptPipeline

            pipeline = BuzzToScriptPipeline()
            pipeline_info = pipeline.process_buzz_videos(buzz_videos)

            # 指示をファイルに保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            instructions_file = OUTPUT_DIR / f"{timestamp}_transcript_instructions.md"
            instructions_file.write_text(pipeline_info["transcript_instructions"], encoding="utf-8")
            print(f"✅ Instructions saved: {instructions_file.name}")

        except Exception as e:
            print(f"⚠️ Pipeline info error: {e}")
            pipeline_info = None

        # Phase 3: 各バズ動画から台本生成
        print("\n[Phase 3] Running script generation pipeline...")

        results = []
        for i, video in enumerate(buzz_videos[:count], 1):
            # バズ動画情報からテーマを生成
            video_title = video.get("title", "")
            channel_name = video.get("channel_name", "")
            pr = video.get("performance_ratio", 0)

            theme = f"「{video_title}」のような動画を作る"

            print(f"\n--- Pipeline {i}/{count}: {theme[:40]}... ---")

            # Script Writer に直接送信（トランスクリプト取得指示付き）
            script_prompt = f"""以下のバズ動画を参考に、同様のテーマで台本を作成してください。

## バズ動画情報
- タイトル: {video_title}
- チャンネル: {channel_name}
- PR (Performance Ratio): {pr:.1f}x
- URL: https://youtube.com/watch?v={video.get('video_id', '')}

## タスク
1. まず上記動画のトランスクリプトをMCPで取得してください:
```
mcp__klavis-strata__execute_action(
    server_name="youtube",
    category_name="YOUTUBE_TRANSCRIPT",
    action_name="get_youtube_video_transcript",
    body_schema='{{"url": "https://youtube.com/watch?v={video.get('video_id', '')}"}}'
)
```

2. トランスクリプトを分析し、構成パターンを抽出

3. 成功要因を特定

4. 同様のテーマ・構成で、オリジナルの台本を作成
   - PASTOR + AREA構成を使用
   - 自分の視点・経験を入れる
   - 差別化ポイントを明確に
"""

            script_result = await self.call_agent("script_writer", script_prompt)
            script_output = self._extract_output(script_result)

            # 保存
            safe_title = video_title.replace("/", "_").replace(" ", "_")[:30]
            script_file = SCRIPTS_DIR / f"{timestamp}_{safe_title}_buzz_script.md"
            script_file.write_text(f"# バズ動画参考台本\n\n## 元動画\n- {video_title}\n- PR: {pr}x\n\n## 生成台本\n{script_output}", encoding="utf-8")

            print(f"✅ Script saved: {script_file.name}")

            # 台本完成通知 + Google Docs作成用データを準備（MCPで実行）
            try:
                from mcp_email_sender import prepare_script_with_doc_and_email
                output_data = prepare_script_with_doc_and_email(
                    theme=theme,
                    score=0,  # レビュー未実施
                    output_file=str(script_file),
                    buzz_video=video
                )

                # 統合JSONを保存（Google Docs + メール）
                mcp_json_file = OUTPUT_DIR / f"{timestamp}_{safe_title}_mcp.json"
                with open(mcp_json_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "google_doc": output_data['google_doc']['mcp_params'],
                        "email": output_data['email']['mcp_params']
                    }, f, ensure_ascii=False, indent=2)

                print(f"📄 Google Docs + メール準備完了: {mcp_json_file.name}")
            except Exception as notify_err:
                print(f"⚠️ 出力準備エラー: {notify_err}")

            # 結果を追加
            results.append(PipelineResult(
                theme=theme,
                status="success",
                final_score=0,  # レビュー未実施
                iterations=1,
                started_at=datetime.now().isoformat(),
                completed_at=datetime.now().isoformat(),
                output_files={"script": str(script_file)}
            ))

        print("\n" + "=" * 60)
        print(f"✅ Buzz Pipeline Complete: {len(results)} scripts generated")
        print("=" * 60)

        return results


# ==========================================
# CLI
# ==========================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Pipeline Runner")
    parser.add_argument("command", choices=["run", "auto", "check", "buzz"],
                       help="run: 指定テーマで実行, auto: 自動テーマ生成, buzz: バズ動画→台本, check: エージェント確認")
    parser.add_argument("--theme", "-t", help="動画テーマ（runコマンド用）")
    parser.add_argument("--count", "-n", type=int, default=1, help="生成台本数")
    parser.add_argument("--hint", "-H", help="テーマ生成ヒント（autoコマンド用）")
    parser.add_argument("--threshold", "-T", type=float, default=5.0, help="PRしきい値（buzzコマンド用）")
    parser.add_argument("--days", "-d", type=int, default=90, help="直近N日以内（buzzコマンド用）")
    args = parser.parse_args()

    runner = PipelineRunner()

    try:
        if args.command == "check":
            print("🔍 Checking agent status...")
            status = await runner.check_agents()
            print("\nPhase 1 - Data Collection:")
            for name in ["channel_monitor", "video_collector", "trend_analyzer"]:
                if name in status:
                    icon = "✅" if status[name] else "❌"
                    print(f"  {icon} {name}: {'Running' if status[name] else 'Not Running'}")
            print("\nPhase 2 - Script Generation:")
            for name in ["coordinator", "research", "hook", "concept", "reviewer", "improver", "script_writer"]:
                if name in status:
                    icon = "✅" if status[name] else "❌"
                    print(f"  {icon} {name}: {'Running' if status[name] else 'Not Running'}")

        elif args.command == "run":
            if not args.theme:
                print("❌ Please specify theme with --theme")
                return

            result = await runner.run_pipeline(args.theme)
            print(f"\nResult: {result.status}")
            print(f"Final Score: {result.final_score}")
            print(f"Output: {result.output_files.get('final', 'N/A')}")

        elif args.command == "auto":
            results = await runner.run_from_channels(
                theme_prompt=args.hint,
                count=args.count
            )

            print(f"\n{'='*60}")
            print(f"📊 Summary: {len(results)} pipelines completed")
            for r in results:
                status_icon = "✅" if r.status == "success" else "⚠️"
                print(f"  {status_icon} {r.theme[:30]}... → {r.final_score}/100")

        elif args.command == "buzz":
            print("🔥 Running Buzz Video → Script Generation Pipeline")
            print(f"   Threshold: PR >= {args.threshold}x")
            print(f"   Period: Last {args.days} days")
            print(f"   Scripts: {args.count}")

            results = await runner.run_from_buzz(
                threshold=args.threshold,
                days=args.days,
                count=args.count
            )

            print(f"\n{'='*60}")
            print(f"📊 Summary: {len(results)} scripts generated from buzz videos")
            for r in results:
                print(f"  ✅ {r.theme[:40]}...")
                if r.output_files.get("script"):
                    print(f"     → {Path(r.output_files['script']).name}")

    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
