from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserCreate(BaseModel):
    user_name: str
    email: EmailStr
    password: str
    confirm_password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    user_name: str
    email: EmailStr
    class Config:
        from_attributes = True

class MessageOut(BaseModel):
    id: int
    sender: str
    content: str
    created_at: datetime
    dashboard_updates: Optional[List[dict]] = None
    class Config:
        from_attributes = True

class ChatOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: List[MessageOut] = []
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
