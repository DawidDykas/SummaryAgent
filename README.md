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

> **GPU (NVIDIA):** `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build`
> — osobny plik `docker-compose.gpu.yml` dokłada rezerwację GPU do Ollamy.

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
uv sync                       # lub: pip install -e .
uv run uvicorn backend.api.main:app --reload --port 8000
```

Ollama musi wtedy działać lokalnie (`ollama serve`) z portu `11434` —
ustaw to w `.env` (`OLLAMA_BASE_URL`) oraz pobierz model: `ollama pull llama3.2`.

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

Przykładowe wywołanie strumienia:

```
GET /api/summary/stream?doc_ids=abc123,def456&lang=pl&length=standard
```

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
| `MAX_FILE_SIZE_MB` | `25` | limit rozmiaru pliku |
| `MAX_FILES` | `10` | limit plików na żądanie |
| `DOC_TTL_SECONDS` | `3600` | jak długo dokumenty żyją w pamięci |

---

## Struktura projektu

```
backend/
  api/
    main.py           # FastAPI + statyka
    config.py         # ustawienia z .env
    schemas.py        # modele odpowiedzi
    routers/
      documents.py    # upload / usuwanie plików
      summary.py      # strumień SSE z podsumowaniem
      ollama.py       # status Ollamy
    services/
      extractors.py   # PDF/DOCX/TXT/MD/HTML/RTF → tekst
      chunker.py      # dzielenie dużych tekstów
      llm.py          # klient API + Ollama (z ponowieniami)
      prompts.py      # prompty (części + finalne)
      store.py        # magazyn dokumentów w pamięci (TTL)
  static/
    index.html        # UI (Tailwind + Alpine.js)
    app.js            # logika: upload, SSE, Rendering MD
Dockerfile
docker-compose.yml
.env.example
```
