# app/repos/firestore_repo.py
import os
from google.cloud import firestore
from google.auth.exceptions import DefaultCredentialsError
from typing import Optional, Dict


class FirestoreRepo:
    def __init__(self):
        self._db = None

        project = os.getenv("FIRESTORE_PROJECT")
        print("FIRESTORE_PROJECT =", project)

        if not project:
            print("Firestore disabled: FIRESTORE_PROJECT not set")
            return

        try:
            self._db = firestore.Client(project=project)
            print("Firestore initialized successfully")
        except DefaultCredentialsError as e:
            print("Firestore credentials error:", str(e))
            print("Firestore disabled due to missing credentials")
            self._db = None
        except Exception as e:
            print("Firestore init failed:", str(e))
            self._db = None

    def enabled(self) -> bool:
        return self._db is not None

    # ---------------------------------------------------
    # Conversation-level
    # ---------------------------------------------------
    def save(self, doc_id: str, data: dict):
        if not self._db:
            return
        self._db.collection("conversations").document(doc_id).set(data)

    def get(self, doc_id: str) -> Optional[Dict]:
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

    # ---------------------------------------------------
    # Chunk-level storage
    # ---------------------------------------------------
    def save_chunk(
        self,
        conversation_id: str,
        chunk_id: str,
        text: str,
        metadata: Optional[Dict] = None
    ):
        """
        Stores chunk text separately (NOT in Pinecone).
        """
        if not self._db:
            return

        payload = {
            "text": text,
            "metadata": metadata or {}
        }

        self._db \
            .collection("conversations") \
            .document(conversation_id) \
            .collection("chunks") \
            .document(chunk_id) \
            .set(payload)

    def get_chunk(self, conversation_id: str, chunk_id: str) -> Optional[str]:
        """
        Retrieves chunk text for RAG.
        """
        if not self._db:
            return None

        doc = (
            self._db
            .collection("conversations")
            .document(conversation_id)
            .collection("chunks")
            .document(chunk_id)
            .get()
        )

        if not doc.exists:
            return None

        return doc.to_dict().get("text")

