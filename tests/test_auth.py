def test_register_success(client):
    response = client.post('/api/auth/register', json={
        'email': 'new@example.com',
        'username': 'newuser',
        'password': 'password123'
    })
    assert response.status_code == 201

def test_register_duplicate_email(client):
    client.post('/api/auth/register', json={
        'email': 'dupe@example.com',
        'username': 'dupeuser',
        'password': 'password123'
    })
    response = client.post('/api/auth/register', json={
        'email': 'dupe@example.com',
        'username': 'otheruser',
        'password': 'password123'
    })
    assert response.status_code == 409

def test_login_success(client):
    client.post('/api/auth/register', json={
        'email': 'login@example.com',
        'username': 'loginuser',
        'password': 'password123'
    })
    response = client.post('/api/auth/login', json={
        'email': 'login@example.com',
        'password': 'password123'
    })
    assert response.status_code == 200

def test_login_invalid_credentials(client):
    response = client.post('/api/auth/login', json={
        'email': 'nonexistent@example.com',
        'password': 'wrong'
    })
    assert response.status_code == 401

def test_profile_protected(client):
    response = client.get('/api/auth/profile')
    assert response.status_code == 401

def test_profile_authenticated(auth_client):
    response = auth_client.get('/api/auth/profile')
    assert response.status_code == 200
    assert response.json['username'] == 'testuser'

def test_logout(auth_client):
    response = auth_client.post('/api/auth/logout')
    assert response.status_code == 200
    # After logout, profile should be inaccessible
    profile_resp = auth_client.get('/api/auth/profile')
    assert profile_resp.status_code == 401