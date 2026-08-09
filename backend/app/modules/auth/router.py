from datetime import timedelta

from fastapi import APIRouter

from app.core.security import sign_internal_payload
from app.modules.auth.dependencies import (
    ActiveUserDep,
    CurrentUserDep,
    SessionDep,
    permission_codes,
)
from app.modules.auth.schemas import BootstrapResponse, UserProfileOut, WebSocketTicketOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/bootstrap", response_model=BootstrapResponse)
async def bootstrap(user: CurrentUserDep, session: SessionDep) -> BootstrapResponse:
    permissions = sorted(await permission_codes(user.id, session))
    output = UserProfileOut.model_validate(user)
    output.permissions = permissions
    return BootstrapResponse(user=output, created=False)


@router.get("/me", response_model=UserProfileOut)
async def me(user: CurrentUserDep, session: SessionDep) -> UserProfileOut:
    output = UserProfileOut.model_validate(user)
    output.permissions = sorted(await permission_codes(user.id, session))
    return output


@router.post("/ws-ticket", response_model=WebSocketTicketOut)
async def websocket_ticket(user: ActiveUserDep) -> WebSocketTicketOut:
    expires_in = 120
    return WebSocketTicketOut(
        ticket=sign_internal_payload(
            {"sub": str(user.id), "purpose": "dashboard-websocket"},
            timedelta(seconds=expires_in),
        ),
        expires_in=expires_in,
    )
