"""Team management routes"""
import uuid
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from api.services.teams import get_team_manager, Role

router = APIRouter(prefix="/teams", tags=["teams"])


class CreateTeamRequest(BaseModel):
    name: str
    owner_email: str


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "member"


class UpdateRoleRequest(BaseModel):
    role: str


async def get_user_id(x_api_key: str = Header(...)) -> str:
    # In production, extract from JWT or session
    if ":" in x_api_key:
        return x_api_key.split(":")[0]
    return "default-user"


@router.post("")
async def create_team(
    request: CreateTeamRequest,
    x_api_key: str = Header(...),
):
    """Create a new team"""
    user_id = await get_user_id(x_api_key)
    manager = get_team_manager()

    team_id = str(uuid.uuid4())
    team = manager.create_team(
        team_id=team_id,
        name=request.name,
        owner_id=user_id,
        owner_email=request.owner_email,
    )

    return team.model_dump()


@router.get("")
async def list_user_teams(x_api_key: str = Header(...)):
    """List teams the user belongs to"""
    user_id = await get_user_id(x_api_key)
    manager = get_team_manager()

    teams = manager.get_user_teams(user_id)
    return {
        "teams": [
            {
                "id": t["team"].id,
                "name": t["team"].name,
                "role": t["role"],
                "plan": t["team"].plan,
            }
            for t in teams
        ]
    }


@router.get("/{team_id}")
async def get_team(team_id: str, x_api_key: str = Header(...)):
    """Get team details"""
    user_id = await get_user_id(x_api_key)
    manager = get_team_manager()

    if not manager.has_permission(team_id, user_id, Role.VIEWER):
        raise HTTPException(status_code=403, detail="Access denied")

    team = manager.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return team.model_dump()


@router.get("/{team_id}/members")
async def list_members(team_id: str, x_api_key: str = Header(...)):
    """List team members"""
    user_id = await get_user_id(x_api_key)
    manager = get_team_manager()

    if not manager.has_permission(team_id, user_id, Role.VIEWER):
        raise HTTPException(status_code=403, detail="Access denied")

    members = manager.get_members(team_id)
    return {
        "members": [m.model_dump() for m in members]
    }


@router.post("/{team_id}/invitations")
async def invite_member(
    team_id: str,
    request: InviteMemberRequest,
    x_api_key: str = Header(...),
):
    """Invite a member to the team"""
    user_id = await get_user_id(x_api_key)
    manager = get_team_manager()

    if not manager.has_permission(team_id, user_id, Role.ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    role = Role(request.role)
    invitation = manager.create_invitation(
        team_id=team_id,
        email=request.email,
        role=role,
        invited_by=user_id,
    )

    return {
        "invitation_id": invitation.id,
        "token": invitation.token,
        "expires_at": invitation.expires_at,
    }


@router.post("/invitations/accept")
async def accept_invitation(
    token: str,
    x_api_key: str = Header(...),
):
    """Accept a team invitation"""
    user_id = await get_user_id(x_api_key)
    manager = get_team_manager()

    member = manager.accept_invitation(token, user_id)
    if not member:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")

    return {"status": "accepted", "team_id": member.team_id}


@router.put("/{team_id}/members/{member_user_id}/role")
async def update_member_role(
    team_id: str,
    member_user_id: str,
    request: UpdateRoleRequest,
    x_api_key: str = Header(...),
):
    """Update a member's role"""
    user_id = await get_user_id(x_api_key)
    manager = get_team_manager()

    if not manager.has_permission(team_id, user_id, Role.ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    role = Role(request.role)
    member = manager.update_member_role(team_id, member_user_id, role)

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    return member.model_dump()


@router.delete("/{team_id}/members/{member_user_id}")
async def remove_member(
    team_id: str,
    member_user_id: str,
    x_api_key: str = Header(...),
):
    """Remove a member from the team"""
    user_id = await get_user_id(x_api_key)
    manager = get_team_manager()

    if not manager.has_permission(team_id, user_id, Role.ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    if not manager.remove_member(team_id, member_user_id):
        raise HTTPException(status_code=404, detail="Member not found")

    return {"status": "removed"}


@router.delete("/{team_id}")
async def delete_team(team_id: str, x_api_key: str = Header(...)):
    """Delete a team"""
    user_id = await get_user_id(x_api_key)
    manager = get_team_manager()

    if not manager.has_permission(team_id, user_id, Role.OWNER):
        raise HTTPException(status_code=403, detail="Owner access required")

    if not manager.delete_team(team_id):
        raise HTTPException(status_code=404, detail="Team not found")

    return {"status": "deleted"}
