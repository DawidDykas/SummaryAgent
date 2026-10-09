def _best_cut(window: str) -> int:
    """Zwraca indeks najlepszego miejsca do podziału wewnątrz okna."""
    for sep in ("\n\n", "\n", ". ", " ", "; "):
        pos = window.rfind(sep)
        if pos > len(window) // 2:
            return pos + len(sep)
    return len(window)


def split_text(text: str, size: int, overlap: int = 0) -> list[str]:
    """Dzieli tekst na części <= size znaków z nakładaniem się (overlap).

    Duże pliki trafiają do modelu porcjami - dzięki temu nie przekraczamy
    limitu kontekstu i dostajemy kompletne podsumowanie.
    """
    text = text.strip()
    if size <= 0:
        raise ValueError("chunk_size musi być > 0")
    if len(text) <= size:
        return [text] if text else []

    overlap = max(0, min(overlap, size // 2))
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            end = start + _best_cut(text[start:end])
            end = min(end, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, end - size + 1, start + 1)
    return chunks


def count_words(text: str) -> int:
    return len(text.split())
