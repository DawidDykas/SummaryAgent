/** Summary history in localStorage (max 8 entries). */

const STORE_KEY = 'summaryagent.history';

export function loadStoredHistory() {
  try {
    const history = JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
    return Array.isArray(history) ? history : [];
  } catch (_) {
    return [];
  }
}

export function saveStoredHistory(item) {
  let history = [item, ...loadStoredHistory().filter((h) => h.summary !== item.summary)].slice(0, 8);
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(history));
  } catch (_) {
    /* out of space - trim and try again */
    history = history.slice(0, 4);
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(history));
    } catch (_) {
      /* still no space - keep history in memory only */
    }
  }
  return history;
}

export function clearStoredHistory() {
  try {
    localStorage.removeItem(STORE_KEY);
  } catch (_) {
    /* ignore */
  }
}
