import asyncio

from fastapi import APIRouter, File, UploadFile

from backend.api.config import get_settings
from backend.api.schemas import DocumentInfo, UploadError, UploadResponse
from backend.api.services.chunker import split_text
from backend.api.services.extractors import ACCEPT, ExtractionError, extract_text, format_of
from backend.api.services.store import store
from backend.core.exceptions import BadRequestError, DocumentNotFoundError

router = APIRouter(prefix="/api", tags=["documents"])


def _info(doc) -> DocumentInfo:
    return DocumentInfo(
        id=doc.id,
        name=doc.name,
        format=doc.fmt,
        chars=doc.chars,
        words=doc.words,
        chunks=doc.chunks,
        preview=doc.text[:240],
    )


@router.post("/documents", response_model=UploadResponse)
async def upload_documents(files: list[UploadFile] = File(...)) -> UploadResponse:
    settings = get_settings()
    if not files:
        raise BadRequestError("Nie przesłano żadnych plików.")
    if len(files) > settings.max_files:
        raise BadRequestError(f"Za dużo plików naraz - maksymalnie {settings.max_files}.")

    limit = settings.max_file_size_mb * 1024 * 1024
    response = UploadResponse()

    for upload in files:
        name = (upload.filename or "bez_nazwy").strip() or "bez_nazwy"
        if format_of(name) is None:
            response.errors.append(
                UploadError(name=name, error="Nieobsługiwany format pliku.")
            )
            continue
        data = await upload.read(limit + 1)
        if len(data) > limit:
            response.errors.append(
                UploadError(
                    name=name,
                    error=f"Plik przekracza limit {settings.max_file_size_mb} MB.",
                )
            )
            continue
        if not data:
            response.errors.append(UploadError(name=name, error="Plik jest pusty."))
            continue
        try:
            fmt, text = await asyncio.to_thread(extract_text, name, data)
        except ExtractionError as exc:
            response.errors.append(UploadError(name=name, error=str(exc)))
            continue
        except Exception:
            response.errors.append(
                UploadError(name=name, error="Nie udało się odczytać pliku.")
            )
            continue

        chunks = split_text(text, settings.chunk_size, settings.chunk_overlap)
        doc = store.put(name, fmt, text, chunks=len(chunks))
        response.documents.append(_info(doc))

    if not response.documents and not response.errors:
        response.errors.append(UploadError(name="-", error="Nie udało się przetworzyć plików."))
    return response


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str) -> dict:
    if not store.delete(doc_id):
        raise DocumentNotFoundError(doc_id, message="Dokument nie istnieje.")
    return {"deleted": doc_id}


__all__ = ["router", "ACCEPT"]
