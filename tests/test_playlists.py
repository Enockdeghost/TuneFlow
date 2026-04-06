def test_create_playlist(auth_client):
    response = auth_client.post('/api/playlists/', json={
        'name': 'My Playlist',
        'description': 'Test playlist',
        'is_public': True
    })
    assert response.status_code == 201
    assert response.json['id'] is not None

def test_list_playlists(auth_client):
    auth_client.post('/api/playlists/', json={'name': 'Playlist 1'})
    auth_client.post('/api/playlists/', json={'name': 'Playlist 2'})
    response = auth_client.get('/api/playlists/')
    assert response.status_code == 200
    assert len(response.json['playlists']) == 2

def test_add_track_to_playlist(auth_client, sample_track):
    create_resp = auth_client.post('/api/playlists/', json={'name': 'Test Playlist'})
    assert create_resp.status_code == 201
    playlist_id = create_resp.json['id']
    response = auth_client.post(f'/api/playlists/{playlist_id}/tracks', json={'track_id': sample_track.id})
    assert response.status_code == 201