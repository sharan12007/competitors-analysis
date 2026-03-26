"""
Run this to inspect the exact browser-use API on your machine.
python inspect_browser_use.py
"""
import inspect
import sys
import pathlib
import site

print(f"Python: {sys.version}")

try:
    from importlib.metadata import version
    print(f"browser-use version: {version('browser-use')}")
except Exception as e:
    print(f"Could not read version: {e}")

try:
    from browser_use import Agent
    sig = inspect.signature(Agent.__init__)
    print(f"\nAgent.__init__ parameters:")
    for name, param in sig.parameters.items():
        print(f"  {name}: default={param.default if param.default != inspect.Parameter.empty else 'REQUIRED'}")
except Exception as e:
    print(f"Agent inspect error: {e}")

try:
    from browser_use.browser.browser import Browser, BrowserConfig
    sig = inspect.signature(BrowserConfig.__init__)
    print(f"\nBrowserConfig parameters:")
    for name, param in sig.parameters.items():
        print(f"  {name}: default={param.default if param.default != inspect.Parameter.empty else 'REQUIRED'}")
except Exception as e:
    print(f"BrowserConfig inspect error: {e}")

print("\n--- Scanning agent/service.py for callback/step lines ---")
for sp in site.getsitepackages():
    for candidate in ["service.py", "agent.py"]:
        agent_path = pathlib.Path(sp) / "browser_use" / "agent" / candidate
        if agent_path.exists():
            print(f"Found: {agent_path}")
            src = agent_path.read_text(encoding="utf-8")
            for i, line in enumerate(src.splitlines()):
                low = line.lower()
                if any(k in low for k in ["callback", "on_step", "register", "new_step"]):
                    print(f"  line {i+1}: {line.rstrip()}")
            break