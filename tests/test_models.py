def test_user_password_hashing():
    from app.models.user import User
    user = User(email='test@hash.com', username='hashuser')
    user.set_password('secret123')
    assert user.check_password('secret123')
    assert not user.check_password('wrong')
    assert user.password_hash != 'secret123'

def test_track_repr(sample_track):
    assert repr(sample_track) == f'<Track {sample_track.title}>'