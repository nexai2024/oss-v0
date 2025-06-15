import re
import string
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status

from .. import auth, crud, models, schemas

# Helper function to convert PromptInDB to PromptPublic
def _map_prompt_to_public(db_prompt: models.PromptInDB, version_to_display: Optional[models.PromptVersionInDB] = None) -> schemas.PromptPublic:
    if not db_prompt.versions: # Should not happen if prompt exists
        current_text = "No versions available."
    else:
        version_for_text = version_to_display if version_to_display else crud.get_latest_prompt_version(db_prompt)
        current_text = version_for_text.prompt_text if version_for_text else "Error: Version not found." # Should be handled before calling

    return schemas.PromptPublic(
        id=db_prompt.id,
        owner_username=db_prompt.owner_username,
        name=db_prompt.name,
        description=db_prompt.description,
        latest_version_number=db_prompt.latest_version_number,
        versions=[
            schemas.PromptVersionPublic(
                prompt_text=v.prompt_text,
                version_number=v.version_number,
                created_at=v.created_at
            ) for v in db_prompt.versions
        ],
        current_prompt_text=current_text
    )

router = APIRouter(
    prefix="/prompts",
    tags=["Prompts"],
    dependencies=[Depends(auth.get_current_active_user)], # All routes here require authentication
    responses={404: {"description": "Prompt not found"}},
)

@router.post("/", response_model=schemas.PromptPublic, status_code=status.HTTP_201_CREATED)
async def create_new_prompt(
    prompt: schemas.PromptCreate,
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    # Check for duplicate prompt name for the same user
    # This check might need adjustment if PromptInDB structure changed significantly regarding name uniqueness logic
    # For now, assuming crud.get_prompts_by_owner still works and returns objects with a .name attribute
    existing_prompts_db = crud.get_prompts_by_owner(owner_username=current_user.username)
    if any(p.name == prompt.name for p in existing_prompts_db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A prompt with the name '{prompt.name}' already exists."
        )

    created_prompt_db = crud.create_prompt(prompt_data=prompt, owner_username=current_user.username)
    # The first version's text is used for current_prompt_text by default in _map_prompt_to_public
    return _map_prompt_to_public(created_prompt_db)

@router.get("/", response_model=List[schemas.PromptPublic])
async def read_user_prompts(
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    prompts_in_db = crud.get_prompts_by_owner(owner_username=current_user.username)
    return [_map_prompt_to_public(p) for p in prompts_in_db]

@router.get("/{prompt_id}", response_model=schemas.PromptPublic)
async def read_single_prompt(
    prompt_id: int,
    version: Optional[int] = None, # New optional query parameter
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    db_prompt = crud.get_prompt_by_id(prompt_id=prompt_id)
    if db_prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    if db_prompt.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    version_to_display_obj = None
    if version is not None:
        version_to_display_obj = crud.get_prompt_version(db_prompt, version)
        if not version_to_display_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found for prompt {prompt_id}"
            )
    else: # Default to latest if no specific version requested
        version_to_display_obj = crud.get_latest_prompt_version(db_prompt)
        if not version_to_display_obj and db_prompt.versions: # Prompt exists but somehow no latest version
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not determine latest version.")
        elif not db_prompt.versions: # Prompt exists but has no versions (should not happen with current CRUD)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt has no versions.")


    return _map_prompt_to_public(db_prompt, version_to_display_obj)

@router.put("/{prompt_id}", response_model=schemas.PromptPublic)
async def update_existing_prompt(
    prompt_id: int,
    prompt_update_data: schemas.PromptUpdate, # Renamed for clarity
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    # Ensure the prompt exists and is owned by the user before attempting update
    # This check is technically done by crud.update_prompt as well, but good for early exit.
    db_prompt_check = crud.get_prompt_by_id(prompt_id=prompt_id)
    if not db_prompt_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    if db_prompt_check.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to update this prompt")

    updated_prompt_db = crud.update_prompt(
        prompt_id=prompt_id,
        prompt_update_data=prompt_update_data, # Pass the renamed variable
        owner_username=current_user.username
    )
    # crud.update_prompt now returns the prompt if an update occurred (or even if not, based on current impl.)
    # It returns None only if the prompt was not found or not owned, which we check above.
    if updated_prompt_db is None:
        # This case should ideally be covered by the initial checks.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Update failed: Prompt not found or not owned by user.")

    # If prompt_update_data.prompt_text was provided, a new version was created.
    # We want to display the latest version in this case.
    # If only metadata changed, we still display the latest version.
    latest_version_obj = crud.get_latest_prompt_version(updated_prompt_db)
    return _map_prompt_to_public(updated_prompt_db, latest_version_obj)

@router.delete("/{prompt_id}", status_code=status.HTTP_200_OK)
async def delete_existing_prompt(
    prompt_id: int,
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    # First, check if the prompt exists to give a 404 if it doesn't.
    db_prompt = crud.get_prompt_by_id(prompt_id=prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    # Then, attempt deletion which also checks ownership.
    deleted = crud.delete_prompt(prompt_id=prompt_id, owner_username=current_user.username)
    if not deleted:
        # If not deleted, and it exists, it must be an ownership issue.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to delete this prompt")
    return {"message": "Prompt deleted successfully"}


# Helper for variable substitution
def _extract_variables_from_template(template_string: str) -> set[str]:
    """Extracts all unique variable names (e.g., {{variable}}) from a template string."""
    return set(re.findall(r"\{\{([a-zA-Z0-9_]+)\}\}", template_string))

def _substitute_variables(prompt_text: str, variables: Dict[str, Any]) -> str:
    """
    Substitutes variables in the prompt_text.
    Uses a custom delimiter for string.Template to match {{variable}}.
    Raises ValueError if a variable in the template is not found in the provided variables.
    """
    class CustomTemplate(string.Template):
        delimiter = "{{"
        pattern = r"\{\{(?P<braced>[a-zA-Z0-9_]+)\}\}" # Adjusted pattern

    # Validate all variables in the template are present in the input
    template_vars = _extract_variables_from_template(prompt_text)
    missing_vars = template_vars - set(variables.keys())
    if missing_vars:
        raise ValueError(f"Missing variables: {', '.join(missing_vars)}")

    # string.Template expects variables without the braces for substitution
    # The pattern defined above should handle the {{var}} style directly if we use substitute
    # However, standard string.Template uses $var or ${var}.
    # To use {{var}}, we need to adapt.
    # A simpler approach for {{var}} might be direct replacement if string.Template is tricky with {{}}

    # Let's try a more direct replacement approach for {{var}}
    # This avoids complexities with string.Template's default $ delimiter.

    substituted_text = prompt_text
    for var_name in template_vars:
        placeholder = f"{{{{{var_name}}}}}" # This creates the {{variable_name}} string
        if var_name in variables:
            substituted_text = substituted_text.replace(placeholder, str(variables[var_name]))
        # The check for missing_vars already handled errors.

    # Check if any placeholders remain unsubstituted (e.g. if variables contained non-string values that didn't cast well, though str() should handle most)
    # This is more of a safeguard. The primary check is missing_vars.
    remaining_placeholders = _extract_variables_from_template(substituted_text)
    if remaining_placeholders:
         # This case should ideally not be hit if missing_vars check is robust
         # and all inputs are converted to strings.
         # Could happen if a variable name is like {{var{{another_var}}}} - but our regex for extraction is simple.
        raise ValueError(f"Failed to substitute all variables. Remaining: {', '.join(remaining_placeholders)}")

    return substituted_text


@router.post("/{prompt_id}/execute", response_model=schemas.PromptExecuteResponse)
async def execute_prompt_with_variables(
    prompt_id: int,
    request: schemas.PromptExecuteRequest,
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    db_prompt = crud.get_prompt_by_id(prompt_id=prompt_id)
    if db_prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    if db_prompt.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    prompt_text_to_execute = ""
    target_version_number = request.version_number

    if target_version_number is not None:
        specific_version = crud.get_prompt_version(db_prompt, target_version_number)
        if not specific_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {target_version_number} not found for prompt {prompt_id}"
            )
        prompt_text_to_execute = specific_version.prompt_text
    else:
        latest_version = crud.get_latest_prompt_version(db_prompt)
        if not latest_version: # Should not happen if prompt exists and has versions
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No versions found for this prompt to execute.")
        prompt_text_to_execute = latest_version.prompt_text

    try:
        executed_text = _substitute_variables(prompt_text_to_execute, request.variables)
    except ValueError as e: # Catches missing variables
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return schemas.PromptExecuteResponse(executed_prompt_text=executed_text)

@router.get("/{prompt_id}/versions", response_model=List[schemas.PromptVersionPublic])
async def list_prompt_versions(
    prompt_id: int,
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    db_prompt = crud.get_prompt_by_id(prompt_id=prompt_id)
    if db_prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    if db_prompt.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    if not db_prompt.versions:
        return [] # Return empty list if no versions exist

    return [
        schemas.PromptVersionPublic(
            prompt_text=v.prompt_text,
            version_number=v.version_number,
            created_at=v.created_at
        ) for v in db_prompt.versions
    ]

@router.get("/{prompt_id}/versions/{version_number}", response_model=schemas.PromptVersionPublic)
async def get_specific_prompt_version_detail( # Renamed to avoid conflict with read_single_prompt's version param
    prompt_id: int,
    version_number: int,
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    db_prompt = crud.get_prompt_by_id(prompt_id=prompt_id)
    if db_prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    if db_prompt.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    version_detail = crud.get_prompt_version(db_prompt, version_number)
    if not version_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found for prompt {prompt_id}"
        )

    return schemas.PromptVersionPublic(
        prompt_text=version_detail.prompt_text,
        version_number=version_detail.version_number,
        created_at=version_detail.created_at
    )
