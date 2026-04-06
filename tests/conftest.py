import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.track import Track
from app.models.playlist import Playlist
from app.models.favorite import Favorite
from app.models.comment import Comment
from app.models.follow import Follow
from app.models.listening_event import ListeningEvent

@pytest.fixture
def app():
    app = create_app('testing')
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    client.post('/api/auth/register', json={
        'email': 'test@example.com',
        'username': 'testuser',
        'password': 'testpass123'
    })
    login_resp = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'testpass123'
    })
    assert login_resp.status_code == 200, "Login failed in fixture"
    return client

@pytest.fixture
def admin_client(client):
    with client.application.app_context():
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(email='admin@example.com', username='admin', role='admin')
            admin.set_password('adminpass123')
            db.session.add(admin)
            db.session.commit()
    login_resp = client.post('/api/auth/login', json={
        'email': 'admin@example.com',
        'password': 'adminpass123'
    })
    assert login_resp.status_code == 200, "Admin login failed in fixture"
    return client

@pytest.fixture
def sample_user(db_session):
    user = User.query.filter_by(email='test@example.com').first()
    if not user:
        user = User(email='test@example.com', username='testuser')
        user.set_password('testpass123')
        db_session.add(user)
        db_session.commit()
    return user

@pytest.fixture
def sample_track(db_session, sample_user):
    track = Track(
        title='Test Track',
        artist='Test Artist',
        album='Test Album',
        genre='Rock',
        duration=180,
        file_key='test.mp3',
        is_premium=False,
        uploaded_by=sample_user.id
    )
    db_session.add(track)
    db_session.commit()
    return track