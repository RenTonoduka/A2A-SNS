#!/usr/bin/env python3
"""
Data Collection Pipeline Runner - Phase 1
チャンネル監視 → 動画収集 → トレンド分析 の自動実行
"""

import json
import time
import argparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime
from pathlib import Path


class DataCollectionRunner:
    """Phase 1: データ収集パイプライン"""

    def __init__(self, timeout: int = 600):
        self.timeout = timeout
        self.agents = {
            "channel_monitor": "http://localhost:8110",
            "video_collector": "http://localhost:8111",
            "trend_analyzer": "http://localhost:8112",
        }
        self.output_dir = Path(__file__).parent / "research" / "data"
        self.report_dir = Path(__file__).parent / "output" / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def check_agent(self, name: str, url: str) -> bool:
        """エージェントの稼働確認"""
        try:
            req = Request(f"{url}/.well-known/agent.json")
            with urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    def check_all_agents(self) -> dict:
        """全エージェントの状態確認"""
        status = {}
        for name, url in self.agents.items():
            status[name] = self.check_agent(name, url)
        return status

    def send_task(self, agent_name: str, message: str) -> dict:
        """エージェントにタスクを送信"""
        url = self.agents.get(agent_name)
        if not url:
            return {"error": f"Unknown agent: {agent_name}"}

        task_data = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message}]
                }
            },
            "id": f"{agent_name}-{int(time.time())}"
        }

        try:
            req = Request(
                f"{url}/a2a",
                data=json.dumps(task_data).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            return {"error": f"HTTP Error: {e.code}"}
        except URLError as e:
            return {"error": f"URL Error: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    def run_channel_monitor(self) -> dict:
        """Step 1: チャンネル監視"""
        print("\n" + "=" * 60)
        print("📡 Step 1: Channel Monitor")
        print("=" * 60)

        message = """
channels.csvの全チャンネルを確認し、以下を実行してください：

1. 各チャンネルの最新状態を取得（登録者数、動画数）
2. 前回取得時からの変化を記録
3. 新着動画があるチャンネルをリストアップ
4. channels.csvのlast_fetched, subscriber_count, video_countを更新

最後に、新着動画があったチャンネル一覧を出力してください。
"""
        result = self.send_task("channel_monitor", message)
        return result

    def run_video_collector(self, channels_with_new_videos: str = None) -> dict:
        """Step 2: 動画収集"""
        print("\n" + "=" * 60)
        print("📹 Step 2: Video Collector")
        print("=" * 60)

        if channels_with_new_videos:
            message = f"""
以下のチャンネルから新着動画を収集してください：

{channels_with_new_videos}

実行内容：
1. 各チャンネルの新着動画情報を取得
2. videos.csvに新規追加
3. performance_ratio を計算
4. 既存動画の統計も更新（再生数の変化等）

収集した動画の一覧と、特にPR >= 2.0の動画を報告してください。
"""
        else:
            message = """
channels.csvの全チャンネルから最新動画を収集してください：

1. 各チャンネルの最新10件の動画情報を取得
2. videos.csvに存在しない動画を追加
3. performance_ratio を計算
4. 既存動画の統計も更新

収集結果とバズ動画（PR >= 2.0）を報告してください。
"""
        result = self.send_task("video_collector", message)
        return result

    def run_trend_analyzer(self) -> dict:
        """Step 3: トレンド分析"""
        print("\n" + "=" * 60)
        print("📊 Step 3: Trend Analyzer")
        print("=" * 60)

        message = """
videos.csvのデータを分析し、トレンドレポートを生成してください：

1. バズ動画ランキング（PR >= 2.0）
2. トレンドキーワード抽出
3. タイトルパターン分析
4. 投稿タイミング分析
5. 台本生成への推奨テーマ提案

分析結果を詳細なレポート形式で出力してください。
"""
        result = self.send_task("trend_analyzer", message)
        return result

    def save_report(self, report: dict, report_type: str):
        """レポートをファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{report_type}.json"
        filepath = self.report_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"📄 Report saved: {filepath}")
        return filepath

    def run_full_pipeline(self):
        """フルパイプライン実行"""
        print("\n" + "=" * 60)
        print("🚀 DATA COLLECTION PIPELINE - Phase 1")
        print("=" * 60)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # エージェント稼働確認
        status = self.check_all_agents()
        print("\nAgent Status:")
        all_ready = True
        for name, is_up in status.items():
            icon = "✅" if is_up else "❌"
            print(f"  {icon} {name}: {'Running' if is_up else 'Not Running'}")
            if not is_up:
                all_ready = False

        if not all_ready:
            print("\n⚠️ Some agents are not running!")
            print("Start agents with: ./start_phase1_agents.sh")
            return

        results = {}

        # Step 1: Channel Monitor
        results["channel_monitor"] = self.run_channel_monitor()

        # Step 2: Video Collector
        results["video_collector"] = self.run_video_collector()

        # Step 3: Trend Analyzer
        results["trend_analyzer"] = self.run_trend_analyzer()

        # レポート保存
        self.save_report(results, "data_collection")

        print("\n" + "=" * 60)
        print("✅ DATA COLLECTION COMPLETE")
        print("=" * 60)
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Reports: {self.report_dir}")

        return results

    def run_quick_check(self):
        """クイックチェック（チャンネル監視のみ）"""
        print("\n" + "=" * 60)
        print("🔍 QUICK CHECK - Channel Monitor Only")
        print("=" * 60)

        status = self.check_agent("channel_monitor", self.agents["channel_monitor"])
        if not status:
            print("❌ Channel Monitor is not running!")
            return

        result = self.run_channel_monitor()
        self.save_report({"channel_monitor": result}, "quick_check")
        return result

    def run_trend_only(self):
        """トレンド分析のみ実行"""
        print("\n" + "=" * 60)
        print("📊 TREND ANALYSIS ONLY")
        print("=" * 60)

        status = self.check_agent("trend_analyzer", self.agents["trend_analyzer"])
        if not status:
            print("❌ Trend Analyzer is not running!")
            return

        result = self.run_trend_analyzer()
        self.save_report({"trend_analyzer": result}, "trend_analysis")
        return result


def main():
    parser = argparse.ArgumentParser(description="Data Collection Pipeline Runner")
    parser.add_argument(
        "command",
        choices=["run", "check", "monitor", "collect", "analyze", "status"],
        help="Command to execute"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds (default: 600)"
    )

    args = parser.parse_args()
    runner = DataCollectionRunner(timeout=args.timeout)

    if args.command == "run":
        # フルパイプライン
        runner.run_full_pipeline()
    elif args.command == "check" or args.command == "status":
        # 状態確認
        status = runner.check_all_agents()
        print("\nPhase 1 Agent Status:")
        for name, is_up in status.items():
            icon = "✅" if is_up else "❌"
            print(f"  {icon} {name}: {'Running' if is_up else 'Not Running'}")
    elif args.command == "monitor":
        # チャンネル監視のみ
        runner.run_quick_check()
    elif args.command == "collect":
        # 動画収集のみ
        status = runner.check_agent("video_collector", runner.agents["video_collector"])
        if status:
            result = runner.run_video_collector()
            runner.save_report({"video_collector": result}, "video_collection")
        else:
            print("❌ Video Collector is not running!")
    elif args.command == "analyze":
        # トレンド分析のみ
        runner.run_trend_only()


if __name__ == "__main__":
    main()
