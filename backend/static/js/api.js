/** Klient API - wszystkie wywołania HTTP w jednym miejscu. */

export async function fetchHealth() {
  const resp = await fetch('/api/health');
  return resp.ok ? resp.json() : null;
}

export async function fetchOllamaStatus() {
  const resp = await fetch('/api/ollama/status');
  return resp.ok ? resp.json() : null;
}

export async function uploadDocuments(files) {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  let resp;
  try {
    resp = await fetch('/api/documents', { method: 'POST', body: form });
  } catch (err) {
    throw new Error(`Nie udało się połączyć z serwerem: ${err.message}`);
  }
  const data = await resp.json().catch(() => null);
  if (!resp.ok || !data) {
    throw new Error(data?.detail || `Błąd wysyłania plików (HTTP ${resp.status}).`);
  }
  return data;
}

export async function deleteDocument(id) {
  try {
    await fetch(`/api/documents/${id}`, { method: 'DELETE' });
  } catch (_) {
    /* serwer niedostępny - dokument i tak znika z UI */
  }
}

export function summaryStreamUrl(ids, lang, length) {
  const params = new URLSearchParams({ doc_ids: ids, lang, length });
  return `/api/summary/stream?${params}`;
}

export async function fetchSummaryStream(ids, lang, length) {
  const resp = await fetch(summaryStreamUrl(ids, lang, length), {
    headers: { Accept: 'text/event-stream' },
  });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      detail = (await resp.json()).detail || detail;
    } catch (_) {
      /* odpowiedź nie jest JSONem */
    }
    throw new Error(detail);
  }
  return resp;
}
