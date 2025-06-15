from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Body, Header, Path as FastApiPath
from fastapi.responses import JSONResponse
from openai import OpenAI # Import OpenAI

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
    request_body: Optional[Dict[str, Any]] = Body(None), # Use Body for request_body
    openai_api_key: str = Header(..., alias="X-OpenAI-API-Key", description="OpenAI API Key")
):
    # Basic API Key validation (presence)
    if not openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-OpenAI-API-Key header is required."
        )

    # !!! IMPORTANT SECURITY NOTE !!!
    # In a production environment, API keys should NOT be passed in headers like this.
    # They should be managed securely, e.g., fetched from a secure vault by the backend,
    # or user-specific keys stored encrypted and retrieved.
    # This method is for PoC demonstration ONLY.
    # Log a warning or have a configurable "strict_key_mode" for development.
    print(f"WARNING: Using API key from header for user {username} - development only.")

    normalized_api_path = crud._normalize_path(api_path) # Normalize incoming path for lookup

    found_endpoint: Optional[models.APIEndpointInDB] = None
    for endpoint in crud.fake_api_endpoints_db:
        if endpoint.owner_username == username and \
           endpoint.path == normalized_api_path and \
           endpoint.is_active:
            found_endpoint = endpoint
            break

    if not found_endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API endpoint not found or not active")

    # Retrieve prompt
    prompt_db = crud.get_prompt_by_id(found_endpoint.mapped_prompt_id)
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
    ai_model_to_use = found_endpoint.ai_model_name or "gpt-3.5-turbo" # Fallback if None in DB

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
    except Exception as e:
        # Log the full error for debugging on the server
        print(f"OpenAI API call failed for endpoint {normalized_api_path}, user {username}: {str(e)}")
        # Return a generic error to the client
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OpenAI API call failed.")

    return JSONResponse(content={"openai_response": ai_response_text})
