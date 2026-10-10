def _best_cut(window: str) -> int:
    """Return the index of the best place to cut inside the window.

    Args:
        window: Text slice to search for a separator.

    Returns:
        Index just after the last separator found in the second half of the
        window, or ``len(window)`` when no suitable separator exists.
    """
    for sep in ("\n\n", "\n", ". ", " ", "; "):
        pos = window.rfind(sep)
        if pos > len(window) // 2:
            return pos + len(sep)
    return len(window)


def split_text(text: str, size: int, overlap: int = 0) -> list[str]:
    """Split text into chunks of at most ``size`` characters with overlap.

    Large files are fed to the model in portions - this keeps every prompt
    within the context limit while still covering the whole document.

    Args:
        text: Source text to split (stripped first).
        size: Maximum chunk length in characters; must be > 0.
        overlap: Characters shared between neighbouring chunks; clamped
            to at most ``size // 2``.

    Returns:
        Chunks in original order; empty list for empty input.

    Raises:
        ValueError: If ``size`` is not positive.
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
