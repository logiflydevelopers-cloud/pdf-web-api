from google.cloud import firestore
from datetime import datetime
import os

class FirestoreRepo:

    def save(self, pdfId: str, data: dict):
        data["updatedAt"] = datetime.utcnow()
        db.collection("pdfs").document(pdfId).set(data)

    def get(self, pdfId: str):
        doc = db.collection("pdfs").document(pdfId).get()
        return doc.to_dict() if doc.exists else None

    def fail(self, pdfId: str, error: str):
        self.save(pdfId, {
            "status": "failed",
            "error": error
        })

