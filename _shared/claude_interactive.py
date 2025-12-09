"""
Claude Code 対話モード自動操作
pexpectを使ってフル機能のClaude Codeを操作
"""

import pexpect
import time
import re
import os
import sys


class ClaudeInteractive:
    """Claude Code対話モードを自動操作"""

    def __init__(self, workspace: str = ".", timeout: int = 300, debug: bool = False):
        self.workspace = workspace
        self.timeout = timeout
        self.child = None
        self.ready = False
        self.debug = debug

    def _log(self, msg: str):
        if self.debug:
            print(f"[DEBUG] {msg}")

    def start(self) -> bool:
        """Claude Code起動"""
        try:
            self.child = pexpect.spawn(
                'claude',
                cwd=self.workspace,
                timeout=self.timeout,
                encoding='utf-8',
                maxread=200000,
                dimensions=(50, 200)
            )

            self._log("Claude Code起動待ち...")
            time.sleep(3)

            # 起動時のダイアログをすべて処理
            self._handle_all_dialogs()

            self.ready = True
            return True

        except Exception as e:
            print(f"起動エラー: {e}")
            return False

    def _handle_all_dialogs(self):
        """すべてのダイアログを処理して入力可能状態にする"""
        for attempt in range(10):
            try:
                output = self.child.read_nonblocking(size=50000, timeout=2)
                self._log(f"起動出力確認 ({attempt+1}回目)")

                if 'MCP server' in output or 'Enter to confirm' in output or '❯' in output:
                    self._log("ダイアログ → Enter")
                    self.child.sendline('')
                    time.sleep(2)
                    continue

            except pexpect.TIMEOUT:
                self._log("入力可能状態")
                break

        time.sleep(1)
        try:
            self.child.read_nonblocking(size=100000, timeout=1)
        except:
            pass

    def send(self, message: str, wait_time: int = 60) -> str:
        """メッセージを送信して応答を取得"""
        if not self.child or not self.ready:
            return "Error: Claude Code not started"

        try:
            self._log(f"送信: {message}")
            self.child.sendline(message)

            # 応答収集（十分待つ）
            output = ""
            start_time = time.time()
            no_output_count = 0

            # 最初は長めに待つ
            time.sleep(3)

            while time.time() - start_time < wait_time:
                try:
                    chunk = self.child.read_nonblocking(size=20000, timeout=3)
                    if chunk:
                        output += chunk
                        no_output_count = 0
                        self._log(f"出力受信: {len(chunk)}文字")

                        # ダイアログ処理
                        if 'Enter to confirm' in chunk:
                            self.child.sendline('')
                        elif 'y/n' in chunk.lower():
                            self.child.sendline('y')

                except pexpect.TIMEOUT:
                    no_output_count += 1
                    self._log(f"タイムアウト ({no_output_count})")

                    # 出力があった後で3秒以上新出力がなければ完了
                    if output and no_output_count >= 2:
                        self._log("応答完了と判断")
                        break

            # 結果整形
            result = self._clean_output(output)

            # 送信メッセージ除去
            if message in result:
                result = result.split(message, 1)[-1]

            return result.strip()

        except Exception as e:
            return f"Error: {str(e)}"

    def execute_slash_command(self, command: str, wait_time: int = 120) -> str:
        """スラッシュコマンドを実行"""
        return self.send(command, wait_time=wait_time)

    def _clean_output(self, text: str) -> str:
        """出力をクリーンアップ"""
        text = re.sub(r'\x1B\[[0-9;]*[a-zA-Z]', '', text)
        text = re.sub(r'\x1B\][^\x07]*\x07', '', text)
        text = re.sub(r'\x1B\]8;;[^\x1B]*\x1B\\', '', text)
        text = re.sub(r'\[\?[0-9]+[hl]', '', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        text = re.sub(r'[╭╮╰╯│─]+', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def stop(self):
        """Claude Code終了"""
        if self.child:
            try:
                self.child.sendline('/exit')
                time.sleep(2)
                self.child.terminate(force=True)
            except:
                pass
            self.child = None
            self.ready = False


if __name__ == "__main__":
    print("=" * 60)
    print("Claude Code 対話モードテスト")
    print("=" * 60)

    workspace = "/Users/tonodukaren/Programming/AI/02_Workspace/03_Markx/40_dev/A2A/SNS"
    claude = ClaudeInteractive(workspace=workspace, debug=True)

    print("\n[1] 起動")
    if claude.start():
        print("  ✓ 起動成功\n")

        print("[2] テスト送信")
        print("-" * 40)
        result = claude.send("3+5は？", wait_time=45)
        print("-" * 40)
        print(f"\n【応答】\n{result}\n")

        print("[3] 終了")
        claude.stop()
        print("  ✓ 終了")

    print("=" * 60)
