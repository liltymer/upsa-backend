from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional
from datetime import datetime


Priority = Literal["normal", "important", "urgent"]


class AnnouncementCreate(BaseModel):
    title: str
    message: str
    priority: Priority = "normal"
    is_active: Optional[bool] = True


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    priority: Optional[Priority] = None
    is_active: Optional[bool] = None


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    message: str
    priority: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)