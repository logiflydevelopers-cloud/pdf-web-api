# app/repos/pinecone_repo.py
from pinecone import Pinecone
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index(host=os.environ["PINECONE_HOST"])


class PineconeRepo:

    def upsert(
        self,
        vectors: List[Dict],
        namespace: str
    ):
        """
        Upserts vectors into a user-scoped namespace.
        """
        index.upsert(
            vectors=vectors,
            namespace=namespace
        )

    def query(
        self,
        vector: List[float],
        namespace: str,
        top_k: int = 6,
        metadata_filter: Optional[Dict] = None
    ):
        """
        Queries vectors within a namespace.
        """
        return index.query(
            vector=vector,
            top_k=top_k,
            namespace=namespace,
            filter=metadata_filter,
            include_metadata=True
        )

    def delete_namespace(self, namespace: str):
        """
        Deletes all vectors for a conversation/user.
        """
        index.delete(
            delete_all=True,
            namespace=namespace
        )
