"""Tests for team management service"""
import pytest
from datetime import datetime

from api.services.teams import TeamManager, Role


class TestTeamManager:
    """Test team manager functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.manager = TeamManager()
        self.owner_id = "owner-123"
        self.owner_email = "owner@test.com"

    def test_create_team(self):
        """Test creating a new team"""
        team = self.manager.create_team(
            team_id="team-1",
            name="Test Team",
            owner_id=self.owner_id,
            owner_email=self.owner_email
        )

        assert team.id == "team-1"
        assert team.name == "Test Team"
        assert len(team.members) == 1
        assert team.members[0].user_id == self.owner_id
        assert team.members[0].role == Role.OWNER

    def test_add_member(self):
        """Test adding a member to team"""
        team = self.manager.create_team(
            team_id="team-2",
            name="Test Team",
            owner_id=self.owner_id,
            owner_email=self.owner_email
        )

        member = self.manager.add_member(
            team_id="team-2",
            user_id="member-456",
            email="member@test.com",
            role=Role.MEMBER
        )

        assert member.user_id == "member-456"
        assert member.role == Role.MEMBER

    def test_create_invitation(self):
        """Test creating team invitation"""
        self.manager.create_team(
            team_id="team-3",
            name="Test Team",
            owner_id=self.owner_id,
            owner_email=self.owner_email
        )

        invitation = self.manager.create_invitation(
            team_id="team-3",
            email="invite@test.com",
            role=Role.MEMBER,
            invited_by=self.owner_id
        )

        assert invitation.email == "invite@test.com"
        assert invitation.role == Role.MEMBER
        assert invitation.token is not None
        assert invitation.expires_at > datetime.utcnow()

    def test_accept_invitation(self):
        """Test accepting team invitation"""
        self.manager.create_team(
            team_id="team-4",
            name="Test Team",
            owner_id=self.owner_id,
            owner_email=self.owner_email
        )

        invitation = self.manager.create_invitation(
            team_id="team-4",
            email="accept@test.com",
            role=Role.ADMIN,
            invited_by=self.owner_id
        )

        member = self.manager.accept_invitation(
            token=invitation.token,
            user_id="new-user-789"
        )

        assert member is not None
        assert member.user_id == "new-user-789"
        assert member.role == Role.ADMIN

    def test_accept_invalid_invitation(self):
        """Test accepting invalid invitation"""
        member = self.manager.accept_invitation(
            token="invalid-token",
            user_id="user-123"
        )
        assert member is None

    def test_remove_member(self):
        """Test removing a member from team"""
        self.manager.create_team(
            team_id="team-5",
            name="Test Team",
            owner_id=self.owner_id,
            owner_email=self.owner_email
        )

        self.manager.add_member(
            team_id="team-5",
            user_id="to-remove",
            email="remove@test.com",
            role=Role.MEMBER
        )

        success = self.manager.remove_member("team-5", "to-remove")
        assert success is True

        team = self.manager.get_team("team-5")
        member_ids = [m.user_id for m in team.members]
        assert "to-remove" not in member_ids

    def test_update_member_role(self):
        """Test updating member role"""
        self.manager.create_team(
            team_id="team-6",
            name="Test Team",
            owner_id=self.owner_id,
            owner_email=self.owner_email
        )

        self.manager.add_member(
            team_id="team-6",
            user_id="promote-user",
            email="promote@test.com",
            role=Role.MEMBER
        )

        member = self.manager.update_member_role(
            team_id="team-6",
            user_id="promote-user",
            new_role=Role.ADMIN
        )

        assert member is not None
        assert member.role == Role.ADMIN

    def test_has_permission(self):
        """Test permission checking"""
        self.manager.create_team(
            team_id="team-7",
            name="Test Team",
            owner_id=self.owner_id,
            owner_email=self.owner_email
        )

        self.manager.add_member(
            team_id="team-7",
            user_id="viewer-user",
            email="viewer@test.com",
            role=Role.VIEWER
        )

        # Owner should have all permissions
        assert self.manager.has_permission("team-7", self.owner_id, Role.ADMIN) is True

        # Viewer should not have member permissions
        assert self.manager.has_permission("team-7", "viewer-user", Role.MEMBER) is False

        # Viewer should have viewer permissions
        assert self.manager.has_permission("team-7", "viewer-user", Role.VIEWER) is True

    def test_get_user_teams(self):
        """Test getting all teams for a user"""
        user_id = "multi-team-user"

        for i in range(3):
            team = self.manager.create_team(
                team_id=f"user-team-{i}",
                name=f"Team {i}",
                owner_id="other-owner",
                owner_email="other@test.com"
            )
            self.manager.add_member(
                team_id=f"user-team-{i}",
                user_id=user_id,
                email="multi@test.com",
                role=Role.MEMBER
            )

        teams = self.manager.get_user_teams(user_id)
        assert len(teams) >= 3

    def test_delete_team(self):
        """Test deleting a team"""
        self.manager.create_team(
            team_id="team-delete",
            name="Delete Team",
            owner_id=self.owner_id,
            owner_email=self.owner_email
        )

        success = self.manager.delete_team("team-delete")
        assert success is True

        team = self.manager.get_team("team-delete")
        assert team is None
