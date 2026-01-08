from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.repos.pinecone_repo import PineconeRepo
from app.repos.firestore_repo import FirestoreRepo
from typing import List, Optional, Dict
import uuid

# -------------------------
# Embedding model
# -------------------------
emb = OpenAIEmbeddings(model="text-embedding-3-small")


def build_embeddings(
    *,
    userId: str,
    convId: str,
    texts: List[str],
    sourceType: str,
    pages: Optional[List[int]] = None,         # PDF only
    url: Optional[str] = None,                  # WEB (single page)
    chunkId: Optional[str] = None,              # Optional prefix
    metadata: Optional[List[Dict]] = None,      # 🔥 NEW (WEB micro-batch)
):
    """
    Build and upsert embeddings for BOTH:
    - PDF
    - Website (micro-batched)

    Storage model:
    - Pinecone: vectors + lightweight metadata ONLY
    - Firestore: chunk text + full metadata (NO vectors)
    """

    if not texts:
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1600,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    )

    pinecone = PineconeRepo()
    firestore = FirestoreRepo()

    namespace = f"{userId}:{convId}"
    vectors = []

    # ==================================================
    # 🔥 WEB MICRO-BATCH MODE
    # ==================================================
    if sourceType == "web" and metadata:
        for idx, text in enumerate(texts):
            page_meta = metadata[idx]

            chunks = splitter.split_text(text)
            if not chunks:
                continue

            embeddings = emb.embed_documents(chunks)

            for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                cid = f"{page_meta['chunkId']}_{i}"

                # -------- Firestore (TEXT ONLY)
                if firestore.enabled():
                    firestore.save_chunk(
                        conversation_id=convId,
                        chunk_id=cid,
                        text=chunk,
                        metadata={
                            "userId": userId,
                            "convId": convId,
                            "chunkId": cid,
                            "sourceType": "web",
                            "url": page_meta["url"],
                        }
                    )

                vectors.append({
                    "id": cid,
                    "values": vector,
                    "metadata": {
                        "chunkId": cid,
                        "sourceType": "web",
                        "url": page_meta["url"],
                    },
                })

    # ==================================================
    # PDF / SINGLE PAGE MODE (UNCHANGED)
    # ==================================================
    else:
        full_text = "\n".join(texts)
        chunks = splitter.split_text(full_text)

        if not chunks:
            return

        embeddings = emb.embed_documents(chunks)

        for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            cid = (
                f"{chunkId}_{i}" if chunkId
                else f"chunk_{uuid.uuid4().hex}"
            )

            if firestore.enabled():
                firestore.save_chunk(
                    conversation_id=convId,
                    chunk_id=cid,
                    text=chunk,
                    metadata={
                        "userId": userId,
                        "convId": convId,
                        "chunkId": cid,
                        "sourceType": sourceType,
                        "page": (
                            pages[i]
                            if sourceType == "pdf" and pages and i < len(pages)
                            else None
                        ),
                        "url": url if sourceType == "web" else None,
                    }
                )

            meta = {
                "chunkId": cid,
                "sourceType": sourceType,
            }

            if sourceType == "pdf" and pages and i < len(pages):
                meta["page"] = pages[i]

            if sourceType == "web" and url:
                meta["url"] = url

            vectors.append({
                "id": cid,
                "values": vector,
                "metadata": meta,
            })

    # -------------------------
    # Upsert once per batch
    # -------------------------
    if vectors:
        pinecone.upsert(vectors=vectors, namespace=namespace)
