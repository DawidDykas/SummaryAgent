"""Testy spójności pakietów: re-eksporty i granice warstw."""

import importlib
import pkgutil
import sys


def _iter_modules(package: str) -> list[str]:
    pkg = importlib.import_module(package)
    names = [package]
    for info in pkgutil.walk_packages(pkg.__path__, prefix=package + "."):
        names.append(info.name)
    return names


def test_core_ports_reexport_protocols():
    from backend.core.ports import DocumentStore, LLMClient, Message, TextExtractor

    for obj in (DocumentStore, LLMClient, TextExtractor):
        assert obj.__module__.startswith("backend.core.ports")
    assert Message == dict[str, str]


def test_core_services_reexport_services():
    from backend.core.services import DocumentService, Event, FileResult, SummaryService

    assert DocumentService.__module__ == "backend.core.services.documents"
    assert SummaryService.__module__ == "backend.core.services.summary"
    assert FileResult.__module__ == "backend.core.services.documents"
    assert Event  # alias typu - obecność wystarczy


def test_schemas_live_in_api_layer():
    """Modele odpowiedzi HTTP należą do warstwy API, nie core."""
    from backend.api import schemas

    for name in ("DocumentInfo", "UploadError", "UploadResponse", "HealthResponse", "OllamaStatus"):
        obj = getattr(schemas, name)
        assert obj.__module__ == "backend.api.schemas", name


def test_core_modules_do_not_import_fastapi():
    """Logika domenowa musi pozostać niezależna od FastAPI/Starlette."""
    for mod in _iter_modules("backend.core"):
        importlib.import_module(mod)

    offenders = []
    for mod in _iter_modules("backend.core"):
        module = sys.modules.get(mod)
        if module is None:
            continue
        for value in vars(module).values():
            origin = getattr(value, "__module__", "")
            if origin.startswith(("fastapi", "starlette")):
                offenders.append(f"{mod} -> {origin}")
    assert not offenders, offenders


def test_all_backend_modules_import_cleanly():
    """Każdy moduł w paczce backend da się zaimportować (brak cykli importów)."""
    for name in _iter_modules("backend"):
        importlib.import_module(name)
