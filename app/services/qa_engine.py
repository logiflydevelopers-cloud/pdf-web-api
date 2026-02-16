# app/repos/qa_engine.py

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.repos.pinecone_repo import PineconeRepo
from app.repos.firestore_repo import FirestoreRepo
from dotenv import load_dotenv
from typing import Tuple, List, Dict

load_dotenv()


# ----------------------------------------
# TOKEN ESTIMATION (1 token ≈ 4 chars)
# ----------------------------------------
def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return int(len(text) / 4)


# ----------------------------------------
# LLM + EMBEDDINGS
# ----------------------------------------
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2
)

emb = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

NO_ANSWER = "Not enough information in the summary to answer that."
NO_DOC_ANSWER = "Not enough information in the document to answer that."


# ----------------------------------------
# MAIN QA FUNCTION
# ----------------------------------------
def answer_question(
    *,
    summary: str,
    question: str,
    userId: str,
    convId: str
) -> Tuple[str, str, List[Dict]]:

    firestore = FirestoreRepo()

    # ----------------------------------
    # STEP 1: SUMMARY-ONLY ANSWER
    # ----------------------------------
    summary_prompt = f"""
You must answer ONLY using the summary below.

If the summary does not contain the answer,
respond EXACTLY with this sentence and nothing else:
"{NO_ANSWER}"

SUMMARY:
{summary}

QUESTION:
{question}
"""

    summary_response = llm.invoke(summary_prompt)
    summary_ans = summary_response.content.strip()

    if summary_ans != NO_ANSWER:
        input_tokens = estimate_tokens(summary_prompt)
        output_tokens = estimate_tokens(summary_ans)

        # Update conversation
        firestore.update(convId, {
            "lastQuestion": question,
            "lastAnswer": summary_ans
        })

        # Atomic token increment
        firestore.increment_tokens(
            convId,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        return summary_ans, "summary", []

    # ----------------------------------
    # STEP 2: RAG FALLBACK
    # ----------------------------------
    q_vec = emb.embed_query(question)
    namespace = f"{userId}:{convId}"

    pinecone = PineconeRepo()

    res = pinecone.query(
        vector=q_vec,
        namespace=namespace,
        top_k=6
    )

    # ----------------------------------
    # NO DOCUMENT MATCH
    # ----------------------------------
    if not res.matches:
        output_text = NO_DOC_ANSWER

        input_tokens = estimate_tokens(question)
        output_tokens = estimate_tokens(output_text)

        firestore.update(convId, {
            "lastQuestion": question,
            "lastAnswer": output_text
        })

        firestore.increment_tokens(
            convId,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        return NO_DOC_ANSWER, "rag", []

    context_blocks = []
    sources = []
    cited_refs = set()

    for m in res.matches:
        md = m.metadata or {}
        chunk_id = md.get("chunkId")
        source_type = md.get("sourceType")

        if not chunk_id:
            continue

        text = firestore.get_chunk(
            conversation_id=convId,
            chunk_id=chunk_id
        )

        if not text:
            continue

        if source_type == "pdf":
            page = md.get("page")
            ref = f"p. {page}" if page else "p. ?"
            context_blocks.append(f"({ref})\n{text}")
            cited_refs.add(ref)

            sources.append({
                "type": "pdf",
                "page": page,
                "chunkId": chunk_id,
                "score": round(m.score, 4)
            })

        elif source_type == "web":
            url = md.get("url")
            ref = url or "web"
            context_blocks.append(f"(source: {ref})\n{text}")
            cited_refs.add(ref)

            sources.append({
                "type": "web",
                "url": url,
                "chunkId": chunk_id,
                "score": round(m.score, 4)
            })

    if not context_blocks:
        return NO_DOC_ANSWER, "rag", []

    context = "\n\n---\n\n".join(context_blocks)

    rag_prompt = f"""
Answer using ONLY the provided context.
Use the summary only for high-level framing.

If the answer is not supported, say exactly:
"{NO_DOC_ANSWER}"

Include citations like (p. X) or (source: URL).

SUMMARY:
{summary}

CONTEXT:
{context}

QUESTION:
{question}
"""

    rag_response = llm.invoke(rag_prompt)
    rag_answer = rag_response.content.strip()

    if cited_refs:
        rag_answer += "\n\nSources: " + ", ".join(sorted(cited_refs))

    # ----------------------------------
    # TOKEN CALCULATION (RAG)
    # ----------------------------------
    input_tokens = estimate_tokens(rag_prompt)
    output_tokens = estimate_tokens(rag_answer)

    firestore.update(convId, {
        "lastQuestion": question,
        "lastAnswer": rag_answer
    })

    firestore.increment_tokens(
        convId,
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )

    return rag_answer, "rag", sources
