"""E2E tests in a real browser (Playwright) - catch UI mounting errors.

Regression for a bug: moving app.js to type="module" without reordering the
<script> tags made Alpine start BEFORE window.summaryApp was set
("Alpine Expression Error: summaryApp is not defined" -> entire UI dead).

The test is skipped when playwright/chromium is unavailable (e.g. no browser in CI).
"""

import asyncio
import socket
import threading
import time
from pathlib import Path

import pytest

playwright_api = pytest.importorskip("playwright.async_api", reason="playwright not installed")
async_playwright = playwright_api.async_playwright


def _chromium_available() -> bool:
    """Is the Chromium binary available? (usually not in CI -> skip instead of fail)"""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _chromium_available(), reason="chromium not installed")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    """Run uvicorn on a free port in a thread (real server for the browser)."""
    port = _free_port()
    config = None
    server = None
    ready = threading.Event()

    def run():
        import uvicorn

        from backend.api.main import app

        nonlocal config, server
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)
        ready.set()
        server.run()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    ready.wait(10)
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.2)
    else:
        pytest.fail("server did not start")
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    t.join(timeout=10)


async def _browser_test(base: str) -> dict:
    page_errors, console_errors = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on(
            "console",
            lambda m: console_errors.append(m.text) if m.type == "error" else None,
        )
        await page.goto(base, wait_until="networkidle")
        await page.wait_for_timeout(1500)

        state = await page.evaluate(
            """() => {
                const el = document.querySelector('[x-data]');
                const d = el?._x_dataStack?.[0];
                if (!d) return {mounted: false};
                return {
                    mounted: true,
                    hasSummaryApp: typeof window.summaryApp === 'function',
                    busy: d.busy, lang: d.lang, docs: d.docs.length,
                    health: d.health?.label || null,
                    steps: (d.steps || []).length,
                };
            }"""
        )

        # 1) click the dropzone -> system dialog -> pick 2 files
        tmp = Path("/tmp") / "e2e_upload.txt"
        tmp.write_text("Dokument testowy do przeslania przez UI. " * 3)
        tmp2 = Path("/tmp") / "e2e_drop.txt"
        tmp2.write_text("Drugi dokument. " * 3)
        async with page.expect_file_chooser(timeout=5000) as fc_info:
            await page.locator("#dropzone .drop-zone").click()
        await (await fc_info.value).set_files([str(tmp)])
        await page.wait_for_timeout(1000)

        after_click = await page.evaluate(
            """() => {
                const d = document.querySelector('[x-data]')._x_dataStack[0];
                return {docs: d.docs.length, format: d.docs[0]?.format || null,
                        nameShown: document.body.innerText.includes('e2e_upload')};
            }"""
        )

        # 2) drag & drop onto the dropzone
        await page.evaluate(
            """() => {
                const f = new File(['drop content'], 'e2e_dnd.txt', {type: 'text/plain'});
                const dt = new DataTransfer();
                dt.items.add(f);
                const target = [...document.querySelectorAll('*')].find((e) =>
                    [...e.attributes].some((a) => a.name.startsWith('@') && a.name.toLowerCase().includes('drop'))
                );
                target.dispatchEvent(new DragEvent('drop', {bubbles: true, cancelable: true, dataTransfer: dt}));
            }"""
        )
        await page.wait_for_timeout(1200)

        after_drop = await page.evaluate(
            """() => {
                const d = document.querySelector('[x-data]')._x_dataStack[0];
                return {docs: d.docs.length, names: d.docs.map((x) => x.name)};
            }"""
        )

        # 3) global UI language in the header - changes the PAGE, not the summary language
        await page.locator("#lang-switcher").click()
        await page.wait_for_timeout(300)
        await page.get_by_role("button", name="English").click()
        await page.wait_for_timeout(400)

        after_lang = await page.evaluate(
            """() => {
                const d = document.querySelector('[x-data]')._x_dataStack[0];
                const sel = document.querySelector('select[x-model="lang"]');
                const body = document.body.innerText;
                const nav = document.querySelector('a[href="#dropzone"]');
                return {uiLang: d.uiLang, lang: d.lang, open: d.langOpen,
                        select: sel ? sel.value : null,
                        title: document.title, htmlLang: document.documentElement.lang,
                        navText: nav ? nav.textContent.trim() : null,
                        dropTranslated: body.includes('Drop files here') && !body.includes('Przeciągnij pliki tutaj'),
                        // labels use CSS uppercase -> compare case-insensitively
                        settingsLabel: body.toLowerCase().includes('language') && !body.toLowerCase().includes('język'),
                        resultTitle: d.t('result.title')};
            }"""
        )

        # 4) select above Summary = SUMMARY LANGUAGE - separate state, does not touch the UI
        await page.select_option('select[x-model="lang"]', "en")
        await page.wait_for_timeout(300)
        after_select = await page.evaluate(
            """() => {
                const d = document.querySelector('[x-data]')._x_dataStack[0];
                const sel = document.querySelector('select[x-model="lang"]');
                const body = document.body.innerText;
                return {lang: d.lang, uiLang: d.uiLang, select: sel.value,
                        pageStillEn: body.includes('Drop files here')};
            }"""
        )

        # 5) header back to PL - the page returns, the summary language STAYS en
        await page.locator("#lang-switcher").click()
        await page.wait_for_timeout(300)
        await page.get_by_role("button", name="Polski").click()
        await page.wait_for_timeout(400)
        after_back = await page.evaluate(
            """() => {
                const d = document.querySelector('[x-data]')._x_dataStack[0];
                const sel = document.querySelector('select[x-model="lang"]');
                const body = document.body.innerText;
                const nav = document.querySelector('a[href="#dropzone"]');
                return {uiLang: d.uiLang, lang: d.lang, select: sel.value,
                        navText: nav ? nav.textContent.trim() : null,
                        pageBackPl: body.includes('Przeciągnij pliki tutaj') && !body.includes('Drop files here'),
                        summaryLangLabel: body.toLowerCase().includes('język podsumowania')};
            }"""
        )

        btn = page.locator("button", has_text="Summary").first
        btn_visible = await btn.is_visible()
        btn_enabled = await btn.is_enabled() if btn_visible else False

        await page.screenshot(path="/tmp/e2e_ui.png", full_page=False)
        await browser.close()

    return {
        "state": state,
        "after_click": after_click,
        "after_drop": after_drop,
        "after_lang": after_lang,
        "after_select": after_select,
        "after_back": after_back,
        "button": {"visible": btn_visible, "enabled": btn_enabled},
        "page_errors": page_errors,
        "console_errors": console_errors,
    }


def test_ui_mounts_without_js_errors(live_server):
    """Alpine must mount summaryApp without ReferenceError and allow uploads."""
    report = asyncio.run(_browser_test(live_server))

    assert report["page_errors"] == [], f"page errors: {report['page_errors']}"
    assert report["console_errors"] == [], f"console: {report['console_errors']}"

    st = report["state"]
    assert st.get("mounted") is not None, "Alpine did not mount x-data"
    assert st["mounted"], "x-data not initialised (summaryApp unavailable to Alpine?)"
    assert st["hasSummaryApp"], "window.summaryApp not set"
    assert st["busy"] is False and st["lang"] == "pl"

    up = report["after_click"]
    assert up["docs"] == 1 and up["format"] == "TXT" and up["nameShown"], up

    dnd = report["after_drop"]
    assert dnd["docs"] == 2 and "e2e_dnd.txt" in dnd["names"], dnd

    ui = report["after_lang"]
    assert ui["uiLang"] == "en", ui
    assert ui["open"] is False, f"dropdown did not close: {ui}"
    # INDEPENDENCE: the header does not touch the summary language
    assert ui["lang"] == "pl" and ui["select"] == "pl", f"header changed lang: {ui}"
    assert ui["htmlLang"] == "en" and "AI document summaries" in ui["title"], ui
    assert ui["navText"] == "Upload files", ui
    assert ui["dropTranslated"], f"dropzone not translated: {ui}"
    assert ui["settingsLabel"], f"settings labels not translated: {ui}"
    assert ui["resultTitle"] == "Summary", ui

    sel = report["after_select"]
    assert sel["lang"] == "en" and sel["select"] == "en", sel
    assert sel["uiLang"] == "en" and sel["pageStillEn"], f"select broke the UI: {sel}"

    back = report["after_back"]
    assert back["uiLang"] == "pl" and back["lang"] == "en" and back["select"] == "en", back
    assert back["navText"] == "Wgraj pliki", back
    assert back["pageBackPl"], f"page did not return to PL: {back}"
    assert back["summaryLangLabel"], f"summary language label missing: {back}"

    assert report["button"]["visible"] and report["button"]["enabled"]
