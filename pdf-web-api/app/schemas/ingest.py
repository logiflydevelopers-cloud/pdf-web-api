# app/repos/ingest.py
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
    sourceUrl: Optional[str] = Field(
        None,
        description="Website URL to scrape"
    )

    prompt: Optional[str] = Field(
        None,
        description="Optional instruction for summarization or focus"
    )

    def ingest_type(self) -> str:
        """
        Helper to detect ingestion type.
        """
        if self.fileUrl:
            return "pdf"
        if self.sourceUrl:
            return "web"
        raise ValueError("Either fileUrl (PDF) or sourceUrl (WEB) is required")


class IngestResponse(BaseModel):
    jobId: str
    convId: str
    status: str
