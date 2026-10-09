/** Pomocnicze funkcje prezentacji (bez stanu). */

export function fmtNum(n) {
  return new Intl.NumberFormat('pl-PL').format(n || 0);
}

export function partsWord(n) {
  return n === 1 ? 'część' : 'części';
}

export function firstLine(text) {
  const line = (text || '').split('\n').find((l) => l.trim()) || '';
  return line.replace(/^#+\s*/, '').slice(0, 80) || '(bez tytułu)';
}

const BADGE_CLASSES = {
  PDF: 'bg-red-500/15 text-red-300 ring-1 ring-red-400/30',
  DOCX: 'bg-blue-500/15 text-blue-300 ring-1 ring-blue-400/30',
  Markdown: 'bg-violet-500/15 text-violet-300 ring-1 ring-violet-400/30',
  HTML: 'bg-orange-500/15 text-orange-300 ring-1 ring-orange-400/30',
  RTF: 'bg-teal-500/15 text-teal-300 ring-1 ring-teal-400/30',
  TXT: 'bg-slate-500/15 text-slate-300 ring-1 ring-slate-400/30',
};

export function badgeClass(fmt) {
  return BADGE_CLASSES[fmt] || BADGE_CLASSES.TXT;
}

export function shortFmt(fmt) {
  return fmt === 'Markdown' ? 'MD' : fmt.toUpperCase();
}

export function scrollToPanel(selector) {
  if (window.innerWidth < 1024) {
    setTimeout(() => {
      document.querySelector(selector)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
  }
}
