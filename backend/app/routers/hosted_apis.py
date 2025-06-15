import time # Import time module
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Body, Header, Path as FastApiPath
from fastapi.responses import JSONResponse
from openai import OpenAI, APIStatusError # Import OpenAI and specific error for status code

from .. import auth, crud, models # Main crud, models
from ..routers.prompts import _substitute_variables # Import substitution helper

router = APIRouter(
    prefix="/hosted", # This prefix will be set in main.py
    tags=["Hosted APIs"],
)

@router.post("/execute/u/{username}/{api_path:path}")
async def execute_hosted_api(
    username: str = FastApiPath(..., description="Username of the API owner"),
    api_path: str = FastApiPath(..., description="Path of the API endpoint as defined by the user"),
    request_body: Optional[Dict[str, Any]] = Body(None),
    promptpilot_api_key: str = Header(..., alias="X-PromptPilot-API-Key", description="Your Prompt Pilot Deployed API Key"),
    openai_api_key: str = Header(..., alias="X-OpenAI-API-Key", description="OpenAI API Key for the model execution") # Still needed for actual OpenAI call
):
    # --- PromptPilot API Key Authentication ---
    if not promptpilot_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-PromptPilot-API-Key header is required."
        )

    normalized_api_path = crud._normalize_path(api_path)

    # Find the target API Endpoint first to get its ID
    target_endpoint: Optional[models.APIEndpointInDB] = None
    for ep in crud.fake_api_endpoints_db:
        if ep.owner_username == username and \
           ep.path == normalized_api_path and \
           ep.is_active:
            target_endpoint = ep
            break

    if not target_endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API endpoint not found or not active")

    # Now, validate the provided PromptPilot API Key
    key_hash_to_check = auth.hash_api_key(promptpilot_api_key)
    active_key_obj = crud.get_active_deployed_api_key_for_user_and_endpoint(
        key_hash=key_hash_to_check,
        requesting_owner_username=username, # The user whose endpoint is being called
        target_api_endpoint_id=target_endpoint.id
    )

    if not active_key_obj:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or unauthorized X-PromptPilot-API-Key")

    # Record key usage (fire and forget for now)
    crud.record_key_usage(active_key_obj.id)

    # --- OpenAI API Key Handling (remains for actual execution) ---
    if not openai_api_key: # This is now for the OpenAI call itself
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-OpenAI-API-Key header is required for model execution."
        )
    # Security warning for X-OpenAI-API-Key still applies
    print(f"WARNING: Using X-OpenAI-API-Key from header for user {username} - development only for OpenAI call.")


    # Retrieve prompt using details from the validated target_endpoint
    prompt_db = crud.get_prompt_by_id(target_endpoint.mapped_prompt_id)
    if not prompt_db:
        # This might happen if a prompt was deleted after endpoint creation
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapped prompt not found")

    # Determine prompt text (specific version or latest)
    prompt_text_to_execute = ""
    if found_endpoint.mapped_prompt_version is not None:
        specific_version = crud.get_prompt_version(prompt_db, found_endpoint.mapped_prompt_version)
        if not specific_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mapped version {found_endpoint.mapped_prompt_version} not found for prompt {prompt_db.id}"
            )
        prompt_text_to_execute = specific_version.prompt_text
    else:
        latest_version = crud.get_latest_prompt_version(prompt_db)
        if not latest_version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No versions found for the mapped prompt.")
        prompt_text_to_execute = latest_version.prompt_text

    # Perform variable substitution
    variables_for_substitution = request_body if request_body is not None else {}
    try:
        substituted_prompt_text = _substitute_variables(prompt_text_to_execute, variables_for_substitution)
    except ValueError as e: # Catches missing variables from _substitute_variables
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Variable substitution error: {str(e)}"
        )

    # Actual OpenAI API Call
    ai_model_to_use = target_endpoint.ai_model_name or "gpt-3.5-turbo" # Fallback if None in DB

    start_time = time.time()
    downstream_status = None
    downstream_error = None
    ai_response_text = None

    try:
        client = OpenAI(api_key=openai_api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": substituted_prompt_text,
                }
            ],
            model=ai_model_to_use,
        )
        ai_response_text = chat_completion.choices[0].message.content
        downstream_status = 200 # Assuming success if no exception
    except APIStatusError as e: # Catch OpenAI specific errors for status code
        downstream_status = e.status_code
        downstream_error = str(e.message) # Or e.response.text
        print(f"OpenAI API call failed for endpoint {target_endpoint.id}, user {username}: {downstream_error}")
        # Do not re-raise yet, log first, then decide response
    except Exception as e:
        downstream_status = 500 # Generic internal server error for other exceptions
        downstream_error = str(e)
        print(f"Generic error during OpenAI call for endpoint {target_endpoint.id}, user {username}: {downstream_error}")
        # Do not re-raise yet, log first

    processing_duration_ms = (time.time() - start_time) * 1000

    # Create Log Entry
    log_entry = models.APICallLogCreate(
        deployed_api_key_id=active_key_obj.id,
        api_endpoint_id=target_endpoint.id,
        owner_username=username, # This is target_endpoint.owner_username
        downstream_ai_provider="OpenAI",
        downstream_model_name=ai_model_to_use,
        downstream_status_code=downstream_status,
        downstream_error_message=downstream_error,
        processing_duration_ms=processing_duration_ms
    )
    crud.create_api_call_log(log_entry)

    if downstream_error:
        # Now raise the HTTP Exception if there was an error during the AI call
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI provider call failed. Details logged.")

    return JSONResponse(content={"openai_response": ai_response_text})
