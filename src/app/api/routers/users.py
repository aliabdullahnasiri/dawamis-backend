from fastapi import APIRouter, status

from app.api.dependencies.auth import CurrentActiveSession
from app.api.dependencies.db import DBSession
from app.schemas.user.data.profile import UserData
from app.schemas.user.request.profile import (
    UpdateEmailRequest,
    UpdateUsernameRequest,
    UpdateUserRequest,
)
from app.schemas.user.response.profile import GetUserResponse
from app.services.user import UserService

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/me", response_model=GetUserResponse)
async def get_me(
    session: CurrentActiveSession,
) -> GetUserResponse:
    """
    Retrieve the profile of the currently authenticated user.
    """
    return GetUserResponse(data=UserData.model_validate(session.user))


@router.patch("/me", response_model=GetUserResponse)
async def update_me(
    request: UpdateUserRequest,
    session: CurrentActiveSession,
    db: DBSession,
) -> GetUserResponse:
    """
    Update the profile of the currently authenticated user.
    """
    updated_user = await UserService.update(db, session.user, request)
    return GetUserResponse(data=UserData.model_validate(updated_user))


@router.patch("/me/email", response_model=GetUserResponse)
async def update_my_email(
    request: UpdateEmailRequest,
    session: CurrentActiveSession,
    db: DBSession,
) -> GetUserResponse:
    """
    Update the email address of the currently authenticated user.
    """
    updated_user = await UserService.update_email(db, session.user, request.email)
    return GetUserResponse(data=UserData.model_validate(updated_user))


@router.patch("/me/username", response_model=GetUserResponse)
async def update_my_username(
    request: UpdateUsernameRequest,
    session: CurrentActiveSession,
    db: DBSession,
) -> GetUserResponse:
    """
    Update the username of the currently authenticated user.
    """
    updated_user = await UserService.update_username(
        db, session.user, request.user_name
    )
    return GetUserResponse(data=UserData.model_validate(updated_user))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    session: CurrentActiveSession,
    db: DBSession,
) -> None:
    """
    Delete the account of the currently authenticated user.
    """
    await UserService.delete(db, session.user)
