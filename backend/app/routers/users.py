from fastapi import APIRouter, Depends, HTTPException

from .. import auth, crud, models, schemas

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)

@router.get("/me", response_model=schemas.UserPublic)
async def read_users_me(current_user: models.UserInDB = Depends(auth.get_current_active_user)):
    # Convert UserInDB to UserPublic for response
    # This assumes UserPublic has all the necessary fields from UserInDB that are safe to expose.
    return schemas.UserPublic(
        username=current_user.username,
        email=current_user.email
        # Add other fields from UserInDB to UserPublic as needed, e.g., id if you add it to UserInDB
    )

# Example of another endpoint, perhaps for fetching a user by ID (admin functionality)
# @router.get("/{user_id}", response_model=schemas.UserPublic)
# async def read_user(user_id: int, current_user: models.UserInDB = Depends(auth.get_current_admin_user)): # Assuming an admin check
#     user = crud.get_user_by_id(user_id=user_id) # This function would need to be added to crud.py
#     if user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user
