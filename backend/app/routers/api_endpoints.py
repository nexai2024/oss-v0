from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from .. import auth, crud, models, schemas # Main crud (for api_endpoints)
from ..crud import get_prompt_by_id, get_prompt_version # Specific imports from main crud for prompt checks if needed directly
                                                      # However, better to pass prompts_crud module to endpoint crud functions

router = APIRouter(
    prefix="/endpoints",
    tags=["API Endpoints"],
    dependencies=[Depends(auth.get_current_active_user)],
    responses={404: {"description": "API Endpoint not found"}},
)

# Helper to map DB model to Public schema
def _map_endpoint_to_public(db_endpoint: models.APIEndpointInDB) -> schemas.APIEndpointPublic:
    return schemas.APIEndpointPublic(
        id=db_endpoint.id,
        name=db_endpoint.name,
        description=db_endpoint.description,
        path=db_endpoint.path,
        mapped_prompt_id=db_endpoint.mapped_prompt_id,
        mapped_prompt_version=db_endpoint.mapped_prompt_version,
        request_schema=db_endpoint.request_schema,
        response_schema=db_endpoint.response_schema,
        owner_username=db_endpoint.owner_username,
        is_active=db_endpoint.is_active,
        ai_model_name=db_endpoint.ai_model_name # Add new field
    )

@router.post("/", response_model=schemas.APIEndpointPublic, status_code=status.HTTP_201_CREATED)
async def create_new_api_endpoint(
    endpoint_data: schemas.APIEndpointCreate,
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    # The prompts_crud module is crud itself here, as it contains prompt functions
    try:
        created_endpoint_db = crud.create_api_endpoint(
            endpoint_data=endpoint_data,
            owner_username=current_user.username,
            prompts_crud_module=crud # Pass the main crud module
        )
    except HTTPException as e: # Catch validation errors from CRUD
        raise e
    return _map_endpoint_to_public(created_endpoint_db)

@router.get("/", response_model=List[schemas.APIEndpointPublic])
async def read_user_api_endpoints(
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    endpoints_in_db = crud.get_api_endpoints_by_owner(owner_username=current_user.username)
    return [_map_endpoint_to_public(ep) for ep in endpoints_in_db]

@router.get("/{endpoint_id}", response_model=schemas.APIEndpointPublic)
async def read_single_api_endpoint(
    endpoint_id: int,
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    db_endpoint = crud.get_api_endpoint_by_id(endpoint_id=endpoint_id)
    if db_endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Endpoint not found")
    if db_endpoint.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return _map_endpoint_to_public(db_endpoint)

@router.put("/{endpoint_id}", response_model=schemas.APIEndpointPublic)
async def update_existing_api_endpoint(
    endpoint_id: int,
    endpoint_update_data: schemas.APIEndpointUpdate,
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    # First, check existence and ownership for a clearer error if not found for this user
    db_endpoint_check = crud.get_api_endpoint_by_id(endpoint_id=endpoint_id)
    if not db_endpoint_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Endpoint not found")
    if db_endpoint_check.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to update this endpoint")

    try:
        updated_endpoint_db = crud.update_api_endpoint(
            endpoint_id=endpoint_id,
            endpoint_update_data=endpoint_update_data,
            owner_username=current_user.username,
            prompts_crud_module=crud # Pass the main crud module
        )
    except HTTPException as e: # Catch validation errors from CRUD
        raise e

    if updated_endpoint_db is None: # Should be caught by initial checks or validation
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Update failed: API Endpoint not found or not owned by user.")

    return _map_endpoint_to_public(updated_endpoint_db)

@router.delete("/{endpoint_id}", status_code=status.HTTP_200_OK)
async def delete_existing_api_endpoint(
    endpoint_id: int,
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    db_endpoint_check = crud.get_api_endpoint_by_id(endpoint_id=endpoint_id)
    if not db_endpoint_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Endpoint not found")
    if db_endpoint_check.owner_username != current_user.username: # Check ownership before attempting delete
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to delete this endpoint")

    deleted = crud.delete_api_endpoint(endpoint_id=endpoint_id, owner_username=current_user.username)
    if not deleted:
        # This case should ideally be covered by the checks above.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Endpoint not found or delete operation failed")
    return {"message": "API Endpoint deleted successfully"}
