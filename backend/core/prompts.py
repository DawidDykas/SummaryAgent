LANG_NAMES = {"pl": "Polish", "en": "English"}

LENGTH_SPECS = {
    "short": "about 120 words",
    "standard": "about 300 words",
    "long": "about 600 words",
    "xl": "about 1200 words",
}
DEFAULT_LENGTH = "standard"

# per-length response token budget
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


def _structure(lang: str = "pl") -> str:
    """Section headings in the summary language (not the interface language)."""
    if lang == "en":
        return (
            "Response structure:\n"
            "## In brief\n(3 sentences)\n\n"
            "## Key points\n(bullet list)\n\n"
            "## Key details\n(facts, numbers, dates, names)\n\n"
            "## Conclusions\n"
        )
    return (
        "Struktura odpowiedzi:\n"
        "## W skrócie\n(3 zdania)\n\n"
        "## Kluczowe punkty\n(lista punktów)\n\n"
        "## Najważniejsze szczegóły\n(fakty, liczby, daty, nazwy)\n\n"
        "## Wnioski\n"
    )


def _system(lang: str) -> str:
    return (
        f"You are an experienced document analyst. Reply exclusively in { _language_name(lang) }. "
        "Write factually and concretely, without fluff. Format the reply in Markdown."
    )


def chunk_prompt(name: str, index: int, total: int, text: str) -> list[dict]:
    system = (
        "You act as a document analyst. Extract EVERYTHING essential from the fragment: "
        "facts, numbers, names, dates, arguments and conclusions. "
        "Reply concisely, without introductions or polite formulas."
    )
    user = (
        f"This is fragment {index}/{total} of the document \"{name}\".\n"
        f"List the key information from this fragment as a concise bullet list.\n\n"
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
        f"Prepare a complete summary of the document \"{name}\""
        + (" (combined from multiple files)." if multi else ".")
    )
    user = (
        f"{header}\n"
        f"Length: {length_spec(length)}.\n{_structure(lang)}\n"
        f"Source material:\n---\n{source}\n---"
    )
    return [{"role": "system", "content": _system(lang)}, {"role": "user", "content": user}]


def combine_prompt(name: str, partials: list[str], *, lang: str, length: str) -> list[dict]:
    joined = "\n\n".join(
        f"### Part {i}/{len(partials)}\n{p}" for i, p in enumerate(partials, start=1)
    )
    user = (
        f"Below are summaries of the individual parts of the document \"{name}\". "
        f"Combine them into one coherent summary of the whole document.\n"
        f"Length: {length_spec(length)}.\n\n"
        f"{_structure(lang)}\n"
        f"---\n{joined}\n---"
    )
    return [{"role": "system", "content": _system(lang)}, {"role": "user", "content": user}]
