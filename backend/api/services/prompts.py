LANG_NAMES = {"pl": "polskim", "en": "angielskim"}


def chunk_prompt(name: str, index: int, total: int, text: str) -> list[dict]:
    system = (
        "Działasz jako analityk dokumentów. Wyciągasz z fragmentu WSZYSTKO istotne: "
        "fakty, liczby, nazwy, terminy, argumenty i wnioski. "
        "Odpowiadasz zwięźle, bez wstępów i grzecznościowych formułek."
    )
    user = (
        f"To fragment {index}/{total} dokumentu \"{name}\".\n"
        f"Wypisz kluczowe informacje z tego fragmentu w formie zwięzłej listy.\n\n"
        f"--- FRAGMENT {index}/{total} ---\n{text}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def final_prompt(
    name: str,
    source: str,
    *,
    lang: str,
    length: str,
    multi: bool,
) -> list[dict]:
    lang_name = LANG_NAMES.get(lang, "polskim")
    length_spec = {
        "short": "ok. 120 słów",
        "standard": "ok. 300 słów",
        "long": "ok. 600 słów",
    }.get(length, "ok. 300 słów")

    system = (
        f"Jesteś doświadczonym analitykiem dokumentów. Odpowiadasz wyłącznie w języku {lang_name}. "
        "Piszesz rzeczowo, konkretnie, bez lania wody. Formatujesz odpowiedź w Markdownie."
    )

    header = (
        f"Przygotuj kompletne podsumowanie dokumentu \"{name}\""
        + (" (połączony z kilku plików)." if multi else ".")
    )
    structure = (
        "Struktura odpowiedzi:\n"
        "## W skrócie\n(3 zdania)\n\n"
        "## Kluczowe punkty\n(lista punktów)\n\n"
        "## Najważniejsze szczegóły\n(fakty, liczby, daty, nazwy)\n\n"
        "## Wnioski\n"
    )
    user = (
        f"{header}\n"
        f"Długość: {length_spec}.\n{structure}\n"
        f"Materiał źródłowy:\n---\n{source}\n---"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def combine_prompt(name: str, partials: list[str], *, lang: str, length: str) -> list[dict]:
    lang_name = LANG_NAMES.get(lang, "polskim")
    length_spec = {
        "short": "ok. 120 słów",
        "standard": "ok. 300 słów",
        "long": "ok. 600 słów",
    }.get(length, "ok. 300 słów")
    system = (
        f"Jesteś doświadczonym analitykiem dokumentów. Odpowiadasz wyłącznie w języku {lang_name}. "
        "Piszesz rzeczowo, konkretnie, bez lania wody. Formatujesz odpowiedź w Markdownie."
    )
    joined = "\n\n".join(
        f"### Część {i}/{len(partials)}\n{p}" for i, p in enumerate(partials, start=1)
    )
    user = (
        f"Poniżej streszczenia poszczególnych części dokumentu \"{name}\". "
        f"Połącz je w jedno, spójne podsumowanie całego dokumentu.\n"
        f"Długość: {length_spec}.\n\n"
        "Struktura odpowiedzi:\n"
        "## W skrócie\n(3 zdania)\n\n"
        "## Kluczowe punkty\n(lista punktów)\n\n"
        "## Najważniejsze szczegóły\n(fakty, liczby, daty, nazwy)\n\n"
        "## Wnioski\n\n"
        f"---\n{joined}\n---"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
