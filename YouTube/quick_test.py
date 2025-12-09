"""
クイックテスト - 単一エージェント呼び出し確認
"""
import urllib.request
import json

def test_agent(port, name):
    """エージェントを単純テスト"""
    print(f"\n🔍 Testing {name} (port {port})...")

    # 1. Agent Card取得
    try:
        req = urllib.request.Request(f"http://localhost:{port}/.well-known/agent.json")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"  ✅ Agent Card OK: {data.get('name', 'N/A')}")
    except Exception as e:
        print(f"  ❌ Agent Card Error: {e}")
        return False

    # 2. 簡単なメッセージ送信
    try:
        payload = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "ping"}]
            }
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"http://localhost:{port}/a2a/tasks/send",
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            state = result.get("status", {}).get("state", "unknown")
            print(f"  ✅ Response OK: state={state}")
            return True
    except Exception as e:
        print(f"  ❌ Response Error: {e}")
        return False


if __name__ == "__main__":
    agents = [
        (8100, "Coordinator"),
        (8101, "Research"),
        (8102, "Hook"),
        (8103, "Concept"),
        (8104, "Reviewer"),
        (8105, "Improver"),
    ]

    print("=" * 50)
    print("🧪 Quick Agent Test")
    print("=" * 50)

    results = {}
    for port, name in agents:
        results[name] = test_agent(port, name)

    print("\n" + "=" * 50)
    print("📊 Results:")
    for name, ok in results.items():
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}")
