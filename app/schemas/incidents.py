from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10)
    severity: str = Field(default="SEV3", pattern=r"^SEV[1-4]$")


class IncidentRead(IncidentCreate):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
