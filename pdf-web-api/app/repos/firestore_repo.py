from google.cloud import firestore
import os

class FirestoreRepo:
    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            project = os.getenv("FIRESTORE_PROJECT")
            if not project:
                raise RuntimeError("FIRESTORE_PROJECT is not set")
            self._db = firestore.Client(project=project)
        return self._db

    def save(self, doc_id: str, data: dict):
        self.db.collection("conversations").document(doc_id).set(data)

    def get(self, doc_id: str):
        doc = self.db.collection("conversations").document(doc_id).get()
        return doc.to_dict() if doc.exists else None

    def fail(self, doc_id: str, error: str):
        self.save(doc_id, {
            "status": "failed",
            "error": error
        })
