def test_admin_access_denied(auth_client):
    response = auth_client.get('/api/admin/users')
    assert response.status_code == 403

def test_admin_access_granted(admin_client):
    response = admin_client.get('/api/admin/users')
    assert response.status_code == 200

def test_admin_create_track(admin_client):
    response = admin_client.post('/api/admin/tracks', json={
        'title': 'Admin Track',
        'file_key': 'admin_test.mp3',
        'artist': 'Admin Artist'
    })
    assert response.status_code == 201