"""
Comprehensive test suite for the Mergington High School Activities API

Uses Arrange-Act-Assert (AAA) pattern for test structure:
- Arrange: Set up test data and fixtures
- Act: Execute the function or endpoint being tested
- Assert: Verify the results
"""

import pytest
from copy import deepcopy
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Provide a TestClient instance for making requests to the app"""
    return TestClient(app)


@pytest.fixture
def fresh_activities():
    """
    Provide a clean copy of activities for each test.
    Uses deepcopy to ensure tests don't interfere with each other.
    """
    return deepcopy(activities)


@pytest.fixture
def app_with_fresh_data(monkeypatch, fresh_activities):
    """
    Provide an app instance with isolated activity data.
    Monkeypatch replaces the global activities dict for this test.
    """
    monkeypatch.setattr("app.activities", fresh_activities)
    return app


# ============================================================================
# GET /activities Tests
# ============================================================================


class TestGetActivities:
    """Tests for fetching all available activities"""

    def test_get_activities_returns_all_activities(self, client):
        """
        Arrange: Client is ready
        Act: Send GET request to /activities
        Assert: Should return all 9 activities
        """
        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        activities_data = response.json()
        assert len(activities_data) == 9
        assert "Chess Club" in activities_data
        assert "Programming Class" in activities_data

    def test_get_activities_returns_correct_structure(self, client):
        """
        Arrange: Client is ready
        Act: Send GET request to /activities
        Assert: Activities should have required fields
        """
        # Act
        response = client.get("/activities")
        activities_data = response.json()

        # Assert - Verify structure of first activity
        first_activity = activities_data["Chess Club"]
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
        assert isinstance(first_activity["participants"], list)

    def test_get_activities_includes_initial_participants(self, client):
        """
        Arrange: Client is ready
        Act: Send GET request to /activities
        Assert: Activities should show pre-registered participants
        """
        # Act
        response = client.get("/activities")
        activities_data = response.json()

        # Assert
        chess_club = activities_data["Chess Club"]
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


# ============================================================================
# POST /activities/{activity_name}/signup Tests
# ============================================================================


class TestSignupForActivity:
    """Tests for signing up students to activities"""

    def test_signup_valid_student(self, client, app_with_fresh_data):
        """
        Arrange: New student email and valid activity name
        Act: Send POST request to signup endpoint
        Assert: Student should be added to participants
        """
        # Arrange
        email = "newstudent@mergington.edu"
        activity = "Chess Club"

        # Act
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {email} for {activity}"

    def test_signup_adds_participant_to_list(self, client, app_with_fresh_data):
        """
        Arrange: New student email
        Act: Sign up student, then fetch activities
        Assert: Student should appear in participants list
        """
        # Arrange
        email = "newstudent@mergington.edu"
        activity = "Chess Club"

        # Act
        client.post(f"/activities/{activity}/signup", params={"email": email})
        response = client.get("/activities")
        activities_data = response.json()

        # Assert
        assert email in activities_data[activity]["participants"]

    def test_signup_duplicate_student_rejected(self, client, app_with_fresh_data):
        """
        Arrange: Student already signed up for activity
        Act: Try to sign up the student again
        Assert: Should return 400 error
        """
        # Arrange
        email = "michael@mergington.edu"  # Already signed up for Chess Club
        activity = "Chess Club"

        # Act
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_invalid_activity(self, client):
        """
        Arrange: Non-existent activity name
        Act: Try to sign up for non-existent activity
        Assert: Should return 404 error
        """
        # Arrange
        email = "student@mergington.edu"
        activity = "Nonexistent Activity"

        # Act
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_missing_email_parameter(self, client):
        """
        Arrange: No email parameter in request
        Act: Send POST request without email
        Assert: Should return validation error
        """
        # Arrange
        activity = "Chess Club"

        # Act
        response = client.post(f"/activities/{activity}/signup")

        # Assert
        assert response.status_code in [400, 422]  # Bad request or validation error

    def test_signup_multiple_students_same_activity(self, client, app_with_fresh_data):
        """
        Arrange: Multiple different students
        Act: Sign up each student to the same activity
        Assert: All students should be in participants list
        """
        # Arrange
        activity = "Chess Club"
        students = [
            "alice@mergington.edu",
            "bob@mergington.edu",
            "carol@mergington.edu"
        ]

        # Act
        for student in students:
            client.post(f"/activities/{activity}/signup", params={"email": student})

        response = client.get("/activities")
        participants = response.json()[activity]["participants"]

        # Assert
        for student in students:
            assert student in participants


# ============================================================================
# DELETE /activities/{activity_name}/signup Tests
# ============================================================================


class TestRemoveFromActivity:
    """Tests for removing students from activities"""

    def test_delete_valid_participant(self, client, app_with_fresh_data):
        """
        Arrange: Student is signed up for an activity
        Act: Send DELETE request to remove student
        Assert: Should return success message
        """
        # Arrange
        email = "michael@mergington.edu"
        activity = "Chess Club"

        # Act
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Removed {email} from {activity}"

    def test_delete_removes_participant_from_list(self, client, app_with_fresh_data):
        """
        Arrange: Student is signed up
        Act: Delete student, then fetch activities
        Assert: Student should no longer be in participants
        """
        # Arrange
        email = "michael@mergington.edu"
        activity = "Chess Club"

        # Act
        client.delete(f"/activities/{activity}/signup", params={"email": email})
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]

        # Assert
        assert email not in participants

    def test_delete_nonexistent_participant(self, client, app_with_fresh_data):
        """
        Arrange: Student is NOT signed up for activity
        Act: Try to delete student
        Assert: Should return 400 error
        """
        # Arrange
        email = "nobody@mergington.edu"
        activity = "Chess Club"

        # Act
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_delete_invalid_activity(self, client):
        """
        Arrange: Non-existent activity
        Act: Try to delete from non-existent activity
        Assert: Should return 404 error
        """
        # Arrange
        email = "student@mergington.edu"
        activity = "Nonexistent Activity"

        # Act
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_delete_missing_email_parameter(self, client):
        """
        Arrange: No email parameter
        Act: Send DELETE request without email
        Assert: Should return validation error
        """
        # Arrange
        activity = "Chess Club"

        # Act
        response = client.delete(f"/activities/{activity}/signup")

        # Assert
        assert response.status_code in [400, 422]

    def test_delete_all_participants_from_activity(self, client, app_with_fresh_data):
        """
        Arrange: Activity has multiple participants
        Act: Delete each participant one by one
        Assert: Participants list should eventually be empty
        """
        # Arrange
        activity = "Chess Club"
        response = client.get("/activities")
        participants_to_remove = response.json()[activity]["participants"].copy()

        # Act & Assert
        for email in participants_to_remove:
            response = client.delete(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200

        # Final check
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestSignupWorkflow:
    """Tests for complete signup/unsignup workflows"""

    def test_signup_then_unsignup_workflow(self, client, app_with_fresh_data):
        """
        Arrange: Student signs up for activity
        Act: Student signs up, then unsigns up
        Assert: Student should not be in participants after unsignup
        """
        # Arrange
        email = "newstudent@mergington.edu"
        activity = "Drama Club"

        # Act - Sign up
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200

        # Verify signed up
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]

        # Act - Unsign up
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200

        # Assert - Verify removed
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]

    def test_multiple_signup_and_unsignup_operations(self, client, app_with_fresh_data):
        """
        Arrange: Multiple students and activities
        Act: Mix of signup and unsignup operations
        Assert: Final state should be correct
        """
        # Arrange
        activity1 = "Programming Class"
        activity2 = "Art Class"
        email1 = "student1@mergington.edu"
        email2 = "student2@mergington.edu"

        # Act & Assert - Multiple operations
        # Sign up student1 to both activities
        assert client.post(
            f"/activities/{activity1}/signup",
            params={"email": email1}
        ).status_code == 200
        assert client.post(
            f"/activities/{activity2}/signup",
            params={"email": email1}
        ).status_code == 200

        # Sign up student2 to activity1
        assert client.post(
            f"/activities/{activity1}/signup",
            params={"email": email2}
        ).status_code == 200

        # Remove student1 from activity1
        assert client.delete(
            f"/activities/{activity1}/signup",
            params={"email": email1}
        ).status_code == 200

        # Verify final state
        response = client.get("/activities")
        activity1_participants = response.json()[activity1]["participants"]
        activity2_participants = response.json()[activity2]["participants"]

        assert email1 not in activity1_participants  # Removed
        assert email2 in activity1_participants  # Still there
        assert email1 in activity2_participants  # Still signed up
