"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user response."""
    id: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class LeanCustomerCreate(BaseModel):
    """Schema for creating Lean customer."""
    user_id: str


class LeanCustomerResponse(BaseModel):
    """Schema for Lean customer response."""
    id: str
    user_id: str
    customer_id: str
    app_user_id: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


class EntityLinkRequest(BaseModel):
    """Schema for initiating entity link."""
    customer_id: str
    entity_id: Optional[str] = None
    bank_identifier: Optional[str] = None
    permissions: List[str] = ["identity", "accounts", "balance", "transactions"]


class EntityLinkResponse(BaseModel):
    """Schema for entity link response."""
    id: str
    customer_id: str
    entity_id: str
    bank_identifier: Optional[str]
    status: str
    permissions: List[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class DataSyncRequest(BaseModel):
    """Schema for data sync request."""
    entity_id: str
    sync_types: List[str] = ["identity", "accounts", "balance", "transactions"]
    from_date: Optional[str] = None  # YYYY-MM-DD
    to_date: Optional[str] = None  # YYYY-MM-DD


class DataSyncResponse(BaseModel):
    """Schema for data sync response."""
    entity_id: str
    sync_results: dict
    files_created: List[str]
    
    model_config = {"from_attributes": True}


class LeanAccountResponse(BaseModel):
    """Schema for Lean account response."""
    id: str
    entity_id: str
    account_id: str
    account_number: Optional[str]
    account_type: Optional[str]
    currency: Optional[str]
    balance: Optional[str]
    available_balance: Optional[str]
    
    model_config = {"from_attributes": True}
