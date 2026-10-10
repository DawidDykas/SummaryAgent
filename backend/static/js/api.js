/** API client - all HTTP calls in one place. */

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
    const e = new Error(err.message);
    e.i18nKey = 'err.serverConn';
    e.i18nParams = { msg: err.message };
    throw e;
  }
  const data = await resp.json().catch(() => null);
  if (!resp.ok || !data) {
    if (data?.detail) throw new Error(data.detail);
    const e = new Error(`HTTP ${resp.status}`);
    e.i18nKey = 'err.uploadHttp';
    e.i18nParams = { status: resp.status };
    throw e;
  }
  return data;
}

export async function deleteDocument(id) {
  try {
    await fetch(`/api/documents/${id}`, { method: 'DELETE' });
  } catch (_) {
    /* server unavailable - the document disappears from the UI anyway */
  }
}

export function summaryStreamUrl(ids, lang, length, uiLang) {
  const params = new URLSearchParams({ doc_ids: ids, lang, length, ui_lang: uiLang });
  return `/api/summary/stream?${params}`;
}

export async function fetchSummaryStream(ids, lang, length, uiLang) {
  const resp = await fetch(summaryStreamUrl(ids, lang, length, uiLang), {
    headers: { Accept: 'text/event-stream' },
  });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      detail = (await resp.json()).detail || detail;
    } catch (_) {
      /* response is not JSON */
    }
    throw new Error(detail);
  }
  return resp;
}
