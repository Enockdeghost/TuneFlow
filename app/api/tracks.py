from flask import Blueprint, request, jsonify, current_app, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, desc, or_
from datetime import datetime, timedelta
import os
import boto3
from app.extensions import db
from app.models.track import Track
from app.models.user import User
from app.models.favorite import Favorite
from app.models.listening_event import ListeningEvent
from app.tasks.analytics import increment_play_count

tracks_bp = Blueprint('tracks', __name__)

@tracks_bp.route('/', methods=['GET'])
def list_tracks():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    q = request.args.get('q', '')
    genre = request.args.get('genre')
    artist = request.args.get('artist')
    sort = request.args.get('sort', 'popular')

    query = Track.query
    if q:
        query = query.filter(or_(
            Track.title.ilike(f'%{q}%'),
            Track.artist.ilike(f'%{q}%'),
            Track.album.ilike(f'%{q}%')
        ))
    if genre:
        query = query.filter(Track.genre == genre)
    if artist:
        query = query.filter(Track.artist.ilike(f'%{artist}%'))

    if sort == 'popular':
        query = query.order_by(Track.play_count.desc())
    elif sort == 'recent':
        query = query.order_by(Track.created_at.desc())
    elif sort == 'title':
        query = query.order_by(Track.title)

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    tracks = [{
        'id': t.id,
        'title': t.title,
        'artist': t.artist,
        'album': t.album,
        'genre': t.genre,
        'duration': t.duration,
        'cover_url': t.cover_url,
        'is_premium': t.is_premium,
        'play_count': t.play_count
    } for t in paginated.items]

    return jsonify({
        'tracks': tracks,
        'total': paginated.total,
        'page': page,
        'pages': paginated.pages
    })

@tracks_bp.route('/<int:track_id>', methods=['GET'])
def get_track(track_id):
    track = Track.query.get_or_404(track_id)
    return jsonify({
        'id': track.id,
        'title': track.title,
        'artist': track.artist,
        'album': track.album,
        'genre': track.genre,
        'duration': track.duration,
        'cover_url': track.cover_url,
        'lyrics': track.lyrics,
        'is_premium': track.is_premium,
        'play_count': track.play_count
    })

@tracks_bp.route('/<int:track_id>/stream', methods=['GET'])
def stream_track(track_id):
    track = Track.query.get_or_404(track_id)

    # Optional premium check – you can re‑enable later with JWT
    # user_id = get_jwt_identity()
    # user = User.query.get(int(user_id)) if user_id else None
    # if track.is_premium and (not user or user.subscription_tier != 'premium'):
    #     return jsonify({'error': 'Premium track, upgrade to listen'}), 403

    # Local file serving
    local_upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
    local_file_path = os.path.join(local_upload_folder, track.file_key)
    if os.path.exists(local_file_path):
        file_url = url_for('static', filename=f'uploads/{track.file_key}', _external=True)
        return jsonify({'stream_url': file_url})

    # AWS S3 fallback
    aws_key = current_app.config.get('AWS_ACCESS_KEY_ID')
    aws_secret = current_app.config.get('AWS_SECRET_ACCESS_KEY')
    s3_bucket = current_app.config.get('S3_BUCKET')
    if aws_key and aws_secret and s3_bucket:
        s3 = boto3.client('s3', aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
        url = s3.generate_presigned_url('get_object',
            Params={'Bucket': s3_bucket, 'Key': track.file_key},
            ExpiresIn=3600
        )
        return jsonify({'stream_url': url})
    else:
        return jsonify({'error': 'Audio file not found'}), 404

@tracks_bp.route('/<int:track_id>/play', methods=['POST'])
@jwt_required()
def record_play(track_id):
    user_id = get_jwt_identity()
    track = Track.query.get_or_404(track_id)
    increment_play_count.delay(track_id, int(user_id))
    return jsonify({'message': 'Play recorded'}), 202

@tracks_bp.route('/<int:track_id>/like', methods=['POST'])
@jwt_required()
def like_track(track_id):
    user_id = int(get_jwt_identity())
    existing = Favorite.query.filter_by(user_id=user_id, track_id=track_id).first()
    if existing:
        return jsonify({'message': 'Already liked'}), 200
    fav = Favorite(user_id=user_id, track_id=track_id)
    db.session.add(fav)
    db.session.commit()
    return jsonify({'message': 'Liked'}), 201

@tracks_bp.route('/<int:track_id>/like', methods=['DELETE'])
@jwt_required()
def unlike_track(track_id):
    user_id = int(get_jwt_identity())
    fav = Favorite.query.filter_by(user_id=user_id, track_id=track_id).first()
    if not fav:
        return jsonify({'error': 'Not liked'}), 404
    db.session.delete(fav)
    db.session.commit()
    return jsonify({'message': 'Unliked'}), 200

@tracks_bp.route('/<int:track_id>/like-status', methods=['GET'])
@jwt_required()
def like_status(track_id):
    user_id = int(get_jwt_identity())
    liked = Favorite.query.filter_by(user_id=user_id, track_id=track_id).first() is not None
    return jsonify({'liked': liked})

@tracks_bp.route('/favorites', methods=['GET'])
@jwt_required()
def get_favorites():
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    favorites = Favorite.query.filter_by(user_id=user_id)\
        .join(Track)\
        .order_by(Favorite.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    tracks = [{
        'id': fav.track.id,
        'title': fav.track.title,
        'artist': fav.track.artist,
        'duration': fav.track.duration,
        'cover_url': fav.track.cover_url,
        'is_premium': fav.track.is_premium
    } for fav in favorites.items]

    return jsonify({
        'tracks': tracks,
        'total': favorites.total,
        'page': page,
        'pages': favorites.pages
    })

@tracks_bp.route('/trending', methods=['GET'])
def get_trending():
    days = request.args.get('days', default=7, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    trending = db.session.query(
        Track, func.count(ListeningEvent.id).label('plays')
    ).join(ListeningEvent, ListeningEvent.track_id == Track.id)\
     .filter(ListeningEvent.created_at >= since)\
     .group_by(Track.id)\
     .order_by(desc('plays'))\
     .limit(50).all()

    result = [{
        'id': t.id,
        'title': t.title,
        'artist': t.artist,
        'cover_url': t.cover_url,
        'duration': t.duration,
        'plays': plays
    } for t, plays in trending]
    return jsonify(result)