"""
Generic async API scanner — platform-agnostic engine used by all ATS integrations.

The caller supplies an extractor function that knows how to parse a platform's
JSON response into (title, url) pairs. Everything else — HTTP fetch, semaphore,
error handling, dedup, write-lock, on_match callback, atomic console output —
lives here once.
"""

import asyncio
from datetime import datetime
from typing import Callable

import httpx

from csv_io import append_match_row
from utils import apply_filters, find_matches


async def scan_api(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    name: str,
    api_url: str,
    titles: list[str],
    output_path: str,
    write_lock: asyncio.Lock,
    known_urls: set[str],
    extractor: Callable[[dict], list[tuple[str, str, dict]]],
    platform_label: str,
    on_match=None,
    filters: dict | None = None,
) -> list[dict]:
    """
    Fetch jobs from an ATS API and return newly matched dicts.

    extractor(json_data) → [(title, absolute_url), ...]
    platform_label is used only for the console line prefix.
    All output lines are buffered and printed atomically to prevent interleaving.
    """
    async with semaphore:
        lines = [f"\n🔎  Scanning ({platform_label}): {name}"]
        new_found = []

        try:
            response = await client.get(api_url, timeout=10.0)

            if response.status_code != 200:
                lines.append(f"⚠️   API error (status {response.status_code}) — skipping")
                print("\n".join(lines))
                return []

            data = response.json()
            jobs = extractor(data)
            jobs = apply_filters(jobs, filters or {})
            links = [(t, u) for t, u, _ in jobs]
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
                            lines.append("🟢  added to output file")

                if not new_found:
                    lines.append("🟡  No new matches found")
            else:
                lines.append("❌  No matches found")

        except httpx.ConnectError:
            lines.append("⚠️   Network error — skipping")
        except httpx.TimeoutException:
            lines.append("⚠️   Request timed out — skipping")
        except (ValueError, KeyError) as e:
            lines.append(f"⚠️   Response parse error — {e}")
        except Exception as e:
            lines.append(f"⚠️   Error — {e}")

        print("\n".join(lines))
        return new_found
