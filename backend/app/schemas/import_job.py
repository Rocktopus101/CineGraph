from datetime import datetime

from pydantic import BaseModel


class ImportJobResponse(BaseModel):
    id: int
    status: str
    file_hash: str | None
    started_at: datetime
    completed_at: datetime | None
    stats_json: dict | None
    error: str | None

    model_config = {"from_attributes": True}
