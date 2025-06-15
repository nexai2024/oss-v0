from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from .. import auth, crud, models, schemas # Main crud (for api_keys) and auth (for key utils)
# We need to pass the main crud module to create_deployed_api_key if it needs to call
# other crud functions e.g. api_endpoints_crud_module.
# For this, we'll assume `crud` contains all necessary sub-crud access or functions.

router = APIRouter(
    prefix="/user/api-keys",
    tags=["User API Keys"],
    dependencies=[Depends(auth.get_current_active_user)],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.NewDeployedAPIAccessKey, status_code=status.HTTP_201_CREATED)
async def create_new_deployed_api_key(
    key_data: schemas.DeployedAPIAccessKeyCreate,
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    full_key = auth.generate_api_key()
    key_hash = auth.hash_api_key(full_key)
    key_prefix = auth.get_key_prefix(full_key)

    try:
        # crud.create_deployed_api_key expects api_endpoints_crud_module.
        # We pass the main `crud` module which should contain access to api_endpoint functions.
        db_key = crud.create_deployed_api_key(
            key_data=key_data,
            owner_username=current_user.username,
            full_key=full_key, # For context, not stored
            key_hash=key_hash,
            key_prefix=key_prefix,
            api_endpoints_crud_module=crud # Pass main crud as it contains get_api_endpoint_by_id
        )
    except HTTPException as e: # Catch validation errors from CRUD
        raise e

    return schemas.NewDeployedAPIAccessKey(
        full_key=full_key, # This is the only time the full key is shown
        id=db_key.id,
        name=db_key.name,
        api_endpoint_id=db_key.api_endpoint_id,
        key_prefix=db_key.key_prefix,
        owner_username=db_key.owner_username,
        created_at=db_key.created_at,
        last_used_at=db_key.last_used_at,
        is_active=db_key.is_active
    )

@router.get("/", response_model=List[schemas.DeployedAPIAccessKeyPublic])
async def list_user_deployed_api_keys(
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    keys_in_db = crud.get_deployed_api_keys_by_owner(owner_username=current_user.username)
    return keys_in_db # Direct return as Pydantic handles conversion via orm_mode

@router.delete("/{key_id}", status_code=status.HTTP_200_OK)
async def deactivate_user_api_key(
    key_id: int,
    current_user: models.UserInDB = Depends(auth.get_current_active_user)
):
    success = crud.deactivate_deployed_api_key(key_id=key_id, owner_username=current_user.username)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found or not owned by user")
    return {"message": "API Key deactivated successfully"}
