from typing import List, Optional

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class ChunkResponse(BaseModel):
    content: str
    source: Optional[str] = None
    page: Optional[int] = None
    score: Optional[float] = None
    type: Optional[str] = "text"
    image_path: Optional[str] = None
    ocr_text: Optional[str] = None
    extraction_method: Optional[str] = None

class AskResponse(BaseModel):
    question: str
    no_rag_answer: str
    rag_answer: str
    retrieved_chunks: List[ChunkResponse]