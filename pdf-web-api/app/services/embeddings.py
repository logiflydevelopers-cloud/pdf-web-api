from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.repos.pinecone_repo import PineconeRepo
from typing import List, Optional

emb = OpenAIEmbeddings(model="text-embedding-3-small")


def build_embeddings(
    *,
    userId: str,
    convId: str,
    texts: List[str],
    sourceType: str,
    pages: Optional[List[int]] = None,
    url: Optional[str] = None,
):
    """
    Build and upsert embeddings for BOTH:
    - PDF
    - Website

    Pinecone:
    - index: same
    - namespace: userId
    - metadata includes actual text
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1600,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks = splitter.split_text("\n".join(texts))
    vectors = []

    embeddings = emb.embed_documents(chunks)

    for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
        metadata = {
            "userId": userId,
            "convId": convId,
            "sourceType": sourceType,  # "pdf" | "web"
            "chunkId": f"c{i}",
            "text": chunk,
        }

        # PDF-specific metadata
        if sourceType == "pdf" and pages:
            metadata["page"] = pages[min(i, len(pages) - 1)]

        # Web-specific metadata
        if sourceType == "web" and url:
            metadata["url"] = url

        vectors.append({
            "id": f"{convId}_c{i}",
            "values": vector,
            "metadata": metadata,
        })

    PineconeRepo().upsert(
        vectors=vectors,
        namespace=userId
    )
