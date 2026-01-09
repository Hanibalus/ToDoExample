import pytest


def test_register(client, test_user_data):
    """Test user registration"""
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == test_user_data["email"]
    assert data["user"]["display_name"] == test_user_data["display_name"]


def test_register_duplicate_email(client, test_user_data):
    """Test duplicate email registration fails"""
    # Register first user
    client.post("/api/v1/auth/register", json=test_user_data)
    
    # Try to register with same email
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 409


def test_login(client, test_user_data):
    """Test user login"""
    # Register
    client.post("/api/v1/auth/register", json=test_user_data)
    
    # Login
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]


def test_login_invalid_password(client, test_user_data):
    """Test login with invalid password"""
    # Register
    client.post("/api/v1/auth/register", json=test_user_data)
    
    # Try wrong password
    login_data = {
        "email": test_user_data["email"],
        "password": "WrongPassword123!"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401


def test_refresh_token(client, test_user_data):
    """Test token refresh"""
    # Register
    register_response = client.post("/api/v1/auth/register", json=test_user_data)
    refresh_token = register_response.json()["refresh_token"]
    
    # Refresh
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["access_token"]


def test_logout(client, auth_token):
    """Test logout"""
    # Get refresh token first (need to register again for this test)
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@test.com",
            "password": "Pass123!",
            "display_name": "Logout User"
        }
    )
    refresh_token = register_response.json()["refresh_token"]
    
    # Logout
    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    
    # Try to use refresh token - should fail
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 401
