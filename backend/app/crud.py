from typing import List, Optional
from . import models, schemas

# In-memory storage for users
fake_users_db: List[models.UserInDB] = []

def get_user_by_email(email: str) -> Optional[models.UserInDB]:
    for user in fake_users_db:
        if user.email == email:
            return user
    return None

def get_user_by_username(username: str) -> Optional[models.UserInDB]:
    for user in fake_users_db:
        if user.username == username:
            return user
    return None

def create_user(user: schemas.UserCreate, hashed_password: str) -> models.UserInDB:
    db_user = models.UserInDB(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    fake_users_db.append(db_user)
    return db_user

from datetime import datetime, timezone

# In-memory storage for prompts
fake_prompts_db: List[models.PromptInDB] = []
prompt_id_counter = 1

def create_prompt(prompt_data: schemas.PromptCreate, owner_username: str) -> models.PromptInDB:
    global prompt_id_counter

    first_version = models.PromptVersionInDB(
        prompt_text=prompt_data.prompt_text,
        version_number=1,
        created_at=datetime.now(timezone.utc)
    )

    db_prompt = models.PromptInDB(
        id=prompt_id_counter,
        name=prompt_data.name,
        description=prompt_data.description,
        owner_username=owner_username,
        versions=[first_version],
        latest_version_number=1
    )
    fake_prompts_db.append(db_prompt)
    prompt_id_counter += 1
    return db_prompt

def get_prompt_by_id(prompt_id: int) -> Optional[models.PromptInDB]:
    for prompt in fake_prompts_db:
        if prompt.id == prompt_id:
            return prompt
    return None

def get_prompts_by_owner(owner_username: str) -> List[models.PromptInDB]:
    return [prompt for prompt in fake_prompts_db if prompt.owner_username == owner_username]

def update_prompt(prompt_id: int, prompt_update_data: schemas.PromptUpdate, owner_username: str) -> Optional[models.PromptInDB]:
    db_prompt = get_prompt_by_id(prompt_id)
    if not db_prompt or db_prompt.owner_username != owner_username:
        return None

    updated = False
    if prompt_update_data.name is not None:
        db_prompt.name = prompt_update_data.name
        updated = True
    if prompt_update_data.description is not None:
        db_prompt.description = prompt_update_data.description
        updated = True

    if prompt_update_data.prompt_text is not None:
        db_prompt.latest_version_number += 1
        new_version = models.PromptVersionInDB(
            prompt_text=prompt_update_data.prompt_text,
            version_number=db_prompt.latest_version_number,
            created_at=datetime.now(timezone.utc)
        )
        db_prompt.versions.append(new_version)
        updated = True

    # In a real DB, we might have an updated_at field for the prompt itself
    # For now, just returning the prompt if any part of it was modified.
    return db_prompt if updated else db_prompt # Or return None if !updated and no text change? For now, returns prompt.

def delete_prompt(prompt_id: int, owner_username: str) -> bool:
    db_prompt = get_prompt_by_id(prompt_id)
    if not db_prompt or db_prompt.owner_username != owner_username:
        return False
    fake_prompts_db.remove(db_prompt)
    return True

def get_prompt_version(prompt: models.PromptInDB, version_number: int) -> Optional[models.PromptVersionInDB]:
    """Helper to get a specific version from a prompt."""
    for version in prompt.versions:
        if version.version_number == version_number:
            return version
    return None

def get_latest_prompt_version(prompt: models.PromptInDB) -> Optional[models.PromptVersionInDB]:
    """Helper to get the latest version of a prompt."""
    if not prompt.versions:
        return None
    # Assuming versions are not necessarily sorted, find max version_number
    # Or, rely on latest_version_number if always consistent
    return get_prompt_version(prompt, prompt.latest_version_number)

# In-memory storage for API Endpoints
fake_api_endpoints_db: List[models.APIEndpointInDB] = []
api_endpoint_id_counter = 1

def _normalize_path(path: str) -> str:
    """Normalizes a path to start with '/' and have no trailing '/'."""
    path = path.strip().strip('/')
    return f"/{path}" if path else "/"

def _validate_endpoint_path(path: str, owner_username: str, existing_endpoint_id: Optional[int] = None) -> None:
    """Checks if the path is unique for the owner after normalization."""
    normalized_path = _normalize_path(path)
    for ep in fake_api_endpoints_db:
        if ep.owner_username == owner_username and ep.path == normalized_path: # Compare with normalized path
            if existing_endpoint_id is None or ep.id != existing_endpoint_id: # If creating, or updating a different endpoint
                 raise HTTPException(status_code=400, detail=f"Path '{normalized_path}' already in use by this user.")

def _validate_prompt_for_endpoint(
    mapped_prompt_id: int,
    mapped_prompt_version: Optional[int],
    owner_username: str,
    prompts_crud_module # Pass the prompts CRUD module
) -> models.PromptInDB:
    """Validates prompt existence, ownership, and version."""
    prompt = prompts_crud_module.get_prompt_by_id(mapped_prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt with ID {mapped_prompt_id} not found.")
    if prompt.owner_username != owner_username:
        raise HTTPException(status_code=403, detail="Cannot map endpoint to a prompt you do not own.")

    if mapped_prompt_version is not None:
        version = prompts_crud_module.get_prompt_version(prompt, mapped_prompt_version)
        if not version:
            raise HTTPException(status_code=404, detail=f"Version {mapped_prompt_version} for prompt {mapped_prompt_id} not found.")
    # If mapped_prompt_version is None, we assume it uses the latest, which is implicitly valid if prompt exists.
    return prompt


def create_api_endpoint(
    endpoint_data: schemas.APIEndpointCreate, # Use schema for input
    owner_username: str,
    prompts_crud_module # Pass the prompts CRUD module
) -> models.APIEndpointInDB:
    global api_endpoint_id_counter

    normalized_path = _normalize_path(endpoint_data.path)
    _validate_endpoint_path(normalized_path, owner_username) # Validate with normalized
    _validate_prompt_for_endpoint(
        endpoint_data.mapped_prompt_id,
        endpoint_data.mapped_prompt_version,
        owner_username,
        prompts_crud_module
    )

    db_endpoint = models.APIEndpointInDB(
        id=api_endpoint_id_counter,
        name=endpoint_data.name,
        description=endpoint_data.description,
        path=normalized_path, # Store normalized path
        mapped_prompt_id=endpoint_data.mapped_prompt_id,
        mapped_prompt_version=endpoint_data.mapped_prompt_version,
        request_schema=endpoint_data.request_schema,
        response_schema=endpoint_data.response_schema,
        owner_username=owner_username,
        is_active=True, # Default from model
        ai_model_name=endpoint_data.ai_model_name # Add new field
    )
    fake_api_endpoints_db.append(db_endpoint)
    api_endpoint_id_counter += 1
    return db_endpoint

def get_api_endpoint_by_id(endpoint_id: int) -> Optional[models.APIEndpointInDB]:
    for ep in fake_api_endpoints_db:
        if ep.id == endpoint_id:
            return ep
    return None

def get_api_endpoints_by_owner(owner_username: str) -> List[models.APIEndpointInDB]:
    return [ep for ep in fake_api_endpoints_db if ep.owner_username == owner_username]

def update_api_endpoint(
    endpoint_id: int,
    endpoint_update_data: schemas.APIEndpointUpdate, # Use schema for input
    owner_username: str,
    prompts_crud_module
) -> Optional[models.APIEndpointInDB]:
    db_endpoint = get_api_endpoint_by_id(endpoint_id)
    if not db_endpoint or db_endpoint.owner_username != owner_username:
        return None # Or raise HTTPException(403/404) from router

    update_data = endpoint_update_data.model_dump(exclude_unset=True)

    if "path" in update_data:
        normalized_new_path = _normalize_path(update_data["path"])
        if normalized_new_path != db_endpoint.path:
            _validate_endpoint_path(normalized_new_path, owner_username, existing_endpoint_id=endpoint_id)
        update_data["path"] = normalized_new_path # Ensure path is updated in its normalized form

    # Validate prompt if prompt_id or version is changing
    # Need to fetch current/new prompt_id and version for validation
    new_prompt_id = update_data.get("mapped_prompt_id", db_endpoint.mapped_prompt_id)
    new_prompt_version = update_data.get("mapped_prompt_version", db_endpoint.mapped_prompt_version)

    # Perform validation if prompt ID changed, or if version changed for the same prompt ID.
    # Or if only version is specified, assuming it's for the current prompt ID.
    if "mapped_prompt_id" in update_data or ("mapped_prompt_version" in update_data and update_data["mapped_prompt_version"] is not None): # only validate if version is explicitly set
         _validate_prompt_for_endpoint(
            new_prompt_id,
            new_prompt_version,
            owner_username,
            prompts_crud_module
        )

    # If mapped_prompt_version is explicitly set to None in the update, it means "use latest".
    # No specific version validation is needed in that case, beyond prompt existence/ownership.
    # The _validate_prompt_for_endpoint handles mapped_prompt_version being None correctly.

    for key, value in update_data.items():
        setattr(db_endpoint, key, value)

    # If ai_model_name is being set to None in an update, it should revert to the default.
    # The model has a default, so assigning None will make it None, not revert.
    # This logic should be handled at the Pydantic model level or endpoint logic if "unsetting" means "revert to default".
    # For now, if `ai_model_name` is in `update_data` and is `None`, it will be set to `None` in the DB.
    # If it's not in `update_data`, it remains unchanged.
    # If a create request omits it, the model's default "gpt-3.5-turbo" is used.

    return db_endpoint

def delete_api_endpoint(endpoint_id: int, owner_username: str) -> bool:
    db_endpoint = get_api_endpoint_by_id(endpoint_id)
    if not db_endpoint or db_endpoint.owner_username != owner_username:
        return False
    fake_api_endpoints_db.remove(db_endpoint)
    return True

# --- Deployed API Access Key CRUD ---
fake_deployed_api_keys_db: List[models.DeployedAPIAccessKeyInDB] = []
deployed_api_key_id_counter = 1

def create_deployed_api_key(
    key_data: schemas.DeployedAPIAccessKeyCreate, # Use schema for input
    owner_username: str,
    full_key: str, # Not stored directly, but passed for context if needed elsewhere
    key_hash: str,
    key_prefix: str,
    api_endpoints_crud_module # To validate api_endpoint_id
) -> models.DeployedAPIAccessKeyInDB:
    global deployed_api_key_id_counter

    if key_data.api_endpoint_id is not None:
        endpoint = api_endpoints_crud_module.get_api_endpoint_by_id(key_data.api_endpoint_id)
        if not endpoint:
            raise HTTPException(status_code=404, detail=f"API Endpoint with ID {key_data.api_endpoint_id} not found.")
        if endpoint.owner_username != owner_username:
            raise HTTPException(status_code=403, detail="Cannot create key for an API Endpoint you do not own.")

    db_key = models.DeployedAPIAccessKeyInDB(
        id=deployed_api_key_id_counter,
        name=key_data.name,
        api_endpoint_id=key_data.api_endpoint_id,
        owner_username=owner_username,
        key_hash=key_hash,
        key_prefix=key_prefix,
        created_at=datetime.now(timezone.utc),
        is_active=True
    )
    fake_deployed_api_keys_db.append(db_key)
    deployed_api_key_id_counter += 1
    return db_key

def get_deployed_api_key_by_hash(key_hash: str) -> Optional[models.DeployedAPIAccessKeyInDB]:
    for key_in_db in fake_deployed_api_keys_db:
        if key_in_db.key_hash == key_hash:
            return key_in_db
    return None

def get_active_deployed_api_key_for_user_and_endpoint(
    key_hash: str,
    requesting_owner_username: str, # The username from the /u/{username}/ part of the URL
    target_api_endpoint_id: int # The ID of the endpoint being called
) -> Optional[models.DeployedAPIAccessKeyInDB]:
    key_in_db = get_deployed_api_key_by_hash(key_hash)
    if not key_in_db:
        return None # Key doesn't exist

    if not key_in_db.is_active:
        return None # Key is not active

    if key_in_db.owner_username != requesting_owner_username:
        # This check ensures the API key belongs to the user whose endpoint is being called.
        # This is crucial if key_hash alone was globally unique but we want to scope its use.
        return None

    # Check if the key is authorized for the specific endpoint
    if key_in_db.api_endpoint_id is not None and key_in_db.api_endpoint_id != target_api_endpoint_id:
        return None # Key is for a specific different endpoint

    return key_in_db


def get_deployed_api_keys_by_owner(owner_username: str) -> List[models.DeployedAPIAccessKeyInDB]:
    return [key for key in fake_deployed_api_keys_db if key.owner_username == owner_username]

def deactivate_deployed_api_key(key_id: int, owner_username: str) -> bool:
    for key_in_db in fake_deployed_api_keys_db:
        if key_in_db.id == key_id and key_in_db.owner_username == owner_username:
            key_in_db.is_active = False
            # key_in_db.updated_at = datetime.now(timezone.utc) # If we add updated_at
            return True
    return False

def record_key_usage(key_id: int) -> None:
    for key_in_db in fake_deployed_api_keys_db:
        if key_in_db.id == key_id:
            key_in_db.last_used_at = datetime.now(timezone.utc)
            break

# --- API Call Log CRUD ---
fake_api_call_logs_db: List[models.APICallLogInDB] = []
api_call_log_id_counter = 1

def create_api_call_log(log_data: models.APICallLogCreate) -> models.APICallLogInDB: # Takes model type
    global api_call_log_id_counter
    db_log = models.APICallLogInDB(
        id=api_call_log_id_counter,
        timestamp=datetime.now(timezone.utc), # Log timestamp is now
        **log_data.model_dump() # Spread fields from APICallLogCreate
    )
    fake_api_call_logs_db.append(db_log)
    api_call_log_id_counter += 1
    return db_log

def get_api_call_logs_by_owner(
    owner_username: str, limit: int = 100, offset: int = 0
) -> List[models.APICallLogInDB]:
    # Simple in-memory pagination and filtering
    user_logs = [log for log in fake_api_call_logs_db if log.owner_username == owner_username]
    # Sort by timestamp descending (newest first)
    user_logs.sort(key=lambda x: x.timestamp, reverse=True)
    return user_logs[offset : offset + limit]

def get_api_call_logs_by_endpoint(
    api_endpoint_id: int, owner_username: str, limit: int = 100, offset: int = 0
) -> List[models.APICallLogInDB]:
    # Ensure user owns the endpoint they are querying logs for (implicitly done if logs are correctly attributed)
    # For direct queries, this check is good practice if logs weren't strictly owner-bound.
    # Here, owner_username on the log itself is the primary filter.
    endpoint_logs = [
        log for log in fake_api_call_logs_db
        if log.api_endpoint_id == api_endpoint_id and log.owner_username == owner_username
    ]
    # Sort by timestamp descending
    endpoint_logs.sort(key=lambda x: x.timestamp, reverse=True)
    return endpoint_logs[offset : offset + limit]
