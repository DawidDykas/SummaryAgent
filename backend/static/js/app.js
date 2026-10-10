/** Główny komponent Alpine - skleja API, SSE, historię i UI. */

import { deleteDocument, fetchHealth, fetchOllamaStatus, fetchSummaryStream, uploadDocuments } from './api.js';
import { clearStoredHistory, loadStoredHistory, saveStoredHistory } from './history.js';
import { heading, tr } from './i18n.js';
import { sseEvents } from './sse.js';
import { badgeClass, firstLine, fmtNum, partsWord, scrollToPanel, shortFmt } from './ui.js';

export function summaryApp() {
  return {
    // --- stan ---
    docs: [],
    errors: [],
    expanded: null,
    busy: false,
    dragging: false,
    lang: 'pl',        // język PODSUMOWANIA (select nad przyciskiem Summary)
    uiLang: 'pl',       // globalny język INTERFEJSU (przełącznik w headerze)
    langOpen: false,
    langs: [
      { code: 'pl', name: 'Polski', flag: '🇵🇱' },
      { code: 'en', name: 'English', flag: '🇬🇧' },
    ],
    length: 'standard',
    // --- przebieg generowania ---
    stage: '',
    steps: [],
    progress: null,
    dots: '',
    // --- wynik ---
    summary: '',
    stats: null,
    statsFiles: [],
    copied: false,
    // --- otoczenie ---
    health: null,
    ollamaWarning: '',
    history: [],
    toast: '',
    maxFileMb: 25,
    maxFiles: 10,
    _dotTimer: null,
    _toastTimer: null,

    async init() {
      this._animateDots();
      this.history = loadStoredHistory();
      try {
        this.health = await fetchHealth();
      } catch (_) {
        /* serwer niedostępny */
      }
      if (this.health?.provider === 'ollama') {
        try {
          const status = await fetchOllamaStatus();
          if (status && (!status.reachable || status.model_ready === false)) {
            this.ollamaWarning = status.detail || this.t('err.ollama');
          }
        } catch (_) {
          /* ignore */
        }
      }
    },

    // ---------- wyliczenia ----------
    get renderedSummary() {
      if (!this.summary) return '';
      try {
        return DOMPurify.sanitize(marked.parse(this.summary));
      } catch (_) {
        return DOMPurify.sanitize(this.summary.replace(/\n/g, '<br>'));
      }
    },

    get providerLabel() {
      return this.health?.label || this.t('provider.fallback');
    },

    get howSteps() {
      return [
        { n: '1', t: this.t('how.1.t'), d: this.t('how.1.d') },
        { n: '2', t: this.t('how.2.t'), d: this.t('how.2.d') },
        { n: '3', t: this.t('how.3.t'), d: this.t('how.3.d') },
      ];
    },

    get _currentLang() {
      return this.langs.find((l) => l.code === this.uiLang) || this.langs[0];
    },

    get langFlag() {
      return this._currentLang.flag;
    },

    get langName() {
      return this._currentLang.name;
    },

    get totalChars() {
      return this.docs.reduce((sum, d) => sum + d.chars, 0);
    },

    get totalChunks() {
      return this.docs.reduce((sum, d) => sum + d.chunks, 0);
    },

    get statsLabel() {
      if (!this.stats) return '';
      const s = this.stats;
      return [
        s.model,
        `${s.chunks} ${partsWord(s.chunks, this.uiLang)}`,
        `${fmtNum(s.chars, this.uiLang)} ${this.t('stats.chars')}`,
        `${s.duration_s}s`,
      ].join(' · ');
    },

    partsWord,
    firstLine,
    fmtNum,
    badgeClass,
    shortFmt,

    t(key, vars) {
      return tr(this.uiLang, key, vars);
    },

    historyTitle(summary) {
      return heading(this.uiLang, firstLine(summary, this.uiLang));
    },

    syncDocLang(code) {
      const lang = code === 'en' ? 'en' : 'pl';
      document.title = this.t('meta.title');
      document.documentElement.lang = lang;
      document.querySelector('meta[name="description"]')?.setAttribute('content', this.t('meta.description'));
    },

    // ---------- pliki ----------
    onPick(e) {
      const files = Array.from(e.target.files || []);
      if (files.length) this.upload(files);
      e.target.value = '';
    },

    onDrop(e) {
      this.dragging = false;
      const files = Array.from(e.dataTransfer?.files || []);
      if (files.length) this.upload(files);
    },

    onDragLeave(e) {
      if (!e.relatedTarget) this.dragging = false;
    },

    async upload(files) {
      if (this.docs.length + files.length > this.maxFiles) {
        this.showError(this.t('err.maxFiles', { n: this.maxFiles }));
        return;
      }
      try {
        const data = await uploadDocuments(files);
        (data.documents || []).forEach((d) => {
          if (!this.docs.some((x) => x.id === d.id)) this.docs.push(d);
        });
        (data.errors || []).forEach((err) => this.showError(`${err.name}: ${err.error}`));
      } catch (err) {
        this.showError(err.message);
      }
    },

    async removeDoc(id) {
      this.docs = this.docs.filter((d) => d.id !== id);
      this.expanded = null;
      await deleteDocument(id);
    },

    // ---------- oś kroków (Thinking) ----------
    _step(key, text, state) {
      const i = this.steps.findIndex((s) => s.key === key);
      if (i >= 0) {
        this.steps[i].text = text;
        if (state) this.steps[i].state = state;
      } else {
        this.steps.forEach((s) => {
          if (s.state === 'active') s.state = 'done';
        });
        this.steps.push({ key, text, state: state || 'active' });
      }
    },

    _applyStatusEvent(data) {
      this.stage = data.message || '';
      if (typeof data.total === 'number' && data.total > 0 && typeof data.progress === 'number') {
        this.progress = Math.max(4, Math.round((data.progress / data.total) * 96));
      } else {
        this.progress = null;
      }
      if (data.step === 'prepare') this._step('prepare', data.message || this.t('step.prepare'));
      else if (data.step === 'chunk') this._step('chunk', data.message || this.t('step.chunk'));
      else if (data.step === 'thinking') this._step('thinking', data.message || this.t('step.thinking'));
      else if (data.step === 'synthesize') this._step('synthesize', data.message || this.t('step.synthesize'));
    },

    // ---------- generowanie ----------
    async generate() {
      if (this.busy || !this.docs.length) return;
      this.busy = true;
      this.summary = '';
      this.stats = null;
      this.statsFiles = [];
      this.steps = [];
      this.progress = null;
      this.stage = this.t('stage.preparing');
      this._step('prepare', this.t('step.prepare'));
      scrollToPanel('#thinking-panel');

      const ids = this.docs.map((d) => d.id).join(',');

      try {
        const resp = await fetchSummaryStream(ids, this.lang, this.length, this.uiLang);
        let finished = false;
        for await (const { event, data } of sseEvents(resp)) {
          if (event === 'status') {
            this._applyStatusEvent(data);
          } else if (event === 'done') {
            finished = true;
            this.steps.forEach((s) => (s.state = 'done'));
            this.summary = data.summary || '';
            this.stats = data.stats || null;
            this.statsFiles = data.files || [];
            this._saveHistory();
            scrollToPanel('#result-panel');
            break;
          } else if (event === 'error') {
            finished = true;
            this.showError(data.message || this.t('err.model'));
            break;
          }
        }
        if (!finished) this.showError(this.t('err.stream'));
      } catch (err) {
        this.showError(err);
      } finally {
        this.busy = false;
        this.stage = '';
        this.progress = null;
      }
    },

    // ---------- akcje na wyniku ----------
    async copySummary() {
      try {
        await navigator.clipboard.writeText(this.summary);
        this.copied = true;
        setTimeout(() => (this.copied = false), 1800);
      } catch (_) {
        this.showError(this.t('err.clipboard'));
      }
    },

    downloadSummary() {
      const name =
        this.statsFiles.length === 1
          ? this.statsFiles[0].replace(/\.[^.]+$/, '')
          : this.t('file.summary');
      const blob = new Blob([this.summary], { type: 'text/markdown;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `${name || this.t('file.summary')}${this.t('file.suffix')}.md`;
      a.click();
      URL.revokeObjectURL(a.href);
    },

    reset() {
      this.docs = [];
      this.errors = [];
      this.expanded = null;
      this.summary = '';
      this.stats = null;
      this.statsFiles = [];
      this.steps = [];
      this.stage = '';
      this.progress = null;
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    // ---------- historia (localStorage) ----------
    loadHistory(h) {
      this.summary = h.summary;
      this.stats = h.stats;
      this.statsFiles = h.files || [];
      this.busy = false;
      scrollToPanel('#result-panel');
    },

    clearHistory() {
      this.history = [];
      clearStoredHistory();
    },

    // ---------- pomocnicze ----------
    _saveHistory() {
      if (!this.summary || !this.stats) return;
      const item = {
        id: Date.now(),
        date: new Date().toLocaleString(this.uiLang === 'en' ? 'en-US' : 'pl-PL', {
          dateStyle: 'short',
          timeStyle: 'short',
        }),
        summary: this.summary.slice(0, 20000),
        stats: this.stats,
        files: this.statsFiles,
      };
      this.history = saveStoredHistory(item);
    },

    showError(err) {
      const msg =
        err && typeof err === 'object' && err.i18nKey
          ? this.t(err.i18nKey, err.i18nParams)
          : String(err?.message ?? err);
      this.toast = msg;
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => (this.toast = ''), 8000);
    },

    _animateDots() {
      this._dotTimer = setInterval(() => {
        this.dots = '.'.repeat((this.dots.length + 1) % 4);
      }, 450);
    },
  };
}

/* Alpine szuka summaryApp() w globalnym scopie - moduł ES tego nie robi sam. */
window.summaryApp = summaryApp;
