from pydantic import BaseModel
from typing import Optional, List
import datetime

class AttachmentOut(BaseModel):
    id: int
    filename: str
    filepath: str
    filetype: Optional[str]
    uploaded_at: datetime.datetime
    class Config:
        orm_mode = True

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: str = 'knowledge'
    priority: Optional[str] = 'normal'
    tags: Optional[str] = None
    status: Optional[str] = 'pending'
    completed_at: Optional[datetime.datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    type: Optional[str]
    status: Optional[str]
    priority: Optional[str]
    tags: Optional[str]
    completed_at: Optional[datetime.datetime]

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    type: str
    status: str
    priority: str
    tags: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    completed_at: Optional[datetime.datetime]
    attachments: List[AttachmentOut] = []
    class Config:
        orm_mode = True 