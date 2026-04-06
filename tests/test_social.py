def test_follow_user(auth_client, db_session):
    other_user = User(email='other@example.com', username='other')
    other_user.set_password('otherpass')
    db_session.add(other_user)
    db_session.commit()
    response = auth_client.post(f'/api/social/follow/{other_user.id}')
    assert response.status_code == 201
    followers_resp = auth_client.get(f'/api/social/followers/{other_user.id}')
    assert len(followers_resp.json['users']) == 1
    assert followers_resp.json['users'][0]['username'] == 'testuser'

def test_comment_on_track(auth_client, sample_track):
    response = auth_client.post(f'/api/social/track/{sample_track.id}/comments', json={
        'text': 'Great track!'
    })
    assert response.status_code == 201
    comments = auth_client.get(f'/api/social/track/{sample_track.id}/comments')
    assert len(comments.json['comments']) == 1
    assert comments.json['comments'][0]['text'] == 'Great track!'