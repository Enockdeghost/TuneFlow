from flask import Blueprint
from flask_jwt_extended import get_jwt_identity
from app.models.user import User
from app.models.playlist import Playlist

frontend = Blueprint('frontend', __name__, template_folder='../templates', static_folder='../static')

@frontend.context_processor
def inject_user_and_playlists():
    user = None
    user_playlists = []
    try:
        user_id = get_jwt_identity()
        if user_id:
            # Convert to int (JWT identity is stored as string)
            user = User.query.get(int(user_id))
            if user:
                user_playlists = Playlist.query.filter_by(user_id=user.id).order_by(Playlist.created_at.desc()).all()
    except Exception as e:
        print(f"Context processor error: {e}")
    return dict(user=user, user_playlists=user_playlists)

from . import routes