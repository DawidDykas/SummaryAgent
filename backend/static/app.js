const STORE_KEY = 'summaryagent.history';

function summaryApp() {
  return {
    // --- stan ---
    docs: [],
    errors: [],
    expanded: null,
    busy: false,
    dragging: false,
    lang: 'pl',
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
      this._loadHistory();
      try {
        const r = await fetch('/api/health');
        if (r.ok) this.health = await r.json();
      } catch (_) { /* serwer niedostępny */ }
      if (this.health?.provider === 'ollama') {
        try {
          const r = await fetch('/api/ollama/status');
          if (r.ok) {
            const s = await r.json();
            if (!s.reachable || s.model_ready === false) this.ollamaWarning = s.detail || 'Ollama jest niedostępna.';
          }
        } catch (_) { /* ignore */ }
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
      return this.health?.label || 'model LLM';
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
        `${s.chunks} ${this.partsWord(s.chunks)}`,
        `${this.fmtNum(s.chars)} znaków`,
        `${s.duration_s}s`,
      ].join(' · ');
    },

    partsWord(n) {
      return n === 1 ? 'część' : 'części';
    },

    firstLine(text) {
      const line = (text || '').split('\n').find((l) => l.trim()) || '';
      return line.replace(/^#+\s*/, '').slice(0, 80) || '(bez tytułu)';
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
        this.showError(`Maksymalnie ${this.maxFiles} plików naraz.`);
        return;
      }
      const form = new FormData();
      files.forEach((f) => form.append('files', f));
      try {
        const resp = await fetch('/api/documents', { method: 'POST', body: form });
        const data = await resp.json().catch(() => null);
        if (!resp.ok || !data) {
          this.showError(data?.detail || `Błąd wysyłania plików (HTTP ${resp.status}).`);
          return;
        }
        (data.documents || []).forEach((d) => {
          if (!this.docs.some((x) => x.id === d.id)) this.docs.push(d);
        });
        (data.errors || []).forEach((err) => this.showError(`${err.name}: ${err.error}`));
      } catch (err) {
        this.showError(`Nie udało się połączyć z serwerem: ${err.message}`);
      }
    },

    async removeDoc(id) {
      this.docs = this.docs.filter((d) => d.id !== id);
      this.expanded = null;
      try { await fetch(`/api/documents/${id}`, { method: 'DELETE' }); } catch (_) { /* ignore */ }
    },

    // ---------- oś kroków (Thinking) ----------
    _step(key, text, state) {
      const i = this.steps.findIndex((s) => s.key === key);
      if (i >= 0) {
        this.steps[i].text = text;
        if (state) this.steps[i].state = state;
      } else {
        this.steps.forEach((s) => { if (s.state === 'active') s.state = 'done'; });
        this.steps.push({ key, text, state: state || 'active' });
      }
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
      this.stage = 'Przygotowuję zapytanie...';
      this._step('prepare', 'Łączenie dokumentów');
      this._scrollTo('#thinking-panel');

      const ids = this.docs.map((d) => d.id).join(',');
      const url = `/api/summary/stream?doc_ids=${encodeURIComponent(ids)}&lang=${this.lang}&length=${this.length}`;

      try {
        const resp = await fetch(url, { headers: { Accept: 'text/event-stream' } });
        if (!resp.ok) {
          let detail = `HTTP ${resp.status}`;
          try { detail = (await resp.json()).detail || detail; } catch (_) { /* ignore */ }
          throw new Error(detail);
        }
        await this._readStream(resp);
      } catch (err) {
        this.showError(err.message || 'Połączenie przerwane.');
      } finally {
        this.busy = false;
        this.stage = '';
        this.progress = null;
      }
    },

    async _readStream(resp) {
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let finished = false;

      const handle = (event, raw) => {
        let data;
        try { data = JSON.parse(raw); } catch (_) { return; }

        if (event === 'status') {
          this.stage = data.message || '';
          if (typeof data.total === 'number' && data.total > 0 && typeof data.progress === 'number') {
            this.progress = Math.max(4, Math.round((data.progress / data.total) * 96));
          } else {
            this.progress = null;
          }
          if (data.step === 'prepare') this._step('prepare', 'Łączenie dokumentów');
          else if (data.step === 'chunk') this._step('chunk', data.message || 'Dzielenie na części');
          else if (data.step === 'thinking') this._step('thinking', data.message || 'Analiza modelu');
          else if (data.step === 'synthesize') this._step('synthesize', data.message || 'Scalanie wyniku');
        } else if (event === 'done') {
          finished = true;
          this.steps.forEach((s) => (s.state = 'done'));
          this.summary = data.summary || '';
          this.stats = data.stats || null;
          this.statsFiles = data.files || [];
          this._saveHistory();
          this._scrollTo('#result-panel');
        } else if (event === 'error') {
          finished = true;
          this.showError(data.message || 'Model zwrócił błąd.');
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const block = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          let event = 'message';
          const dataLines = [];
          for (const line of block.split('\n')) {
            if (line.startsWith('event:')) event = line.slice(6).trim();
            else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
          }
          if (dataLines.length) handle(event, dataLines.join('\n'));
          if (finished) return;
        }
      }
      if (!finished) this.showError('Strumień zakończony bez wyniku — sprawdź logi serwera.');
    },

    // ---------- akcje na wyniku ----------
    async copySummary() {
      try {
        await navigator.clipboard.writeText(this.summary);
        this.copied = true;
        setTimeout(() => (this.copied = false), 1800);
      } catch (_) {
        this.showError('Przeglądarka zablokowała kopiowanie do schowka.');
      }
    },

    downloadSummary() {
      const name = this.statsFiles.length === 1
        ? this.statsFiles[0].replace(/\.[^.]+$/, '')
        : 'podsumowanie';
      const blob = new Blob([this.summary], { type: 'text/markdown;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `${name || 'podsumowanie'}-streszczenie.md`;
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
    _loadHistory() {
      try {
        this.history = JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
        if (!Array.isArray(this.history)) this.history = [];
      } catch (_) {
        this.history = [];
      }
    },

    _saveHistory() {
      if (!this.summary || !this.stats) return;
      const item = {
        id: Date.now(),
        date: new Date().toLocaleString('pl-PL', { dateStyle: 'short', timeStyle: 'short' }),
        summary: this.summary.slice(0, 20000),
        stats: this.stats,
        files: this.statsFiles,
      };
      this.history = [item, ...this.history.filter((h) => h.summary !== item.summary)].slice(0, 8);
      try {
        localStorage.setItem(STORE_KEY, JSON.stringify(this.history));
      } catch (_) {
        this.history = this.history.slice(0, 4);
        try { localStorage.setItem(STORE_KEY, JSON.stringify(this.history)); } catch (_) { /* ignore */ }
      }
    },

    loadHistory(h) {
      this.summary = h.summary;
      this.stats = h.stats;
      this.statsFiles = h.files || [];
      this.busy = false;
      this._scrollTo('#result-panel');
    },

    clearHistory() {
      this.history = [];
      try { localStorage.removeItem(STORE_KEY); } catch (_) { /* ignore */ }
    },

    // ---------- pomocnicze ----------
    showError(msg) {
      this.toast = msg;
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => (this.toast = ''), 8000);
    },

    fmtNum(n) {
      return new Intl.NumberFormat('pl-PL').format(n || 0);
    },

    badgeClass(fmt) {
      const map = {
        PDF: 'bg-red-500/15 text-red-300 ring-1 ring-red-400/30',
        DOCX: 'bg-blue-500/15 text-blue-300 ring-1 ring-blue-400/30',
        Markdown: 'bg-violet-500/15 text-violet-300 ring-1 ring-violet-400/30',
        HTML: 'bg-orange-500/15 text-orange-300 ring-1 ring-orange-400/30',
        RTF: 'bg-teal-500/15 text-teal-300 ring-1 ring-teal-400/30',
        TXT: 'bg-slate-500/15 text-slate-300 ring-1 ring-slate-400/30',
      };
      return map[fmt] || map.TXT;
    },

    shortFmt(fmt) {
      return fmt === 'Markdown' ? 'MD' : fmt.toUpperCase();
    },

    _scrollTo(selector) {
      if (window.innerWidth < 1024) {
        setTimeout(() => {
          document.querySelector(selector)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 80);
      }
    },

    _animateDots() {
      this._dotTimer = setInterval(() => {
        this.dots = '.'.repeat((this.dots.length + 1) % 4);
      }, 450);
    },
  };
}
