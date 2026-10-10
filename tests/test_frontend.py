"""Testy frontendu (moduły ES) uruchamiane w node - łapią brakujące importy itp.

Zabezpiecza przed powtórką błędu, przez który przestało działać UI:
użycie `shortFmt` w app.js bez zaimportowania => ReferenceError w Alpine.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

NODE = shutil.which("node")
STATIC_JS = Path(__file__).resolve().parents[1] / "backend" / "static" / "js"

pytestmark = pytest.mark.skipif(NODE is None, reason="node niedostępny w środowisku")


def run_node(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [NODE, "--input-type=module", "-e", textwrap.dedent(script)],
        capture_output=True,
        text=True,
        cwd=STATIC_JS,
        timeout=30,
    )


def test_all_modules_load():
    result = run_node(
        """
        globalThis.window = {};
        globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
        for (const name of ['api', 'sse', 'history', 'ui', 'i18n', 'app']) {
          await import(`./${name}.js`);
          console.log(name + ':OK');
        }
        """
    )
    assert result.returncode == 0, result.stderr
    for name in ("api", "sse", "history", "ui", "i18n", "app"):
        assert f"{name}:OK" in result.stdout


def test_summary_app_initializes_and_helpers_work():
    """Wywołanie summaryApp() nie może rzucić ReferenceError (brak importu)."""
    result = run_node(
        """
        globalThis.window = {};
        globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
        globalThis.document = {
          title: '',
          documentElement: { lang: 'pl' },
          querySelector: () => null,
          createElement: () => ({ click() {} }),
        };
        globalThis.marked = { parse: (s) => s };
        globalThis.DOMPurify = { sanitize: (s) => s };

        const { summaryApp } = await import('./app.js');
        const app = summaryApp();

        const required = [
          'init', 'generate', 'upload', 'removeDoc', 'onPick', 'onDrop', 'onDragLeave',
          'copySummary', 'downloadSummary', 'reset', 'showError', 'loadHistory', 'clearHistory',
          'renderedSummary', 'statsLabel', 'providerLabel', 'totalChars', 'totalChunks',
          'badgeClass', 'shortFmt', 'fmtNum', 'partsWord', 'firstLine',
          'langFlag', 'langName', 'langOpen', 'langs',
          't', 'howSteps', 'syncDocLang', 'uiLang', 'historyTitle',
        ];
        const missing = required.filter((k) => !(k in app));
        if (missing.length) { console.error('BRAK KLUCZY: ' + missing.join(',')); process.exit(1); }

        if (app.shortFmt('Markdown') !== 'MD') { console.error('shortFmt zły'); process.exit(1); }
        if (app.shortFmt('TXT') !== 'TXT') { console.error('shortFmt TXT zły'); process.exit(1); }
        if (!app.badgeClass('PDF').includes('red')) { console.error('badgeClass zły'); process.exit(1); }
        if (app.fmtNum(1234567).length < 5) { console.error('fmtNum zły'); process.exit(1); }
        if (app.partsWord(1) !== 'część' || app.partsWord(2) !== 'części') { console.error('partsWord zły'); process.exit(1); }
        if (app.firstLine('## Tytuł\\ntreść') !== 'Tytuł') { console.error('firstLine zły: ' + app.firstLine('## Tytuł')); process.exit(1); }
        if (app.summary !== '' || app.busy !== false || app.lang !== 'pl' || app.uiLang !== 'pl') { console.error('stan domyślny zły'); process.exit(1); }
        if (app.langFlag !== '🇵🇱' || app.langName !== 'Polski') { console.error('flaga/język domyślny zły'); process.exit(1); }
        // FLAGA w headerze sledzi uiLang (jezyk interfejsu), NIE lang (jezyk podsumowania)
        app.uiLang = 'en';
        if (app.langFlag !== '🇬🇧' || app.langName !== 'English') { console.error('flaga nie sledzi uiLang'); process.exit(1); }
        app.uiLang = 'pl';
        if (app.langFlag !== '🇵🇱' || app.langName !== 'Polski') { console.error('flaga nie wraca na pl'); process.exit(1); }

        // t() sledzi uiLang...
        if (app.t('nav.upload') !== 'Wgraj pliki') { console.error('i18n pl: ' + app.t('nav.upload')); process.exit(1); }
        app.uiLang = 'en';
        if (app.t('nav.upload') !== 'Upload files') { console.error('i18n en: ' + app.t('nav.upload')); process.exit(1); }
        // ...i jest NIEZALEZNE od jezyka podsumowania (lang)
        app.lang = 'pl';
        if (app.t('nav.upload') !== 'Upload files') { console.error('t() zalezne od lang - zle'); process.exit(1); }
        app.lang = 'en';
        if (app.uiLang !== 'en') { console.error('zmiana lang nadpisala uiLang - zle'); process.exit(1); }

        const withVars = app.t('drop.max', {mb: 25, n: 10});
        if (!withVars.includes('25') || !withVars.includes('10')) { console.error('interpolacja zła: ' + withVars); process.exit(1); }
        if (app.t('nie.ma.takiego.klucza') !== 'nie.ma.takiego.klucza') { console.error('fallback klucza zły'); process.exit(1); }

        // syncDocLang aktualizuje <title> i lang dokumentu
        app.uiLang = 'en';
        app.syncDocLang('en');
        if (globalThis.document.documentElement.lang !== 'en') { console.error('html lang niezmieniony'); process.exit(1); }
        if (!globalThis.document.title.includes('AI document summaries')) { console.error('title niezmieniony: ' + globalThis.document.title); process.exit(1); }

        // kroki "jak to działa" po angielsku
        const steps = app.howSteps;
        if (steps.length !== 3 || steps[0].t !== 'Upload files') { console.error('howSteps złe: ' + JSON.stringify(steps)); process.exit(1); }

        // TYTUL wpisu historii ("W skrócie") w jezyku globalnym (uiLang), w obie strony
        if (app.historyTitle('## W skrócie\\nabc') !== 'In brief') { console.error('historyTitle en: ' + app.historyTitle('## W skrócie')); process.exit(1); }
        if (app.historyTitle('## Wnioski\\nabc') !== 'Conclusions') { console.error('historyTitle wnioski en zly'); process.exit(1); }
        if (app.historyTitle('## In brief\\nabc') !== 'In brief') { console.error('historyTitle en en zly'); process.exit(1); }
        if (app.historyTitle('## Mój raport Q4') !== 'Mój raport Q4') { console.error('historyTitle passthrough zly'); process.exit(1); }
        app.uiLang = 'pl';
        if (app.historyTitle('## In brief\\nabc') !== 'W skrócie') { console.error('historyTitle pl: ' + app.historyTitle('## In brief')); process.exit(1); }
        if (app.historyTitle('(bez nagłówka)') !== '(bez nagłówka)') { console.error('historyTitle pusty zly'); process.exit(1); }
        app.uiLang = 'en';

        // window.summaryApp jest ustawione - tak Alpine znajduje komponent
        if (typeof globalThis.window.summaryApp !== 'function') { console.error('brak window.summaryApp'); process.exit(1); }

        console.log('SUMMARY_APP_OK');
        """
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "SUMMARY_APP_OK" in result.stdout


def test_sse_parser_handles_split_chunks():
    result = run_node(
        """
        import { sseEvents } from './sse.js';
        const full = 'event: status\\ndata: {"step":"prepare","message":"x"}\\n\\n'
                   + 'event: done\\ndata: {"summary":"OK"}\\n\\n';
        const parts = [full.slice(0, 33), full.slice(33, 80), full.slice(80)];
        const resp = { body: { getReader() {
          let i = 0;
          return { async read() {
            return i < parts.length ? { done: false, value: Buffer.from(parts[i++]) } : { done: true };
          } };
        } } };
        const events = [];
        for await (const e of sseEvents(resp)) events.push(e);
        if (events.length !== 2 || events[1].data.summary !== 'OK') {
          console.error('SSE zły: ' + JSON.stringify(events)); process.exit(1);
        }
        console.log('SSE_OK');
        """
    )
    assert result.returncode == 0, result.stderr
    assert "SSE_OK" in result.stdout
