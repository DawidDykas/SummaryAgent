function summaryApp() {
  return {
    docs: [],
    errors: [],
    busy: false,
    dragging: false,
    lang: 'pl',
    length: 'standard',
    stage: '',
    progress: null,
    dots: '',
    summary: '',
    stats: null,
    statsFiles: [],
    health: null,
    ollamaWarning: '',
    toast: '',
    copied: false,
    maxFileMb: 25,
    maxFiles: 10,
    _dotTimer: null,
    _toastTimer: null,

    async init() {
      this._animateDots();
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

    get statsLabel() {
      if (!this.stats) return '';
      const s = this.stats;
      return [
        `${s.model}`,
        `${s.chunks} ${s.chunks === 1 ? 'część' : 'części'}`,
        `${this.fmtNum(s.chars)} znaków`,
        `${s.duration_s}s`,
      ].join(' · ');
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
      try { await fetch(`/api/documents/${id}`, { method: 'DELETE' }); } catch (_) { /* ignore */ }
    },

    // ---------- summary ----------
    async generate() {
      if (this.busy || !this.docs.length) return;
      this.busy = true;
      this.summary = '';
      this.stats = null;
      this.progress = null;
      this.stage = 'Przygotowuję zapytanie...';

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
        } else if (event === 'done') {
          finished = true;
          this.summary = data.summary || '';
          this.stats = data.stats || null;
          this.statsFiles = data.files || [];
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

    // ---------- akcje ----------
    copySummary() {
      navigator.clipboard?.writeText(this.summary).then(() => {
        this.copied = true;
        setTimeout(() => (this.copied = false), 1800);
      });
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
      this.summary = '';
      this.stats = null;
      this.stage = '';
      this.progress = null;
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    // ---------- pomocnicze ----------
    showError(msg) {
      this.toast = msg;
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => (this.toast = ''), 7000);
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

    _animateDots() {
      this._dotTimer = setInterval(() => {
        this.dots = '.'.repeat((this.dots.length + 1) % 4);
      }, 450);
    },
  };
}
