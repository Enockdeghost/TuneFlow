from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, desc
from app.extensions import db
from app.models.user import User
from app.models.track import Track
from app.models.comment import Comment
from app.models.listening_event import ListeningEvent
from app.models.favorite import Favorite
from app.models.playlist import Playlist
from functools import wraps

admin_bp = Blueprint('admin_api', __name__)   # unique name

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    return wrapper

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')

    query = User.query
    if sort == 'created_at':
        order_func = User.created_at.desc() if order == 'desc' else User.created_at.asc()
    elif sort == 'username':
        order_func = User.username.desc() if order == 'desc' else User.username.asc()
    else:
        order_func = User.id.desc()

    users = query.order_by(order_func).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'users': [{
            'id': u.id,
            'email': u.email,
            'username': u.username,
            'subscription_tier': u.subscription_tier,
            'role': u.role,
            'created_at': u.created_at
        } for u in users.items],
        'total': users.total,
        'page': page,
        'pages': users.pages
    })

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if 'subscription_tier' in data:
        user.subscription_tier = data['subscription_tier']
    if 'role' in data:
        user.role = data['role']

    db.session.commit()
    return jsonify({'message': 'User updated'})

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        return jsonify({'error': 'Cannot delete admin user'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'})

@admin_bp.route('/tracks', methods=['GET'])
@jwt_required()
@admin_required
def list_tracks_admin():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')

    query = Track.query
    if sort == 'created_at':
        order_func = Track.created_at.desc() if order == 'desc' else Track.created_at.asc()
    elif sort == 'play_count':
        order_func = Track.play_count.desc() if order == 'desc' else Track.play_count.asc()
    else:
        order_func = Track.id.desc()

    tracks = query.order_by(order_func).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'tracks': [{
            'id': t.id,
            'title': t.title,
            'artist': t.artist,
            'album': t.album,
            'genre': t.genre,
            'duration': t.duration,
            'cover_url': t.cover_url,
            'play_count': t.play_count,
            'is_premium': t.is_premium,
            'created_at': t.created_at
        } for t in tracks.items],
        'total': tracks.total,
        'page': page,
        'pages': tracks.pages
    })

@admin_bp.route('/tracks', methods=['POST'])
@jwt_required()
@admin_required
def create_track():
    data = request.get_json()
    required_fields = ['title', 'file_key']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} required'}), 400

    track = Track(
        title=data['title'],
        artist=data.get('artist'),
        album=data.get('album'),
        genre=data.get('genre'),
        duration=data.get('duration'),
        cover_url=data.get('cover_url'),
        file_key=data['file_key'],
        lyrics=data.get('lyrics'),
        is_premium=data.get('is_premium', False),
        uploaded_by=get_jwt_identity()
    )
    db.session.add(track)
    db.session.commit()
    return jsonify({'id': track.id, 'message': 'Track created'}), 201

@admin_bp.route('/tracks/<int:track_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_track(track_id):
    track = Track.query.get_or_404(track_id)
    data = request.get_json()

    for field in ['title', 'artist', 'album', 'genre', 'duration', 'cover_url', 'file_key', 'lyrics', 'is_premium']:
        if field in data:
            setattr(track, field, data[field])

    db.session.commit()
    return jsonify({'message': 'Track updated'})

@admin_bp.route('/tracks/<int:track_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_track(track_id):
    track = Track.query.get_or_404(track_id)
    db.session.delete(track)
    db.session.commit()
    return jsonify({'message': 'Track deleted'})

@admin_bp.route('/analytics', methods=['GET'])
@jwt_required()
@admin_required
def get_analytics():
    total_users = User.query.count()
    premium_users = User.query.filter_by(subscription_tier='premium').count()
    total_tracks = Track.query.count()
    total_plays = ListeningEvent.query.count()
    total_comments = Comment.query.count()
    top_tracks = Track.query.order_by(Track.play_count.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    return jsonify({
        'total_users': total_users,
        'premium_users': premium_users,
        'free_users': total_users - premium_users,
        'total_tracks': total_tracks,
        'total_plays': total_plays,
        'total_comments': total_comments,
        'top_tracks': [{
            'id': t.id,
            'title': t.title,
            'artist': t.artist,
            'play_count': t.play_count
        } for t in top_tracks],
        'recent_users': [{
            'id': u.id,
            'username': u.username,
            'created_at': u.created_at
        } for u in recent_users]
    })

@admin_bp.route('/comments', methods=['GET'])
@jwt_required()
@admin_required
def list_comments():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    comments = Comment.query.order_by(desc(Comment.created_at))\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'comments': [{
            'id': c.id,
            'user': c.author.username,
            'track': c.track.title,
            'text': c.text,
            'created_at': c.created_at
        } for c in comments.items],
        'total': comments.total,
        'page': page,
        'pages': comments.pages
    })

@admin_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_comment_admin(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'message': 'Comment deleted'})