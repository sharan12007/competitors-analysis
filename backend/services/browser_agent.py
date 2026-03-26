import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse

from config import settings
from sse import broadcast
from services.llm_client import ask as llm_ask

logger = logging.getLogger(__name__)

PAGE_TARGETS = {
    "pricing": ["/pricing", "/plans"],
    "features": ["/features", "/product", "/platform"],
    "integrations": ["/integrations", "/integration", "/apps"],
    "customers": ["/customers", "/case-studies", "/customer-stories"],
    "security": ["/security", "/trust", "/enterprise"],
}

PAGE_KEYWORDS = {
    "pricing": ("pricing", "plans", "plan", "billing"),
    "features": ("features", "product", "platform", "solutions", "capabilities"),
    "integrations": ("integrations", "integration", "apps", "ecosystem", "marketplace"),
    "customers": ("customers", "case studies", "stories", "testimonials", "success"),
    "security": ("security", "trust", "enterprise", "compliance", "privacy"),
}


def _extract_page_text(page, max_chars: int = 7000) -> str:
    try:
        text = page.locator("body").inner_text(timeout=8000) or ""
        return " ".join(text.split())[:max_chars]
    except Exception:
        return ""


def _extract_section(text: str, label: str) -> str:
    pattern = rf"{re.escape(label)}\s*(.*?)(?=\n[A-Za-z /]+?:|\Z)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return " ".join(match.group(1).strip().split())


def _extract_feature_list(text: str) -> list[str]:
    raw = _extract_section(text, "Key Features:")
    if not raw:
        return []
    parts = re.split(r"[,\n]|(?:\s-\s)|(?:\s•\s)", raw)
    cleaned = []
    for part in parts:
        item = part.strip(" -•\t\r\n")
        if item and item.lower() not in {"key features:", "none"}:
            cleaned.append(item)
    return cleaned[:5]


def _derive_pricing_model(pricing_text: str) -> str:
    lowered = pricing_text.lower()
    if any(word in lowered for word in ["free", "freemium"]):
        return "freemium"
    if any(word in lowered for word in ["custom", "contact sales", "enterprise"]):
        return "custom"
    if pricing_text and pricing_text.lower() != "not found":
        return "paid"
    return "unknown"


def _looks_like_real_page(title: str, text: str) -> bool:
    title_l = (title or "").lower()
    text_l = (text or "").lower()
    bad_markers = ["404", "not found", "page not found", "error", "access denied"]
    return bool(text.strip()) and not any(marker in title_l or marker in text_l[:220] for marker in bad_markers)


def _is_same_domain(base_url: str, candidate_url: str) -> bool:
    base_host = (urlparse(base_url).netloc or "").lower().replace("www.", "")
    candidate_host = (urlparse(candidate_url).netloc or "").lower().replace("www.", "")
    return bool(base_host) and base_host == candidate_host


def _score_link(label: str, href: str, text: str) -> int:
    haystack = f"{href} {text}".lower()
    return sum(1 for keyword in PAGE_KEYWORDS[label] if keyword in haystack)


def _discover_candidate_links(page, base_url: str) -> list[dict]:
    discovered = []
    seen = set()

    try:
        anchors = page.locator("a[href]")
        count = min(anchors.count(), 120)
    except Exception:
        count = 0
        anchors = None

    for index in range(count):
        try:
            anchor = anchors.nth(index)
            href = anchor.get_attribute("href") or ""
            text = (anchor.inner_text(timeout=1000) or "").strip()
            if not href:
                continue

            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)

            if parsed.scheme not in ("http", "https"):
                continue
            if not _is_same_domain(base_url, absolute_url):
                continue
            if absolute_url in seen:
                continue
            if any(fragment in absolute_url.lower() for fragment in ("#", "mailto:", "tel:")):
                continue

            seen.add(absolute_url)
            discovered.append({
                "url": absolute_url,
                "text": text,
            })
        except Exception:
            continue

    return discovered


def _pick_dynamic_targets(base_url: str, discovered_links: list[dict]) -> dict[str, str]:
    chosen: dict[str, str] = {}

    for label in PAGE_TARGETS:
        best_url = ""
        best_score = 0

        for item in discovered_links:
            score = _score_link(label, item["url"], item["text"])
            if score > best_score:
                best_score = score
                best_url = item["url"]

        if best_url:
            chosen[label] = best_url

    for label, paths in PAGE_TARGETS.items():
        if label in chosen:
            continue
        for path in paths:
            chosen[label] = urljoin(base_url, path)
            break

    return chosen


def _discover_second_layer_links(page, base_url: str, label: str) -> list[str]:
    relevant = []
    for item in _discover_candidate_links(page, base_url):
        if _score_link(label, item["url"], item["text"]) > 0:
            relevant.append(item["url"])
        if len(relevant) >= 2:
            break
    return relevant


def _visible_scroll(page, headless: bool) -> None:
    if headless:
        return
    try:
        page.mouse.wheel(0, 700)
        page.wait_for_timeout(900)
        page.mouse.wheel(0, 700)
        page.wait_for_timeout(900)
        page.mouse.wheel(0, -900)
        page.wait_for_timeout(700)
    except Exception:
        return


def _highlight_matching_link(page, target_url: str, headless: bool) -> bool:
    if headless:
        return False

    try:
        escaped_url = target_url.replace("\\", "\\\\").replace("'", "\\'")
        result = page.evaluate(
            f"""
            (() => {{
              const target = '{escaped_url}';
              const links = Array.from(document.querySelectorAll('a[href]'));
              const match = links.find((link) => link.href === target);
              if (!match) return false;
              match.scrollIntoView({{ behavior: 'instant', block: 'center' }});
              const previousOutline = match.style.outline;
              const previousOffset = match.style.outlineOffset;
              match.style.outline = '3px solid #ff7b57';
              match.style.outlineOffset = '4px';
              setTimeout(() => {{
                match.style.outline = previousOutline;
                match.style.outlineOffset = previousOffset;
              }}, 1200);
              return true;
            }})()
            """
        )
        if result:
            page.wait_for_timeout(1400)
            return True
    except Exception:
        pass

    return False


def _run_sync_browser_analysis(competitor_url: str, headless: bool) -> dict:
    from playwright.sync_api import sync_playwright

    steps = []
    pages = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=700 if not headless else 0,
            args=["--disable-web-security", "--no-sandbox", "--disable-dev-shm-usage"],
        )
        browser_label = "Playwright Chromium"

        page = browser.new_page()
        page.set_viewport_size({"width": 1440, "height": 1200})

        steps.append({"action": f"Opened {browser_label} browser", "url": ""})

        page.goto(competitor_url, wait_until="domcontentloaded", timeout=30000)
        homepage_title = page.title()
        homepage_text = _extract_page_text(page, max_chars=9000)
        pages["homepage"] = {
            "title": homepage_title,
            "url": page.url,
            "text": homepage_text,
        }
        steps.append({"action": f"Loaded homepage: {homepage_title}", "url": page.url})
        if not headless:
            page.wait_for_timeout(3500)
            _visible_scroll(page, headless)

        discovered_links = _discover_candidate_links(page, page.url)
        steps.append({"action": f"Discovered {len(discovered_links)} internal links on homepage", "url": page.url})

        target_urls = _pick_dynamic_targets(page.url, discovered_links)

        for label, candidate_url in target_urls.items():
            try:
                if _highlight_matching_link(page, candidate_url, headless):
                    steps.append({"action": f"Highlighted discovered {label} link before navigation", "url": candidate_url})

                page.goto(candidate_url, wait_until="domcontentloaded", timeout=18000)
                current_title = page.title()
                current_text = _extract_page_text(page, max_chars=7000)

                if not _looks_like_real_page(current_title, current_text):
                    continue

                pages[label] = {
                    "title": current_title,
                    "url": page.url,
                    "text": current_text,
                }
                steps.append({"action": f"Opened {label} page: {current_title}", "url": page.url})
                if not headless:
                    page.wait_for_timeout(2500)
                    _visible_scroll(page, headless)

                second_layer = _discover_second_layer_links(page, page.url, label)
                for nested_url in second_layer:
                    if nested_url == page.url:
                        continue
                    try:
                        if _highlight_matching_link(page, nested_url, headless):
                            steps.append({"action": f"Highlighted {label} detail link before navigation", "url": nested_url})

                        page.goto(nested_url, wait_until="domcontentloaded", timeout=15000)
                        nested_title = page.title()
                        nested_text = _extract_page_text(page, max_chars=5000)
                        if _looks_like_real_page(nested_title, nested_text):
                            pages[f"{label}_detail"] = {
                                "title": nested_title,
                                "url": page.url,
                                "text": nested_text,
                            }
                            steps.append({"action": f"Explored {label} detail page: {nested_title}", "url": page.url})
                            if not headless:
                                page.wait_for_timeout(1800)
                                _visible_scroll(page, headless)
                            break
                    except Exception:
                        continue

            except Exception:
                continue

        if not headless:
            page.wait_for_timeout(3500)

        browser.close()

    return {
        "pages": pages,
        "steps": steps,
    }


async def run_browser_analysis(session_id: str, competitor: dict) -> dict:
    competitor_name = competitor.get("name", "Unknown")
    competitor_url = competitor.get("url", "")

    if competitor_url and not competitor_url.startswith("http"):
        competitor_url = "https://" + competitor_url

    await broadcast(session_id, "browser_start", {
        "competitor": competitor_name,
        "url": competitor_url,
    })
    await broadcast(session_id, "browser_step", {
        "step": 1,
        "action": "Launching browser for live site analysis",
        "url": competitor_url,
        "screenshot_b64": None,
    })

    try:
        raw = await asyncio.to_thread(
            _run_sync_browser_analysis,
            competitor_url,
            settings.BROWSER_HEADLESS,
        )
    except Exception as e:
        logger.error(f"[browser_agent] Browser launch failed for {competitor_name}: {e}", exc_info=True)
        await broadcast(session_id, "browser_timeout", {
            "competitor": competitor_name,
            "partial_findings": f"Browser agent error: {str(e)}",
        })
        return _fallback(competitor_name, competitor_url, str(e))

    step_counter = 0
    for idx, step in enumerate(raw.get("steps", []), start=1):
        step_counter = idx
        await broadcast(session_id, "browser_step", {
            "step": idx,
            "action": step.get("action", f"Step {idx}"),
            "url": step.get("url", "")[:160],
            "screenshot_b64": None,
        })

    pages = raw.get("pages", {})
    homepage = pages.get("homepage", {})
    pricing = pages.get("pricing", {})
    features_page = pages.get("features", {})
    integrations_page = pages.get("integrations", {})
    customers_page = pages.get("customers", {})
    security_page = pages.get("security", {})

    homepage_text = homepage.get("text", "")
    pricing_text = pricing.get("text", "")

    if not homepage_text:
        error_text = "Browser agent could not read the competitor homepage."
        logger.warning(f"[browser_agent] {error_text} Competitor={competitor_name}")
        await broadcast(session_id, "browser_timeout", {
            "competitor": competitor_name,
            "partial_findings": error_text,
        })
        return _fallback(competitor_name, competitor_url, error_text)

    extra_context = []
    for key in ("pricing_detail", "features_detail", "integrations_detail", "customers_detail", "security_detail"):
        page_info = pages.get(key)
        if page_info:
            extra_context.append(f"{key.replace('_', ' ').title()} text:\n{page_info.get('text', '')}")

    extra_context_text = "\n\n".join(extra_context) if extra_context else "No extra detail pages captured."

    prompt = f"""You are summarizing a live browser visit for a competitor intelligence report.

Competitor: {competitor_name}
Homepage URL: {competitor_url}
Pricing URL: {pricing.get("url", "")}
Features URL: {features_page.get("url", "")}
Integrations URL: {integrations_page.get("url", "")}
Customers URL: {customers_page.get("url", "")}
Security URL: {security_page.get("url", "")}

Homepage title:
{homepage.get("title", "")}

Homepage text:
{homepage_text}

Pricing text:
{pricing_text or "No pricing page text captured."}

Features / product text:
{features_page.get("text", "") or "No dedicated features page captured."}

Integrations text:
{integrations_page.get("text", "") or "No integrations page captured."}

Customer / trust text:
{customers_page.get("text", "") or "No customer stories page captured."}

Security / enterprise text:
{security_page.get("text", "") or "No security or trust page captured."}

Additional discovered detail pages:
{extra_context_text}

Return a concise but evidence-rich structured summary with these exact sections:
- Value Proposition:
- Key Features:
- Pricing:
- Target Audience:
- Trust Signals:
- Integrations / Ecosystem:
- Security / Enterprise Readiness:
- Notable Messaging Angles:
"""

    try:
        findings_text = await llm_ask(prompt=prompt, max_tokens=1200)
    except Exception as e:
        logger.error(f"[browser_agent] LLM summarization failed for {competitor_name}: {e}", exc_info=True)
        findings_text = (
            f"Value Proposition: {homepage.get('title', competitor_name)}\n"
            f"Key Features: Derived from homepage and discovered internal pages.\n"
            f"Pricing: {'Captured from pricing-related page.' if pricing_text else 'Not found.'}\n"
            f"Target Audience: Derived from homepage messaging.\n"
            f"Trust Signals: Check homepage and customer pages for logos/testimonials.\n"
            f"Integrations / Ecosystem: Check discovered integrations/app pages.\n"
            f"Security / Enterprise Readiness: Check security/trust pages.\n"
            f"Notable Messaging Angles: Derived from page headlines and repeated positioning language."
        )

    await broadcast(session_id, "browser_complete", {
        "competitor": competitor_name,
        "findings": findings_text,
        "steps_taken": step_counter,
    })

    features = _extract_feature_list(findings_text)
    pricing_details = _extract_section(findings_text, "Pricing:")
    target_audience = _extract_section(findings_text, "Target Audience:")
    trust_signals = _extract_section(findings_text, "Trust Signals:")
    value_proposition = _extract_section(findings_text, "Value Proposition:")

    return _result(
        competitor_name,
        competitor_url,
        findings_text,
        step_counter,
        True,
        pricing_model=_derive_pricing_model(pricing_details),
        pricing_details=pricing_details,
        features=features,
        strengths=[value_proposition] if value_proposition else [],
        weaknesses=[],
        target_audience=target_audience,
        market_position=trust_signals or f"Analyzed via browser agent ({step_counter} steps)",
    )


def _result(
    name,
    url,
    findings,
    steps,
    browser_analyzed,
    pricing_model="unknown",
    pricing_details="",
    features=None,
    strengths=None,
    weaknesses=None,
    target_audience="",
    market_position=None,
):
    return {
        "name": name,
        "url": url,
        "browser_findings": findings,
        "steps_taken": steps,
        "is_browser_analyzed": browser_analyzed,
        "pricing_model": pricing_model,
        "pricing_details": pricing_details,
        "features": features or [],
        "strengths": strengths or [],
        "weaknesses": weaknesses or [],
        "market_position": market_position or f"Analyzed via browser agent ({steps} steps)",
        "target_audience": target_audience,
    }


def _fallback(name, url, error):
    return {
        "name": name,
        "url": url,
        "browser_findings": f"Browser analysis failed: {error}",
        "steps_taken": 0,
        "is_browser_analyzed": False,
        "pricing_model": "unknown",
        "pricing_details": "",
        "features": [],
        "strengths": [],
        "weaknesses": [],
        "market_position": "Browser analysis unavailable",
        "target_audience": "",
    }
