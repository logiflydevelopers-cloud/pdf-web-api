# app/repos/qa.py
from pydantic import BaseModel
from typing import List, Optional, Any


class QAHistoryItem(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AskRequest(BaseModel):
    question: str
    history: Optional[List[QAHistoryItem]] = None


class AskResponse(BaseModel):
    convId: str
    question: str
    answer: str
    answerMode: str  # "summary" | "rag"
    sources: List[Any]
