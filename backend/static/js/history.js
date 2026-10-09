/** Historia podsumowań w localStorage (max 8 wpisów). */

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
    /* brak miejsca - skracamy i próbujemy ponownie */
    history = history.slice(0, 4);
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(history));
    } catch (_) {
      /* dalej brak - zostawiamy tylko w pamięci */
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
