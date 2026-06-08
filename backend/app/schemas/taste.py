from datetime import datetime

from pydantic import BaseModel


class TasteProfileResponse(BaseModel):
    summary_text: str | None
    insights_json: dict | None
    computed_at: datetime | None

    model_config = {"from_attributes": True}


class AnalyticsResponse(BaseModel):
    genres: list[dict]
    decades: list[dict]
    monthly_activity: list[dict]
    top_directors: list[dict]
    average_rating_by_genre: list[dict]
    avoided_genres: list[dict]
