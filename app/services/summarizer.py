from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv
from typing import Optional, List

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=os.environ["OPENAI_API_KEY"]
)

# -------------------------
# Helpers
# -------------------------
def compute_target_words(total_words: int) -> int:
    if total_words <= 2_000:
        return 150
    if total_words <= 6_000:
        return 300
    if total_words <= 20_000:
        return 600
    return 900


def choose_chunk_size(total_words: int) -> int:
    if total_words <= 8_000:
        return 5_000
    if total_words <= 30_000:
        return 8_000
    return 12_000


# -------------------------
# Main summarizer
# -------------------------
def summarize(
    text: str,
    *,
    total_words: int,
    sourceType: str,
    prompt: Optional[str] = None
) -> str:
    """
    Auto-tuned summarizer.

    Behavior:
    - If prompt is provided → summarize ONLY that topic/section
    - If no prompt → summarize full content

    Works for:
    - PDF
    - Website
    """

    if not text or len(text.strip()) < 200:
        return "Not enough content to generate a summary."

    target_words = compute_target_words(total_words)
    chunk_size = choose_chunk_size(total_words)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks = splitter.split_text(text)

    # -------------------------
    # MAP step (prompt-aware)
    # -------------------------
    if prompt:
        map_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a precise document analyzer. "
                "Extract ONLY information related to the given topic. "
                "Ignore all unrelated content completely."
            ),
            (
                "user",
                "TOPIC:\n{prompt}\n\n"
                "TEXT:\n{chunk}\n\n"
                "Return ONLY relevant bullet points."
            )
        ])
    else:
        map_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a precise document summarizer. "
                "Return ONLY 5–7 concise bullet points capturing key facts."
            ),
            ("user", "TEXT:\n{chunk}")
        ])

    bullets = []
    for c in chunks:
        bullets.append(
            llm.invoke(
                map_prompt.format_messages(
                    chunk=c,
                    prompt=prompt
                )
            ).content.strip()
        )

    # -------------------------
    # REDUCE step
    # -------------------------
    reduce_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Combine partial summaries into a single coherent summary."
        ),
        (
            "user",
            "Create a clear summary of about {target_words} words.\n\n"
            "BULLETS:\n{bullets}"
        )
    ])

    final = llm.invoke(
        reduce_prompt.format_messages(
            target_words=str(target_words),
            bullets="\n\n".join(bullets)
        )
    ).content.strip()

    return final


# -------------------------
# Generate top questions
# -------------------------
def generate_questions(text: str) -> List[str]:
    """
    Generate top 3 useful questions from the document.
    Stored in Firestore for UI suggestions.
    """

    if not text or len(text.strip()) < 200:
        return []

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You generate helpful questions a user might ask "
            "after reading a document."
        ),
        (
            "user",
            "From the content below, generate EXACTLY 3 concise questions.\n\n"
            "CONTENT:\n{text}\n\n"
            "Return them as a numbered list."
        )
    ])

    response = llm.invoke(
        prompt.format_messages(text=text[:12_000])  # memory-safe cap
    ).content.strip()

    questions = []
    for line in response.splitlines():
        line = line.strip()
        if line and line[0].isdigit():
            questions.append(line.split(".", 1)[-1].strip())

    return questions[:3]
