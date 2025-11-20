"""Team and organization management"""
import secrets
import logging
from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class TeamMember(BaseModel):
    """Team member"""
    id: str
    team_id: str
    user_id: str
    email: str
    role: Role
    invited_by: Optional[str] = None
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class Team(BaseModel):
    """Team/organization"""
    id: str
    name: str
    owner_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    plan: str = "free"
    stripe_customer_id: Optional[str] = None
    settings: dict = Field(default_factory=dict)


class Invitation(BaseModel):
    """Team invitation"""
    id: str
    team_id: str
    email: str
    role: Role
    invited_by: str
    token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    accepted: bool = False


class TeamManager:
    """Manage teams and members"""

    def __init__(self):
        self._teams: dict[str, Team] = {}
        self._members: dict[str, list[TeamMember]] = {}
        self._invitations: dict[str, Invitation] = {}

    # Team operations
    def create_team(
        self,
        team_id: str,
        name: str,
        owner_id: str,
        owner_email: str,
    ) -> Team:
        """Create a new team"""
        team = Team(
            id=team_id,
            name=name,
            owner_id=owner_id,
        )
        self._teams[team_id] = team

        # Add owner as first member
        owner_member = TeamMember(
            id=f"{team_id}:{owner_id}",
            team_id=team_id,
            user_id=owner_id,
            email=owner_email,
            role=Role.OWNER,
        )
        self._members[team_id] = [owner_member]

        logger.info(f"Created team {name} ({team_id}) with owner {owner_id}")
        return team

    def get_team(self, team_id: str) -> Optional[Team]:
        return self._teams.get(team_id)

    def update_team(self, team_id: str, **updates) -> Optional[Team]:
        team = self._teams.get(team_id)
        if not team:
            return None

        for key, value in updates.items():
            if hasattr(team, key):
                setattr(team, key, value)

        return team

    def delete_team(self, team_id: str) -> bool:
        if team_id not in self._teams:
            return False

        del self._teams[team_id]
        self._members.pop(team_id, None)

        # Clean up invitations
        to_delete = [
            inv_id for inv_id, inv in self._invitations.items()
            if inv.team_id == team_id
        ]
        for inv_id in to_delete:
            del self._invitations[inv_id]

        return True

    # Member operations
    def get_members(self, team_id: str) -> list[TeamMember]:
        return self._members.get(team_id, [])

    def add_member(
        self,
        team_id: str,
        user_id: str,
        email: str,
        role: Role,
        invited_by: Optional[str] = None,
    ) -> TeamMember:
        """Add a member to a team"""
        member = TeamMember(
            id=f"{team_id}:{user_id}",
            team_id=team_id,
            user_id=user_id,
            email=email,
            role=role,
            invited_by=invited_by,
        )

        if team_id not in self._members:
            self._members[team_id] = []

        self._members[team_id].append(member)
        logger.info(f"Added {email} to team {team_id} as {role}")
        return member

    def update_member_role(
        self,
        team_id: str,
        user_id: str,
        role: Role,
    ) -> Optional[TeamMember]:
        """Update a member's role"""
        members = self._members.get(team_id, [])
        for member in members:
            if member.user_id == user_id:
                member.role = role
                return member
        return None

    def remove_member(self, team_id: str, user_id: str) -> bool:
        """Remove a member from a team"""
        members = self._members.get(team_id, [])
        for i, member in enumerate(members):
            if member.user_id == user_id:
                del members[i]
                logger.info(f"Removed {user_id} from team {team_id}")
                return True
        return False

    def get_user_teams(self, user_id: str) -> list[dict]:
        """Get all teams a user belongs to"""
        result = []
        for team_id, members in self._members.items():
            for member in members:
                if member.user_id == user_id and member.is_active:
                    team = self._teams.get(team_id)
                    if team:
                        result.append({
                            "team": team,
                            "role": member.role,
                        })
        return result

    # Invitation operations
    def create_invitation(
        self,
        team_id: str,
        email: str,
        role: Role,
        invited_by: str,
        expires_hours: int = 72,
    ) -> Invitation:
        """Create a team invitation"""
        from datetime import timedelta

        invitation = Invitation(
            id=secrets.token_urlsafe(16),
            team_id=team_id,
            email=email,
            role=role,
            invited_by=invited_by,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
        )

        self._invitations[invitation.id] = invitation
        logger.info(f"Created invitation for {email} to team {team_id}")
        return invitation

    def accept_invitation(
        self,
        token: str,
        user_id: str,
    ) -> Optional[TeamMember]:
        """Accept a team invitation"""
        # Find invitation by token
        invitation = None
        for inv in self._invitations.values():
            if inv.token == token and not inv.accepted:
                invitation = inv
                break

        if not invitation:
            return None

        if datetime.utcnow() > invitation.expires_at:
            return None

        # Add member
        member = self.add_member(
            team_id=invitation.team_id,
            user_id=user_id,
            email=invitation.email,
            role=invitation.role,
            invited_by=invitation.invited_by,
        )

        invitation.accepted = True
        return member

    def get_pending_invitations(self, team_id: str) -> list[Invitation]:
        """Get pending invitations for a team"""
        return [
            inv for inv in self._invitations.values()
            if inv.team_id == team_id and not inv.accepted
        ]

    def cancel_invitation(self, invitation_id: str) -> bool:
        """Cancel an invitation"""
        if invitation_id in self._invitations:
            del self._invitations[invitation_id]
            return True
        return False

    # Permission checks
    def has_permission(
        self,
        team_id: str,
        user_id: str,
        required_role: Role,
    ) -> bool:
        """Check if user has required role or higher"""
        role_hierarchy = {
            Role.VIEWER: 0,
            Role.MEMBER: 1,
            Role.ADMIN: 2,
            Role.OWNER: 3,
        }

        members = self._members.get(team_id, [])
        for member in members:
            if member.user_id == user_id and member.is_active:
                return role_hierarchy[member.role] >= role_hierarchy[required_role]
        return False


# Global team manager
_team_manager: Optional[TeamManager] = None


def get_team_manager() -> TeamManager:
    global _team_manager
    if _team_manager is None:
        _team_manager = TeamManager()
    return _team_manager
