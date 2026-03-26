import asyncio
from services.browser_agent import run_browser_analysis

async def main():
    result = await run_browser_analysis(
        session_id="test-session-123",
        competitor={"name": "Linear", "url": "https://linear.app"}
    )
    print("\n=== RESULT ===")
    print(f"Steps taken: {result['steps_taken']}")
    print(f"Browser analyzed: {result['is_browser_analyzed']}")
    print(f"\nFindings:\n{result['browser_findings']}")

asyncio.run(main())