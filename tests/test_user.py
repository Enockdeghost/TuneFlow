def test_update_preferences(auth_client):
    response = auth_client.put('/api/user/preferences', json={
        'eq_preset': 'rock',
        'theme': 'dark'
    })
    assert response.status_code == 200
    assert response.json['preferences']['eq_preset'] == 'rock'

def test_get_stats(auth_client, sample_track):
    auth_client.post(f'/api/tracks/{sample_track.id}/play')
    response = auth_client.get('/api/user/stats')
    assert response.status_code == 200
    assert 'total_listening_hours' in response.json