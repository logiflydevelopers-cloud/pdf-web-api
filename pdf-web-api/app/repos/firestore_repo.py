# app/repos/firestore_repo.py
import os
from google.cloud import firestore
from google.auth.exceptions import DefaultCredentialsError


class FirestoreRepo:
    def __init__(self):
        self._db = None

        project = os.getenv("FIRESTORE_PROJECT")
        if not project:
            return

        try:
            self._db = firestore.Client(project=project)
        except DefaultCredentialsError:
            # Firestore disabled gracefully (Render-safe)
            self._db = None

    def enabled(self) -> bool:
        return self._db is not None

    def save(self, doc_id: str, data: dict):
        if not self._db:
            return
        self._db.collection("conversations").document(doc_id).set(data)

    def get(self, doc_id: str):
        if not self._db:
            return None

        doc = self._db.collection("conversations").document(doc_id).get()
        return doc.to_dict() if doc.exists else None

    def fail(self, doc_id: str, error: str):
        if not self._db:
            return

        self.save(doc_id, {
            "status": "failed",
            "error": error
        })
