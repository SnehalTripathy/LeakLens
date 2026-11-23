from __future__ import annotations

"""Browser release smoke checks for the built LeakLens app.

Starts isolated local API/frontend processes, then exercises the user-facing
import -> intelligence -> review -> export path, basic keyboard/mobile
behavior, axe accessibility rules, and a lightweight page-load budget.
"""

import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
API_URL = "http://127.0.0.1:8000"
WEB_URL = "http://127.0.0.1:4173"


def wait_for(url: str, process: subprocess.Popen, timeout: int = 60) -> None:
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Service exited early ({process.returncode}): {last_error}")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise TimeoutError(f"Service did not become ready: {url}; last error: {last_error}")


def main() -> None:
    temp = tempfile.TemporaryDirectory(prefix="leaklens-e2e-")
    work = Path(temp.name)
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT / "backend"),
        "LEAKLENS_DB_PATH": str(work / "e2e.sqlite3"),
        "LEAKLENS_CORS_ORIGINS": WEB_URL,
        "LEAKLENS_ENABLE_LOCAL_ADMIN": "false",
    })
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=ROOT / "backend", env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    web = subprocess.Popen(
        [sys.executable, "-m", "http.server", "4173", "--bind", "127.0.0.1",
         "--directory", str(ROOT / "frontend" / "dist")],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    csv_path = work / "review-ledger.csv"
    lines = ["date,description,vendor,category,amount,type,currency,branch,account_code,account_name,service_date"]
    for month, amount in [(6, 100), (7, 100), (8, 100), (9, 100), (10, 100), (11, 260)]:
        lines.append(f"2026-{month:02d}-12,Cloud platform renewal,Release Smoke Vendor,Technology,{amount},expense,USD,East,6100,Cloud Services,2026-{month:02d}-01")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    try:
        wait_for(API_URL + "/health", api)
        wait_for(WEB_URL, web)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            page_errors: list[str] = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))

            page.goto(WEB_URL, wait_until="networkidle", timeout=30000)
            page.locator("h1").first.wait_for()
            assert "See the bigger" in page.locator("h1").first.inner_text()

            # Import preview must be non-destructive until explicit confirmation.
            page.get_by_role("button", name="Import transactions").click()
            page.locator('input[type="file"]').set_input_files(str(csv_path))
            page.get_by_role("heading", name="Review before importing").wait_for()
            assert page.get_by_text("Detected columns").is_visible()
            page.get_by_role("button", name="Confirm import").click()
            page.get_by_text("Import processed: 6 new transactions added.").wait_for(timeout=15000)

            # Detect and review the imported vendor signal.
            page.get_by_role("button", name="Leak detection").click()
            page.get_by_text("Release Smoke Vendor").wait_for(timeout=15000)
            page.get_by_role("button", name="Alerts centre").click()
            review_button = page.get_by_role("button", name="Mark reviewed").first
            review_button.wait_for(timeout=15000)
            review_button.click()

            # Export a real CSV download from the UI.
            page.get_by_role("button", name="Reports").click()
            with page.expect_download(timeout=15000) as download_info:
                page.get_by_role("button", name="Download CSV").click()
            download = download_info.value
            assert download.suggested_filename.endswith(".csv")

            # Keyboard focus and automated WCAG scan (critical violations fail CI).
            page.goto(WEB_URL, wait_until="networkidle")
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement && document.activeElement.tagName !== 'BODY'")
            axe_path = Path(os.environ.get("AXE_CORE_PATH", str(ROOT / "frontend" / "node_modules" / "axe-core" / "axe.min.js")))
            page.add_script_tag(path=str(axe_path))
            axe = page.evaluate("""async () => {
              const result = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa']}});
              return result.violations.map(v => ({id:v.id, impact:v.impact, description:v.description, nodes:v.nodes.length}));
            }""")
            critical = [item for item in axe if item["impact"] == "critical"]
            print("Axe WCAG findings:", axe)
            assert not critical, f"Critical accessibility violations: {critical}"

            # Responsive layout and lightweight performance budget.
            page.set_viewport_size({"width": 390, "height": 844})
            page.reload(wait_until="networkidle")
            page.get_by_role("button", name="Open menu").click()
            assert page.get_by_role("button", name="Close navigation").is_visible()
            overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            assert overflow <= 1, f"Horizontal overflow at mobile width: {overflow}px"
            page.set_viewport_size({"width": 1440, "height": 960})
            page.reload(wait_until="networkidle")
            timing = page.evaluate("""() => {
              const n = performance.getEntriesByType('navigation')[0];
              const resources = performance.getEntriesByType('resource');
              return {load_ms: n ? n.loadEventEnd - n.startTime : 0,
                      resource_count: resources.length,
                      transfer_bytes: resources.reduce((sum, r) => sum + (r.transferSize || 0), 0)};
            }""")
            print("Page performance:", timing)
            assert timing["load_ms"] < 8000, f"Page-load budget exceeded: {timing}"
            assert not page_errors, f"Browser runtime errors: {page_errors}"
            browser.close()
    finally:
        for process in (web, api):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        temp.cleanup()


if __name__ == "__main__":
    main()
