from pydantic import BaseModel, Field
from typing import Optional


class IngestRequest(BaseModel):
    """
    Unified ingestion request.
    Handles BOTH:
    - PDF ingestion
    - Website scraping ingestion
    """

    userId: str = Field(..., description="Authenticated user ID")
    convId: str = Field(..., description="Conversation / document ID")

    # -------------------------
    # PDF ingestion
    # -------------------------
    fileUrl: Optional[str] = Field(
        None,
        description="Public URL of the PDF (Firebase / S3 / HTTPS)"
    )

    storagePath: Optional[str] = Field(
        None,
        description="Internal storage path (optional, future use)"
    )

    fileName: Optional[str] = Field(
        None,
        description="Original file name"
    )

    # -------------------------
    # Web ingestion
    # -------------------------
    prompt: Optional[str] = Field(
        None,
        description="Website URL OR instruction prompt for web scraping"
    )

    def ingest_type(self) -> str:
        """
        Helper to detect ingestion type.
        """
        if self.fileUrl:
            return "pdf"
        if self.prompt:
            return "web"
        raise ValueError("Either fileUrl (PDF) or prompt (WEB) is required")


class IngestResponse(BaseModel):
    jobId: str
    convId: str
    status: str
