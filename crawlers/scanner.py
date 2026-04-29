"""
Scanner — async Playwright-based career page scanner.
"""

import asyncio
from datetime import datetime
from urllib.parse import urljoin

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from config import PAGE_TIMEOUT, PAGE_TIMEOUT_RETRY, PAGE_SETTLE_MS
from csv_io import append_match_row
from utils import normalize_text, find_matches


# ── Navigation ────────────────────────────────────────────────────────────────

async def navigate(page, url: str, timeout: int) -> None:
    """
    Navigate to URL and wait for DOM to be ready.

    Uses domcontentloaded instead of networkidle — career pages often have
    persistent analytics/chat requests that never fully settle, causing
    networkidle to always hit the timeout limit.
    A fixed settle wait after load gives JS time to render job listings.
    """
    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    await page.wait_for_timeout(PAGE_SETTLE_MS)


# ── Link extraction ───────────────────────────────────────────────────────────

async def get_job_links(page, base_url: str) -> list[tuple[str, str]]:
    """
    Extract all anchor elements from the page.
    Returns a list of (link_text_line, absolute_url) pairs.

    Link text is split line by line — some ATS platforms put the job title
    on the first line followed by location/type on subsequent lines.
    Relative hrefs are resolved to absolute URLs using base_url.
    """
    result = []
    for anchor in await page.query_selector_all("a[href]"):
        href      = await anchor.get_attribute("href") or ""
        link_text = await anchor.inner_text() or ""
        if not href or not link_text.strip():
            continue
        absolute_url = urljoin(base_url, href)
        for line in link_text.splitlines():
            line = line.strip()
            if line:
                result.append((line, absolute_url))
    return result


# ── Company scanner ───────────────────────────────────────────────────────────

async def scan_company(
    semaphore: asyncio.Semaphore,
    context,
    name: str,
    url: str,
    titles: list[str],
    output_path: str,
    write_lock: asyncio.Lock,
    known_urls: set[str],
    on_match=None,
) -> list[dict]:
    """
    Scan a single company's career page.
    Controlled by semaphore to cap concurrent open tabs.
    Collects all output lines then prints them atomically so results
    from parallel tabs don't interleave in the console.

    Resilience:
    - Fix 1: domcontentloaded + settle wait instead of networkidle
    - Fix 4: one retry with extended timeout on first-attempt timeout
    - Fix 5: execution context guard on DOM query (handles mid-scan redirects)

    Duplicate check:
    - For each matched URL, acquires write_lock and checks known_urls.
    - New URLs are written immediately and added to known_urls.
    - Duplicate URLs are skipped silently.

    Returns a list of newly written match dicts. Returns [] on timeout/error.
    """
    async with semaphore:
        page = await context.new_page()
        lines     = [f"\n🔎  Scanning : {name} - {url}"]
        new_found = []
        try:
            # Fix 1 + Fix 4 — load with domcontentloaded, retry once on timeout
            try:
                await navigate(page, url, PAGE_TIMEOUT)
            except PlaywrightTimeoutError:
                lines.append("⏳  Timed out, retrying with extended timeout...")
                await navigate(page, url, PAGE_TIMEOUT_RETRY)

            # Fix 5 — execution context guard: if the page navigates mid-query
            # (SPA redirect, meta-refresh, etc.) the context is destroyed.
            # Wait for the new load state and retry the DOM query once.
            try:
                links = await get_job_links(page, url)
            except Exception as e:
                if "context was destroyed" in str(e).lower():
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(PAGE_SETTLE_MS)
                    links = await get_job_links(page, url)
                else:
                    raise

            matches = find_matches(links, titles)

            if matches:
                time_found = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for title, scraped_text, job_url in matches:
                    async with write_lock:
                        if job_url not in known_urls:
                            match_dict = {
                                "company_name":       name,
                                "match_title":        title,
                                "position_title":     scraped_text,
                                "match_position_url": job_url,
                                "time_found":         time_found,
                            }
                            append_match_row(match_dict, output_path)
                            known_urls.add(job_url)
                            new_found.append(match_dict)
                            if on_match:
                                on_match(name, title, scraped_text, job_url)
                            lines.append(f"✅  Match for: [{title}]:")
                            lines.append(f"    {scraped_text}")
                            lines.append(f"    {job_url}")
                            lines.append(f"🟢  added to output file")
                        # duplicate — skip silently, no output line

                if not new_found:
                    # Title matches were found on the page but all URLs already in CSV
                    lines.append("🟡  No new matches found")
            else:
                lines.append("❌  No matches found")

        except PlaywrightTimeoutError:
            lines.append("⚠️   Timeout after retry — skipping")
        except Exception as e:
            lines.append(f"⚠️   Error — {e}")
        finally:
            await page.close()

        # Print all lines for this company in one shot — keeps output grouped
        print("\n".join(lines))
        return new_found
