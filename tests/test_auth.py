def test_register_and_login(client):
    response = client.post(
        "/auth/register",
        data={
            "email": "coach@example.com",
            "password": "secret123",
            "confirm_password": "secret123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"club" in response.data.lower() or b"Club" in response.data

    client.get("/auth/logout", follow_redirects=True)
    response = client.post(
        "/auth/login",
        data={"email": "coach@example.com", "password": "secret123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
