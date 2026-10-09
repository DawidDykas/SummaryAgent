from fastapi import APIRouter, Depends, File, UploadFile

from backend.api.dependencies import (
    get_document_service,
    get_settings,
    get_store,
)
from backend.api.schemas import DocumentInfo, UploadError, UploadResponse
from backend.core.config import Settings
from backend.core.exceptions import BadRequestError, DocumentNotFoundError
from backend.core.models import StoredDocument
from backend.core.ports.store import DocumentStore
from backend.core.services.documents import DocumentService

router = APIRouter(prefix="/api", tags=["documents"])


def _info(doc: StoredDocument) -> DocumentInfo:
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
async def upload_documents(
    files: list[UploadFile] = File(...),
    settings: Settings = Depends(get_settings),
    service: DocumentService = Depends(get_document_service),
) -> UploadResponse:
    if not files:
        raise BadRequestError("Nie przesłano żadnych plików.")

    limit = settings.max_file_size_mb * 1024 * 1024
    items: list[tuple[str, bytes]] = []
    for upload in files:
        name = (upload.filename or "bez_nazwy").strip() or "bez_nazwy"
        items.append((name, await upload.read(limit + 1)))

    results = await service.upload(items)

    response = UploadResponse()
    for result in results:
        if result.document is not None:
            response.documents.append(_info(result.document))
        else:
            response.errors.append(
                UploadError(name=result.name, error=result.error or "Nie udało się przetworzyć pliku.")
            )

    if not response.documents and not response.errors:
        response.errors.append(UploadError(name="-", error="Nie udało się przetworzyć plików."))
    return response


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    store: DocumentStore = Depends(get_store),
) -> dict:
    if not store.delete(doc_id):
        raise DocumentNotFoundError(doc_id, message="Dokument nie istnieje.")
    return {"deleted": doc_id}


__all__ = ["router"]
