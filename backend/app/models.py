from pydantic import BaseModel
from typing import Optional

class UserInDB(BaseModel):
    username: str
    email: str
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

from datetime import datetime

# Models for Prompts
class PromptVersionBase(BaseModel):
    prompt_text: str

class PromptVersionInDB(PromptVersionBase):
    version_number: int
    created_at: datetime

class PromptBase(BaseModel): # This now primarily holds metadata, not text
    name: str
    description: Optional[str] = None

class PromptCreate(PromptBase): # For creation, text is still passed but will form version 1
    prompt_text: str

class PromptUpdate(BaseModel): # For updates, text is optional for new version
    name: Optional[str] = None
    description: Optional[str] = None
    prompt_text: Optional[str] = None

class PromptInDB(PromptBase):
    id: int
    owner_username: str # Using username for simplicity with in-memory DB
    versions: list[PromptVersionInDB] = []
    latest_version_number: int = 0

# Models for API Endpoints
class APIEndpointBase(BaseModel):
    name: str
    description: Optional[str] = None
    path: str # Path defined by user, e.g. /my-sentiment-analyzer
    mapped_prompt_id: int
    mapped_prompt_version: Optional[int] = None # If None, uses latest version of the prompt
    # Schemas for request/response validation by the dynamic endpoint (not by FastAPI itself directly for these)
    request_schema: Optional[dict] = None
    response_schema: Optional[dict] = None
    is_active: bool = True
    ai_model_name: Optional[str] = "gpt-3.5-turbo" # Default model

class APIEndpointCreate(APIEndpointBase): # Inherits ai_model_name, can be overridden at creation
    pass

class APIEndpointUpdate(BaseModel): # All fields optional for partial updates
    name: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    mapped_prompt_id: Optional[int] = None
    mapped_prompt_version: Optional[int] = None # Explicitly allowing None to unset/use latest
    request_schema: Optional[dict] = None
    response_schema: Optional[dict] = None
    is_active: Optional[bool] = None
    ai_model_name: Optional[str] = None # Allow update to set or unset (to default)

class APIEndpointInDB(APIEndpointBase): # Inherits ai_model_name from APIEndpointBase
    id: int
    owner_username: str

# Models for Deployed API Access Keys (for user-created APIs)
class DeployedAPIAccessKeyBase(BaseModel):
    name: str
    api_endpoint_id: Optional[int] = None # If None, key is valid for all user's endpoints

class DeployedAPIAccessKeyCreate(DeployedAPIAccessKeyBase):
    pass # No extra fields needed for creation request from user

class DeployedAPIAccessKeyInDB(DeployedAPIAccessKeyBase):
    id: int
    key_hash: str # Store the hash of the key, not the key itself
    key_prefix: str # Store a few characters of the key for identification
    owner_username: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    is_active: bool = True

# Models for API Call Logs
class APICallLogBase(BaseModel):
    deployed_api_key_id: int # Refers to DeployedAPIAccessKeyInDB.id
    api_endpoint_id: int # Refers to APIEndpointInDB.id
    owner_username: str # Denormalized for easier querying, but should match key & endpoint owner

    # Information about the downstream AI call
    downstream_ai_provider: Optional[str] = None # e.g., "OpenAI"
    downstream_model_name: Optional[str] = None # e.g., "gpt-3.5-turbo"

    # Response details from downstream
    downstream_status_code: Optional[int] = None # e.g., 200 from OpenAI, or 500 if OpenAI call failed
    downstream_error_message: Optional[str] = None # If there was an error from downstream

    processing_duration_ms: Optional[float] = None # Time taken for the downstream call

class APICallLogCreate(APICallLogBase):
    pass

class APICallLogInDB(APICallLogBase):
    id: int
    timestamp: datetime # Time of the incoming call to Prompt Pilot hosted API
