from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import auth, crud, models, schemas

router = APIRouter(
    prefix="/call-logs",
    tags=["API Call Logs"],
    dependencies=[Depends(auth.get_current_active_user)],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[schemas.APICallLogPublic])
async def list_user_api_call_logs(
    current_user: models.UserInDB = Depends(auth.get_current_active_user),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    logs = crud.get_api_call_logs_by_owner(
        owner_username=current_user.username,
        limit=limit,
        offset=offset
    )
    return logs

@router.get("/endpoint/{endpoint_id}", response_model=List[schemas.APICallLogPublic])
async def list_endpoint_api_call_logs(
    endpoint_id: int,
    current_user: models.UserInDB = Depends(auth.get_current_active_user),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    # First, verify the endpoint exists and belongs to the user
    target_endpoint = crud.get_api_endpoint_by_id(endpoint_id)
    if not target_endpoint or target_endpoint.owner_username != current_user.username:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Endpoint not found or not owned by user."
        )

    logs = crud.get_api_call_logs_by_endpoint(
        api_endpoint_id=endpoint_id,
        owner_username=current_user.username, # Pass owner_username for explicit check in CRUD too
        limit=limit,
        offset=offset
    )
    return logs
