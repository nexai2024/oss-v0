from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr # Changed from username to email for login, as per TokenData
    password: str

class User(UserBase):
    id: int # Assuming we'll have an ID when retrieving from a real DB
    username: str
    is_active: bool = True # Example field

    class Config:
        orm_mode = True # Changed from from_attributes to orm_mode for Pydantic v2 compatibility

# Output schema for user, without password
class UserPublic(UserBase):
    username: str
    # Any other public fields can be added here
    pass

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: EmailStr | None = None


from datetime import datetime
from typing import List, Any # Ensure List and Any are imported

# Schemas for Prompts
class PromptVersionBase(BaseModel): # For consistency, can be used by PromptVersionPublic
    prompt_text: str

class PromptVersionPublic(PromptVersionBase):
    version_number: int
    created_at: datetime

    class Config:
        orm_mode = True

class PromptBasePublic(BaseModel): # Base for PromptPublic, containing common fields
    id: int
    owner_username: str
    name: str
    description: Optional[str] = None
    latest_version_number: int

    class Config:
        orm_mode = True

class PromptPublic(PromptBasePublic):
    versions: List[PromptVersionPublic] = []
    current_prompt_text: str # Text of the latest or specified version

# Schema for creating a new prompt, initial text becomes version 1
class PromptCreate(BaseModel): # No longer inherits PromptBase from models directly
    name: str
    description: Optional[str] = None
    prompt_text: str # This text will be for the first version

# Schema for updating a prompt. Text is optional; if provided, creates new version.
class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt_text: Optional[str] = None # If present, creates a new version

# Schemas for Prompt Execution
class PromptExecuteRequest(BaseModel):
    variables: Dict[str, Any] # Explicitly import Dict and Any
    version_number: Optional[int] = None # For specifying which version to execute

class PromptExecuteResponse(BaseModel):
    executed_prompt_text: str

# Schemas for API Endpoints
class APIEndpointBaseSchema(BaseModel): # Renamed to avoid conflict with model's APIEndpointBase
    name: str
    description: Optional[str] = None
    path: str
    mapped_prompt_id: int
    mapped_prompt_version: Optional[int] = None
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    ai_model_name: Optional[str] = "gpt-3.5-turbo" # Add with default

class APIEndpointCreate(APIEndpointBaseSchema): # Inherits from schema version, including ai_model_name
    pass

class APIEndpointUpdate(BaseModel): # Matches model's APIEndpointUpdate
    name: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    mapped_prompt_id: Optional[int] = None
    mapped_prompt_version: Optional[int] = None
    is_active: Optional[bool] = None
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    ai_model_name: Optional[str] = None # Allow update

class APIEndpointPublic(APIEndpointBaseSchema): # Will inherit ai_model_name from APIEndpointBaseSchema
    id: int
    owner_username: str
    is_active: bool = True

    class Config:
        orm_mode = True
