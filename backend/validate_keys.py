"""
Phase 1 — API Key Validation Script
Run this ONCE to confirm all keys are live before building any logic.
Usage (Windows):  python validate_keys.py
"""

import os
import sys
from dotenv import load_dotenv

# Load .env from parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
TAVILY_API_KEY   = os.getenv("TAVILY_API_KEY", "")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
GITHUB_TOKEN     = os.getenv("GITHUB_TOKEN", "")

results = {}

# ── 1. Groq ──────────────────────────────────────────────────────────────────
print("\n[1/4] Validating Groq API key...")
try:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Say: OK"}],
        max_tokens=5,
    )
    text = resp.choices[0].message.content.strip()
    print(f"  ✅ Groq OK — response: '{text}'")
    results["groq"] = True
except Exception as e:
    print(f"  ❌ Groq FAILED: {e}")
    results["groq"] = False

# ── 2. Tavily ────────────────────────────────────────────────────────────────
print("\n[2/4] Validating Tavily API key...")
try:
    from tavily import TavilyClient
    tc = TavilyClient(api_key=TAVILY_API_KEY)
    res = tc.search("test query", max_results=1)
    count = len(res.get("results", []))
    print(f"  ✅ Tavily OK — got {count} result(s)")
    results["tavily"] = True
except Exception as e:
    print(f"  ❌ Tavily FAILED: {e}")
    results["tavily"] = False

# ── 3. Firecrawl ─────────────────────────────────────────────────────────────
print("\n[3/4] Validating Firecrawl API key...")
try:
    import httpx
    r = httpx.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}"},
        json={"url": "https://example.com", "formats": ["markdown"]},
        timeout=15,
    )
    if r.status_code == 200 and r.json().get("success"):
        md_len = len(r.json().get("data", {}).get("markdown", ""))
        print(f"  ✅ Firecrawl OK — got {md_len} chars of markdown")
        results["firecrawl"] = True
    else:
        print(f"  ❌ Firecrawl returned {r.status_code}: {r.text[:200]}")
        results["firecrawl"] = False
except Exception as e:
    print(f"  ❌ Firecrawl FAILED: {e}")
    results["firecrawl"] = False

# ── 4. GitHub ────────────────────────────────────────────────────────────────
print("\n[4/4] Validating GitHub token...")
try:
    from github import Github
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo("openai/openai-python")
    stars = repo.stargazers_count
    print(f"  ✅ GitHub OK — openai/openai-python has {stars:,} stars")
    results["github"] = True
except Exception as e:
    print(f"  ❌ GitHub FAILED: {e}")
    results["github"] = False

# ── Summary ──────────────────────────────────────────────────────────────────
print("\n" + "─" * 50)
all_pass = all(results.values())
for k, v in results.items():
    status = "✅ PASS" if v else "❌ FAIL"
    print(f"  {status}  {k.upper()}")
print("─" * 50)

if all_pass:
    print("\n🎉 ALL KEYS VALID — proceed to Phase 2\n")
    sys.exit(0)
else:
    failed = [k for k, v in results.items() if not v]
    print(f"\n🚫 Fix these keys before continuing: {', '.join(failed)}\n")
    sys.exit(1)