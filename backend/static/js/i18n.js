/** Słowniki interfejsu (PL/EN) + prosta interpolacja {zmienna}.

 * Klucz = identyfikator w HTML (x-text="t('klucz')") i w app.js.
 * brakujący klucz -> zwraca sam klucz (widoczny sygnał do uzupełnienia).
 */

const DICT = {
  pl: {
    'meta.title': 'SummaryAgent — podsumowanie dokumentów AI',
    'meta.description':
      'Wgraj pliki (PDF, DOCX, TXT, MD, HTML, RTF) i otrzymaj ich podsumowanie od modelu LLM.',
    tagline: 'dokumenty → podsumowanie AI',
    'nav.upload': 'Wgraj pliki',
    'lang.title': 'Język interfejsu: {name}',
    'hero.title':
      'Wrzuć pliki. Kliknij <span class="grad-text">Summary</span>.<br class="hidden sm:block"> Odbierz gotowe streszczenie.',
    'drop.title': 'Przeciągnij pliki tutaj',
    'drop.or': 'lub',
    'drop.choose': 'wybierz z dysku',
    'drop.max': 'max {mb} MB / plik · do {n} plików',
    'files.label': 'Pliki',
    'files.clearAll': 'wyczyść wszystko',
    'doc.chars': 'zn.',
    'doc.words': 'sł.',
    'doc.split': 'podzielony',
    'a11y.preview': 'Podgląd',
    'a11y.remove': 'Usuń',
    'settings.summaryLang': 'Język podsumowania',
    'settings.length': 'Objętość',
    'length.short': 'Zwięzłe (~120 słów)',
    'length.standard': 'Standard (~300 słów)',
    'length.long': 'Szczegółowe (~600 słów)',
    'length.xl': 'Obszerne (~1200 słów)',
    'stats.files': '{n} plik(ów)',
    'stats.chars': 'znaków',
    'cta.generating': 'Generowanie…',
    'history.title': 'Ostatnie podsumowania',
    'history.clear': 'wyczyść',
    'history.meta': '{date} · {n} plik(ów) · {model}',
    'start.title': 'Gotowy do streszczenia',
    'start.readyDocs':
      'Wgrane pliki czekają po lewej stronie — kliknij Summary, aby uruchomić model.',
    'start.uploadDocs':
      'Wgraj dokumenty po lewej stronie. Obsługujemy PDF, DOCX, TXT, MD, HTML i RTF.',
    'how.1.t': 'Wgraj pliki',
    'how.1.d': 'Drag & drop lub wybór z dysku — także kilka naraz.',
    'how.2.t': 'Model analizuje',
    'how.2.d': 'Duże pliki są dzielone na części i liczone pojedynczo.',
    'how.3.t': 'Odbierz streszczenie',
    'how.3.d': 'Markdown: w skrócie, kluczowe punkty, wnioski.',
    'thinking.preparing': 'Przygotowuję...',
    'thinking.inProgress': 'analiza w toku',
    'result.title': 'Podsumowanie',
    'result.copy': 'Kopiuj',
    'result.copied': 'Skopiowano!',
    'result.new': 'Nowe',
    'result.source': 'Źródło:',
    footer:
      'SummaryAgent · Ollama lub dowolne API zgodne z OpenAI (ustawienia w <code class="text-slate-500">.env</code>) · dokumenty przechowywane tylko w pamięci serwera',
    'provider.fallback': 'model LLM',
    'stage.preparing': 'Przygotowuję zapytanie...',
    'step.prepare': 'Łączenie dokumentów',
    'step.chunk': 'Dzielenie na części',
    'step.thinking': 'Analiza modelu',
    'step.synthesize': 'Scalanie wyniku',
    'err.maxFiles': 'Maksymalnie {n} plików naraz.',
    'err.ollama': 'Ollama jest niedostępna.',
    'err.model': 'Model zwrócił błąd.',
    'err.stream': 'Strumień zakończony bez wyniku — sprawdź logi serwera.',
    'err.connection': 'Połączenie przerwane.',
    'err.clipboard': 'Przeglądarka zablokowała kopiowanie do schowka.',
    'err.uploadHttp': 'Błąd wysyłania plików (HTTP {status}).',
    'err.serverConn': 'Nie udało się połączyć z serwerem: {msg}',
    'file.summary': 'podsumowanie',
    'file.suffix': '-streszczenie',
  },
  en: {
    'meta.title': 'SummaryAgent — AI document summaries',
    'meta.description':
      'Upload files (PDF, DOCX, TXT, MD, HTML, RTF) and get their summary from an LLM.',
    tagline: 'documents → AI summary',
    'nav.upload': 'Upload files',
    'lang.title': 'UI language: {name}',
    'hero.title':
      'Drop files. Click <span class="grad-text">Summary</span>.<br class="hidden sm:block"> Get your summary.',
    'drop.title': 'Drop files here',
    'drop.or': 'or',
    'drop.choose': 'choose from disk',
    'drop.max': 'max {mb} MB / file · up to {n} files',
    'files.label': 'Files',
    'files.clearAll': 'clear all',
    'doc.chars': 'ch.',
    'doc.words': 'w.',
    'doc.split': 'split',
    'a11y.preview': 'Preview',
    'a11y.remove': 'Remove',
    'settings.summaryLang': 'Summary language',
    'settings.length': 'Length',
    'length.short': 'Short (~120 words)',
    'length.standard': 'Standard (~300 words)',
    'length.long': 'Detailed (~600 words)',
    'length.xl': 'Extensive (~1200 words)',
    'stats.files': '{n} file(s)',
    'stats.chars': 'chars',
    'cta.generating': 'Generating…',
    'history.title': 'Recent summaries',
    'history.clear': 'clear',
    'history.meta': '{date} · {n} file(s) · {model}',
    'start.title': 'Ready to summarize',
    'start.readyDocs':
      'Uploaded files are waiting on the left — click Summary to run the model.',
    'start.uploadDocs':
      'Upload documents on the left. We support PDF, DOCX, TXT, MD, HTML and RTF.',
    'how.1.t': 'Upload files',
    'how.1.d': 'Drag & drop or pick from disk — multiple files welcome.',
    'how.2.t': 'The model analyzes',
    'how.2.d': 'Large files are split into parts and processed one by one.',
    'how.3.t': 'Get the summary',
    'how.3.d': 'Markdown: in short, key points, conclusions.',
    'thinking.preparing': 'Preparing...',
    'thinking.inProgress': 'analysis in progress',
    'result.title': 'Summary',
    'result.copy': 'Copy',
    'result.copied': 'Copied!',
    'result.new': 'New',
    'result.source': 'Source:',
    footer:
      'SummaryAgent · Ollama or any OpenAI-compatible API (configured in <code class="text-slate-500">.env</code>) · documents kept in server memory only',
    'provider.fallback': 'LLM model',
    'stage.preparing': 'Preparing request...',
    'step.prepare': 'Combining documents',
    'step.chunk': 'Splitting into parts',
    'step.thinking': 'Model analysis',
    'step.synthesize': 'Combining results',
    'err.maxFiles': 'Maximum {n} files at once.',
    'err.ollama': 'Ollama is unavailable.',
    'err.model': 'The model returned an error.',
    'err.stream': 'Stream ended without a result — check server logs.',
    'err.connection': 'Connection lost.',
    'err.clipboard': 'The browser blocked clipboard access.',
    'err.uploadHttp': 'File upload error (HTTP {status}).',
    'err.serverConn': 'Could not connect to the server: {msg}',
    'file.summary': 'summary',
    'file.suffix': '-summary',
  },
};

export function tr(lang, key, vars) {
  const table = DICT[lang] || DICT.pl;
  let text = table[key];
  if (text === undefined) text = DICT.pl[key];
  if (text === undefined) return key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
  }
  return text;
}

/** Znane nagłówki sekcji streszczenia -> odpowiednik w języku UI (historia). */
const HEADING_CANON = {
  'w skrócie': { pl: 'W skrócie', en: 'In brief' },
  'kluczowe punkty': { pl: 'Kluczowe punkty', en: 'Key points' },
  'najważniejsze szczegóły': { pl: 'Najważniejsze szczegóły', en: 'Key details' },
  'wnioski': { pl: 'Wnioski', en: 'Conclusions' },
  'in brief': { pl: 'W skrócie', en: 'In brief' },
  'in short': { pl: 'W skrócie', en: 'In brief' },
  summary: { pl: 'W skrócie', en: 'In brief' },
  'key points': { pl: 'Kluczowe punkty', en: 'Key points' },
  'key takeaways': { pl: 'Kluczowe punkty', en: 'Key points' },
  'key details': { pl: 'Najważniejsze szczegóły', en: 'Key details' },
  'important details': { pl: 'Najważniejsze szczegóły', en: 'Key details' },
  'most important details': { pl: 'Najważniejsze szczegóły', en: 'Key details' },
  conclusions: { pl: 'Wnioski', en: 'Conclusions' },
  conclusion: { pl: 'Wnioski', en: 'Conclusions' },
};

/** Pierwsza linia streszczenia przetłumaczona na język UI (dla historii). */
export function heading(lang, line) {
  const canon = HEADING_CANON[String(line || '').trim().toLowerCase()];
  if (!canon) return line;
  return canon[lang] || canon.pl;
}
