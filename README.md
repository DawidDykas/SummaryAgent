# SummaryAgent

Wgraj pliki (PDF, DOCX, TXT, MD, HTML, RTF) → kliknij **Summary** → otrzymaj gotowe streszczenie.

- za duże pliki są automatycznie **dzielone na części** i analizowane pojedynczo (map-reduce),
- działa na **lokalnej Ollamie** albo na **dowolnym API zgodnym z OpenAI** —
  jeśli pole `LLM_API_URL` w `.env` jest **puste**, aplikacja **sama przełącza się na Ollamę**,
- frontend z animacją *Thinking*, paskiem postępu i wynikiem w Markdownie.

---

## Szybki start (Docker — zalecany)

```bash
cp .env.example .env        # domyślnie LLM_API_URL puste => Ollama
docker compose up -d --build
```

Przy pierwszym starcie komplet pobiera model `llama3.2` (~2 GB).

Otwórz **http://localhost:8000**

> **GPU:** Ollama startuje domyślnie z GPU (NVIDIA) — sekcja `deploy` w `docker-compose.yml`.
> Bez karty NVIDIA usuń ten blok z pliku.

> Chcesz tylko API (bez lokalnego modelu)? `docker compose up -d --build api --no-deps`

### Wyłączenie Ollamy, użycie własnego API

W `.env` wpisz:

```bash
LLM_API_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

i uruchom sam backend: `docker compose up -d --build api --no-deps`

---

## Start bez Dockera

```bash
cp .env.example .env
uv sync --all-groups       # zależności + narzędzia dev (pytest, ruff)
uv run uvicorn backend.api.main:app --reload --port 8000
```

Ollama musi wtedy działać lokalnie (`ollama serve`) z portu `11434` —
ustaw to w `.env` (`OLLAMA_BASE_URL`) oraz pobierz model: `ollama pull llama3.2`.

### Testy i lint

```bash
uv run pytest              # testy jednostkowe + integracyjne (bez sieci/LMM)
uv run ruff check backend tests
```

---

## Obsługiwane formaty

| Rozszerzenie | Format |
|---|---|
| `.pdf` | PDF (wymagana warstwa tekstowa — nie skan) |
| `.docx` | Word (akapity + tabele) |
| `.txt` | Tekst |
| `.md`, `.markdown` | Markdown |
| `.html`, `.htm` | HTML |
| `.rtf` | RTF |

Nowy format = jeden wpis w rejestrze (`backend/adapters/extractors`):

```python
from backend.adapters.extractors import register
register(".odt", "ODT", my_extractor)  # extractor: Callable[[bytes], str]
```

---

## API

| Metoda | Endpoint | Opis |
|---|---|---|
| `GET` | `/api/health` | aktywny provider (API / Ollama), model, formaty |
| `POST` | `/api/documents` | upload plików (`multipart`, pole `files`) → ekstrakcja tekstu |
| `DELETE` | `/api/documents/{id}` | usunięcie dokumentu |
| `GET` | `/api/summary/stream` | strumień SSE: `status` → `done` / `error` |
| `GET` | `/api/ollama/status` | czy Ollama odpowiada i czy model jest pobrany |
| `GET` | `/docs` | dokumentacja Swagger |

Każda odpowiedź zawiera nagłówek `X-Request-ID` (propagowany z żądania lub
generowany) — przydaje się do korelacji w logach.

Przykładowe wywołanie strumienia:

```
GET /api/summary/stream?doc_ids=abc123,def456&lang=pl&length=standard
```

Parametr `length` (objętość podsumowania): `short` (~120 słów), `standard` (~300),
`long` (~600), `xl` (~1200 słów). Duże pliki są dzielone na części i analizowane
**równolegle** (domyślnie 2 naraz — patrz `SUMMARY_CONCURRENCY`).

---

## Konfiguracja (`.env`)

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `LLM_API_URL` | *(puste)* | adres API zgodnego z OpenAI; **puste = Ollama** |
| `LLM_API_KEY` | *(puste)* | klucz do API (jeśli wymagane) |
| `LLM_MODEL` | `gpt-4o-mini` | model dla zewnętrznego API |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | adres Ollamy (w compose: `http://ollama:11434`) |
| `OLLAMA_MODEL` | `llama3.2` | model Ollamy |
| `CHUNK_SIZE` | `12000` | ile znaków na część przy dzieleniu dużych plików |
| `CHUNK_OVERLAP` | `400` | nakładanie się części |
| `SUMMARY_CONCURRENCY` | `2` | ile części dużego dokumentu analizować równolegle (1–8) |
| `MAX_FILE_SIZE_MB` | `25` | limit rozmiaru pliku |
| `MAX_FILES` | `10` | limit plików na żądanie |
| `DOC_TTL_SECONDS` | `3600` | jak długo dokumenty żyją w pamięci |
| `LOG_LEVEL` | `INFO` | poziom logów (`DEBUG`…`CRITICAL`) |
| `LOG_JSON` | `false` | `true` = logi w formacie JSON (produkcja) |

Wszystkie wartości są **walidowane przy starcie** (pydantic) — błąd w `.env`
zatrzymuje aplikację z czytelnym komunikatem, zamiast działać nieprzewidywalnie.

---

## Struktura projektu

Architektura w stylu hexagonalnym: `core` (logika) nie importuje FastAPI,
`adapters` (infrastruktura) realizuje porty z `core`, `api` tylko przepina.

```
backend/
  core/                  # logika domenowa - bez zależności od FastAPI
    config.py            # Settings (.env) z walidacją
    exceptions.py        # hierarchia błędów -> mapowana na HTTP w api/
    logging.py           # konfiguracja structlog
    models.py            # StoredDocument
    chunking.py          # dzielenie dużych tekstów
    prompts.py           # prompty (części + finalne)
    ports/               # kontrakty (Protocol)
      llm.py             #   LLMClient
      store.py           #   DocumentStore
      extractor.py       #   TextExtractor
    services/            # orchestration (testowalne bez HTTP)
      documents.py       #   upload: walidacja → ekstrakcja → chunking → store
      summary.py         #   map-reduce + strumień zdarzeń status/done/error
  adapters/              # implementacje portów
    llm/                 # OpenAI-compat, Ollama + retry + fabryka
    store/               # magazyn in-memory (+ fabryka pod kolejne)
    extractors/          # rejestr formatów (PDF, DOCX, ...)
  api/                   # warstwa transportowa (FastAPI)
    main.py              # app + lifespan (zasoby) + exception handlery
    dependencies.py      # wstrzykiwanie zależności (Depends)
    middleware.py        # X-Request-ID + log żądań
    schemas.py           # modele odpowiedzi API
    routers/             # documents, summary (SSE), ollama
  static/
    index.html           # UI (Tailwind + Alpine.js)
    js/                  # moduły ES: app, api, sse, history, ui
tests/                   # pytest: jednostkowe, integracyjne (fake LLM)
```

### Dodawanie nowego providera LLM

1. Nowy plik w `backend/adapters/llm/` z klasą realizującą `LLMClient`
   (`chat()` + `close()`).
2. Fabryka `backend/adapters/llm/__init__.py` wybiera implementację na podstawie
   `Settings` — żadna zmiana w routerach ani serwisach.

### Dodawanie nowego magazynu (np. Redis)

1. Nowy plik w `backend/adapters/store/` realizujący `DocumentStore`.
2. Fabryka `create_store()` w `backend/adapters/store/__init__.py`.
