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
