from datetime import datetime

from pydantic import BaseModel


class Citation(BaseModel):
    movie_id: int
    title: str
    rating: float | None = None
    watched_date: str | None = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    citations: list[Citation]
    query_id: int | None = None


class GenerateRequest(BaseModel):
    query: str
    filters: dict | None = None


class ChatHistoryItem(BaseModel):
    id: int
    query_text: str
    response_preview: str | None
    created_at: datetime


class ChatHistoryDetail(BaseModel):
    id: int
    query_text: str
    response_text: str
    citations: list[Citation]
    created_at: datetime
