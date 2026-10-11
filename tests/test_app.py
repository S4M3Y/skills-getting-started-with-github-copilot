from copy import deepcopy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture
def client():
    original_activities = deepcopy(activities)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        activities.clear()
        activities.update(original_activities)


def signup_url(activity_name: str) -> str:
    return f"/activities/{quote(activity_name, safe='')}/signup"


def test_root_redirects_to_web_app(client: TestClient):
    # Arrange

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_static_web_app_is_served(client: TestClient):
    # Arrange

    # Act
    response = client.get("/static/index.html")

    # Assert
    assert response.status_code == 200
    assert "Mergington High School Activities" in response.text


def test_get_activities_returns_activity_data(client: TestClient):
    # Arrange
    expected_activities = deepcopy(activities)

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected_activities


def test_signup_adds_participant(client: TestClient):
    # Arrange
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"

    # Act
    response = client.post(signup_url(activity_name), params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    assert email in activities[activity_name]["participants"]


def test_signup_rejects_duplicate_participant(client: TestClient):
    # Arrange
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"
    client.post(signup_url(activity_name), params={"email": email})

    # Act
    response = client.post(signup_url(activity_name), params={"email": email})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"
    assert activities[activity_name]["participants"].count(email) == 1


@pytest.mark.parametrize("method", ["post", "delete"])
def test_signup_routes_reject_unknown_activity(client: TestClient, method: str):
    # Arrange
    url = signup_url("Unknown Activity")

    # Act
    response = getattr(client, method)(url, params={"email": "student@mergington.edu"})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_remove_signup_removes_participant(client: TestClient):
    # Arrange
    activity_name = "Chess Club"
    email = activities[activity_name]["participants"][0]

    # Act
    response = client.delete(signup_url(activity_name), params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Removed {email} from {activity_name}"}
    assert email not in activities[activity_name]["participants"]


def test_remove_signup_rejects_unregistered_participant(client: TestClient):
    # Arrange
    activity_name = "Chess Club"
    email = "not.registered@mergington.edu"

    # Act
    response = client.delete(signup_url(activity_name), params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


@pytest.mark.parametrize("method", ["post", "delete"])
def test_signup_routes_require_email_query_parameter(client: TestClient, method: str):
    # Arrange
    url = signup_url("Chess Club")

    # Act
    response = getattr(client, method)(url)

    # Assert
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "email"]
