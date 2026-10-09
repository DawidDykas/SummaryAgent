from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    id: str
    name: str
    format: str
    chars: int
    chunks: int
    words: int
    preview: str


class UploadError(BaseModel):
    name: str
    error: str


class UploadResponse(BaseModel):
    documents: list[DocumentInfo] = Field(default_factory=list)
    errors: list[UploadError] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    provider: str
    model: str
    label: str
    base_url: str
    supported_formats: list[str]


class OllamaStatus(BaseModel):
    reachable: bool
    base_url: str
    model: str
    model_ready: bool | None = None
    models: list[str] = Field(default_factory=list)
    detail: str = ""


class SummaryStats(BaseModel):
    files: int
    chars: int
    chunks: int
    duration_s: float
    provider: str
    model: str
    lang: str
    length: str
