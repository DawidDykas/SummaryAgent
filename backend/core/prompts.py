LANG_NAMES = {"pl": "polskim", "en": "angielskim"}

LENGTH_SPECS = {
    "short": "ok. 120 słów",
    "standard": "ok. 300 słów",
    "long": "ok. 600 słów",
    "xl": "ok. 1200 słów",
}
DEFAULT_LENGTH = "standard"

# limity tokenów na odpowiedź zależne od wybranej objętości
FINAL_MAX_TOKENS = {
    "short": 900,
    "standard": 1500,
    "long": 2200,
    "xl": 3400,
}


def length_spec(length: str) -> str:
    return LENGTH_SPECS.get(length, LENGTH_SPECS[DEFAULT_LENGTH])


def final_max_tokens(length: str) -> int:
    return FINAL_MAX_TOKENS.get(length, FINAL_MAX_TOKENS[DEFAULT_LENGTH])


def _language_name(lang: str) -> str:
    return LANG_NAMES.get(lang, LANG_NAMES["pl"])


def _structure() -> str:
    return (
        "Struktura odpowiedzi:\n"
        "## W skrócie\n(3 zdania)\n\n"
        "## Kluczowe punkty\n(lista punktów)\n\n"
        "## Najważniejsze szczegóły\n(fakty, liczby, daty, nazwy)\n\n"
        "## Wnioski\n"
    )


def _system(lang: str) -> str:
    return (
        f"Jesteś doświadczonym analitykiem dokumentów. Odpowiadasz wyłącznie w języku {_language_name(lang)}. "
        "Piszesz rzeczowo, konkretnie, bez lania wody. Formatujesz odpowiedź w Markdownie."
    )


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
    header = (
        f"Przygotuj kompletne podsumowanie dokumentu \"{name}\""
        + (" (połączony z kilku plików)." if multi else ".")
    )
    user = (
        f"{header}\n"
        f"Długość: {length_spec(length)}.\n{_structure()}\n"
        f"Materiał źródłowy:\n---\n{source}\n---"
    )
    return [{"role": "system", "content": _system(lang)}, {"role": "user", "content": user}]


def combine_prompt(name: str, partials: list[str], *, lang: str, length: str) -> list[dict]:
    joined = "\n\n".join(
        f"### Część {i}/{len(partials)}\n{p}" for i, p in enumerate(partials, start=1)
    )
    user = (
        f"Poniżej streszczenia poszczególnych części dokumentu \"{name}\". "
        f"Połącz je w jedno, spójne podsumowanie całego dokumentu.\n"
        f"Długość: {length_spec(length)}.\n\n"
        f"{_structure()}\n"
        f"---\n{joined}\n---"
    )
    return [{"role": "system", "content": _system(lang)}, {"role": "user", "content": user}]
