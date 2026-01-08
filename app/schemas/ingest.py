# app/repos/ingest.py
from pydantic import BaseModel, Field, model_validator
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

    @model_validator(mode="after")
    def validate_ingestion_source(self):
        if self.fileUrl and self.sourceUrl:
            raise ValueError("Provide ONLY ONE of fileUrl or sourceUrl")

        if not self.fileUrl and not self.sourceUrl:
            raise ValueError("Either fileUrl (PDF) or sourceUrl (WEB) is required")

        return self

    def ingest_type(self) -> str:
        return "pdf" if self.fileUrl else "web"


class IngestResponse(BaseModel):
    jobId: str
    convId: str
    status: str
