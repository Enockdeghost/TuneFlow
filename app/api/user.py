from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from app.extensions import db
from app.models.user import User
from app.models.track import Track
from app.models.listening_event import ListeningEvent
from app.models.favorite import Favorite
from app.models.playlist import Playlist
from app.models.comment import Comment
from app.models.follow import Follow

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'subscription_tier': user.subscription_tier,
        'role': user.role,
        'preferences': user.preferences,
        'created_at': user.created_at
    })

@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 409
        user.username = data['username']

    if 'email' in data and data['email'] != user.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409
        user.email = data['email']

    db.session.commit()
    return jsonify({'message': 'Profile updated'})

@user_bp.route('/preferences', methods=['GET'])
@jwt_required()
def get_preferences():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    return jsonify(user.preferences or {})

@user_bp.route('/preferences', methods=['PUT'])
@jwt_required()
def update_preferences():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    allowed_keys = {'eq_preset', 'bass_boost', 'playback_speed', 'crossfade_enabled', 'gapless_enabled', 'theme'}
    new_prefs = {k: v for k, v in data.items() if k in allowed_keys}

    if not new_prefs:
        return jsonify({'error': 'No valid preferences provided'}), 400

    if user.preferences is None:
        user.preferences = {}
    user.preferences.update(new_prefs)
    db.session.commit()
    return jsonify({'message': 'Preferences updated', 'preferences': user.preferences})

@user_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    history = ListeningEvent.query.filter_by(user_id=user_id)\
        .order_by(ListeningEvent.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    tracks = []
    for event in history.items:
        track = Track.query.get(event.track_id)
        if track:
            tracks.append({
                'track_id': track.id,
                'title': track.title,
                'artist': track.artist,
                'duration': track.duration,
                'cover_url': track.cover_url,
                'listened_seconds': event.listened_seconds,
                'completed': event.completed,
                'listened_at': event.created_at
            })

    return jsonify({
        'history': tracks,
        'total': history.total,
        'page': page,
        'pages': history.pages
    })

@user_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    user_id = int(get_jwt_identity())

    total_seconds = db.session.query(func.sum(ListeningEvent.listened_seconds)).filter_by(user_id=user_id).scalar() or 0
    total_hours = round(total_seconds / 3600, 1)

    top_artists = db.session.query(
        Track.artist, func.count(ListeningEvent.id).label('plays')
    ).join(ListeningEvent, ListeningEvent.track_id == Track.id)\
     .filter(ListeningEvent.user_id == user_id, Track.artist.isnot(None))\
     .group_by(Track.artist)\
     .order_by(func.count(ListeningEvent.id).desc())\
     .limit(5).all()

    top_genres = db.session.query(
        Track.genre, func.count(ListeningEvent.id).label('plays')
    ).join(ListeningEvent, ListeningEvent.track_id == Track.id)\
     .filter(ListeningEvent.user_id == user_id, Track.genre.isnot(None))\
     .group_by(Track.genre)\
     .order_by(func.count(ListeningEvent.id).desc())\
     .limit(5).all()

    favorites_count = Favorite.query.filter_by(user_id=user_id).count()
    playlists_count = Playlist.query.filter_by(user_id=user_id).count()
    comments_count = Comment.query.filter_by(user_id=user_id).count()
    following_count = Follow.query.filter_by(follower_id=user_id).count()
    followers_count = Follow.query.filter_by(followed_id=user_id).count()

    return jsonify({
        'total_listening_hours': total_hours,
        'top_artists': [{'artist': a, 'plays': p} for a, p in top_artists],
        'top_genres': [{'genre': g, 'plays': p} for g, p in top_genres],
        'favorites': favorites_count,
        'playlists': playlists_count,
        'comments': comments_count,
        'following': following_count,
        'followers': followers_count
    })