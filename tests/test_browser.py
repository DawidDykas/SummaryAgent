"""Testy E2E w prawdziwej przeglądarce (Playwright) - łapią błędy montowania UI.

Regresja dla buga: przeniesienie app.js na type="module" bez zmiany kolejności
tagów <script> sprawiło, że Alpine startował PRZED ustawieniem window.summaryApp
("Alpine Expression Error: summaryApp is not defined" -> całe UI martwe).

Test pomijany, gdy playwright/chromium niedostępne (np. brak przeglądarki w CI).
"""

import asyncio
import socket
import threading
import time
from pathlib import Path

import pytest

playwright_api = pytest.importorskip("playwright.async_api", reason="playwright niezainstalowany")
async_playwright = playwright_api.async_playwright


def _chromium_available() -> bool:
    """Chromium binarny dostępny? (w CI zwykle nie -> test pomijany zamiast faila)"""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _chromium_available(), reason="chromium niezainstalowany")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    """Uruchamia uvicorn na wolnym porcie w wątku (prawdziwy serwer dla przeglądarki)."""
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
        pytest.fail("serwer nie wystartował")
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

        # 1) klik w dropzone -> dialog systemowy -> wybór 2 plików
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

        # 2) drag & drop na dropzone
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

        # 3) wybór języka z flagą w headerze (dropdown) + sync z selectem z lewej
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
                return {lang: d.lang, flag: d.langFlag, open: d.langOpen,
                        select: sel ? sel.value : null,
                        title: document.title, htmlLang: document.documentElement.lang,
                        navText: nav ? nav.textContent.trim() : null,
                        dropTranslated: body.includes('Drop files here') && !body.includes('Przeciągnij pliki tutaj'),
                        // etykiety mają CSS uppercase -> porównujemy bez wielkości liter
                        settingsLabel: body.toLowerCase().includes('language') && !body.toLowerCase().includes('język'),
                        resultTitle: d.t('result.title')};
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
        "button": {"visible": btn_visible, "enabled": btn_enabled},
        "page_errors": page_errors,
        "console_errors": console_errors,
    }


def test_ui_mounts_without_js_errors(live_server):
    """Alpine musi zamontować summaryApp bez ReferenceError i pozwalać na upload."""
    report = asyncio.run(_browser_test(live_server))

    assert report["page_errors"] == [], f"bledy strony: {report['page_errors']}"
    assert report["console_errors"] == [], f"konsola: {report['console_errors']}"

    st = report["state"]
    assert st.get("mounted") is not None, "Alpine nie zamontowal x-data"
    assert st["mounted"], "x-data nie zainicjalizowane (summaryApp niedostepne dla Alpine?)"
    assert st["hasSummaryApp"], "window.summaryApp nie ustawione"
    assert st["busy"] is False and st["lang"] == "pl"

    up = report["after_click"]
    assert up["docs"] == 1 and up["format"] == "TXT" and up["nameShown"], up

    dnd = report["after_drop"]
    assert dnd["docs"] == 2 and "e2e_dnd.txt" in dnd["names"], dnd

    lang = report["after_lang"]
    assert lang["lang"] == "en" and lang["flag"] == "🇬🇧", lang
    assert lang["open"] is False, f"dropdown nie zamknął się: {lang}"
    assert lang["select"] == "en", f"select z lewej nie zsynchronizowany: {lang}"
    # tłumaczenie interfejsu po wybraniu języka
    assert lang["htmlLang"] == "en" and "AI document summaries" in lang["title"], lang
    assert lang["navText"] == "Upload files", lang
    assert lang["dropTranslated"], f"dropzone nietłumaczony: {lang}"
    assert lang["settingsLabel"], f"etykiety ustawień nietłumaczone: {lang}"
    assert lang["resultTitle"] == "Summary", lang

    assert report["button"]["visible"] and report["button"]["enabled"]
