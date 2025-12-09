"""
YouTube A2A Agents テストスクリプト
"""

import asyncio
import httpx
import json

BASE_URLS = {
    "coordinator": "http://localhost:8100",
    "research": "http://localhost:8101",
    "hook": "http://localhost:8102",
    "concept": "http://localhost:8103",
    "reviewer": "http://localhost:8104",
    "improver": "http://localhost:8105",
}


async def test_agent_card(name: str, url: str):
    """Agent Cardを取得してテスト"""
    print(f"\n{'='*50}")
    print(f"Testing: {name}")
    print(f"{'='*50}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{url}/.well-known/agent.json")
            response.raise_for_status()
            card = response.json()

            print(f"✅ Agent Card Retrieved")
            print(f"   Name: {card.get('name')}")
            print(f"   Description: {card.get('description')[:50]}...")
            print(f"   Skills: {len(card.get('skills', []))} skills")

            return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


async def test_send_task(name: str, url: str, message: str):
    """タスクを送信してテスト"""
    print(f"\n{'='*50}")
    print(f"Testing Task: {name}")
    print(f"{'='*50}")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            payload = {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message}]
                }
            }

            print(f"📤 Sending task to {url}...")
            response = await client.post(
                f"{url}/a2a/tasks/send",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            print(f"✅ Task Completed")
            print(f"   Task ID: {result.get('id')}")
            print(f"   Status: {result.get('status', {}).get('state')}")

            # Artifactを表示
            artifacts = result.get('artifacts', [])
            if artifacts:
                for artifact in artifacts:
                    for part in artifact.get('parts', []):
                        if part.get('text'):
                            output = part['text'][:500]
                            print(f"   Output: {output}...")

            return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


async def main():
    print("="*60)
    print("🎬 YouTube A2A Agents Test Suite")
    print("="*60)

    # 1. Agent Card テスト
    print("\n📋 Phase 1: Agent Card Tests")
    results = {}
    for name, url in BASE_URLS.items():
        results[name] = await test_agent_card(name, url)

    # 結果サマリー
    print("\n" + "="*60)
    print("Agent Card Test Results:")
    for name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {name}")

    # 2. タスク送信テスト（Research Agentのみ）
    print("\n📋 Phase 2: Task Execution Test")
    if results.get("research"):
        await test_send_task(
            "research",
            BASE_URLS["research"],
            "AIエージェント というテーマで競合動画を分析してください。簡潔に3つのポイントだけ教えてください。"
        )

    print("\n" + "="*60)
    print("✅ Test Suite Completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
