from pydantic import BaseModel
from typing import List, Optional
import uuid

class AIQueryRequest(BaseModel):
    user_id: str
    query: str

class AIQueryResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    data_summary: Optional[dict] = None

class Contact(BaseModel):
    id: int
    name: str
    company: Optional[str] = None
    phone_number: Optional[str] = None
    contact_email: Optional[str] = None

class Note(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    contact_ids: List[int]
    related_contacts: List[str]