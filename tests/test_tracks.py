def test_list_tracks(client, sample_track):
    response = client.get('/api/tracks/')
    assert response.status_code == 200
    assert len(response.json['tracks']) == 1

def test_get_track(client, sample_track):
    response = client.get(f'/api/tracks/{sample_track.id}')
    assert response.status_code == 200
    assert response.json['title'] == sample_track.title

def test_stream_track(client, sample_track):
    response = client.get(f'/api/tracks/{sample_track.id}/stream')
    assert response.status_code == 200
    assert 'stream_url' in response.json

def test_like_track(auth_client, sample_track):
    response = auth_client.post(f'/api/tracks/{sample_track.id}/like')
    assert response.status_code == 201
    fav_response = auth_client.get('/api/tracks/favorites')
    assert fav_response.status_code == 200
    assert len(fav_response.json['tracks']) == 1

def test_unlike_track(auth_client, sample_track):
    auth_client.post(f'/api/tracks/{sample_track.id}/like')
    response = auth_client.delete(f'/api/tracks/{sample_track.id}/like')
    assert response.status_code == 200
    fav_response = auth_client.get('/api/tracks/favorites')
    assert len(fav_response.json['tracks']) == 0

def test_record_play(auth_client, sample_track):
    response = auth_client.post(f'/api/tracks/{sample_track.id}/play')
    assert response.status_code == 202

def test_search_tracks(client, sample_track):
    response = client.get('/api/tracks/?q=Test')
    assert response.status_code == 200
    assert len(response.json['tracks']) == 1
    response = client.get('/api/tracks/?q=nonexistent')
    assert response.status_code == 200
    assert len(response.json['tracks']) == 0