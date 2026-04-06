from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.playlist import Playlist
from app.models.track import Track

playlists_bp = Blueprint('playlists', __name__)

@playlists_bp.route('/', methods=['GET'])
@jwt_required()
def list_playlists():
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    playlists = Playlist.query.filter_by(user_id=user_id)\
        .order_by(Playlist.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'playlists': [{
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'is_public': p.is_public,
            'track_count': p.tracks.count()
        } for p in playlists.items],
        'total': playlists.total,
        'page': page,
        'pages': playlists.pages
    })

@playlists_bp.route('/public', methods=['GET'])
def list_public_playlists():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    playlists = Playlist.query.filter_by(is_public=True)\
        .order_by(Playlist.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'playlists': [{
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'owner': p.owner.username,
            'track_count': p.tracks.count()
        } for p in playlists.items],
        'total': playlists.total,
        'page': page,
        'pages': playlists.pages
    })

@playlists_bp.route('/', methods=['POST'])
@jwt_required()
def create_playlist():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    is_public = data.get('is_public', False)

    if not name:
        return jsonify({'error': 'Playlist name required'}), 400

    playlist = Playlist(
        name=name,
        description=description,
        is_public=is_public,
        user_id=user_id
    )
    db.session.add(playlist)
    db.session.commit()

    return jsonify({'id': playlist.id, 'message': 'Playlist created'}), 201

@playlists_bp.route('/<int:playlist_id>', methods=['GET'])
def get_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    user_id = get_jwt_identity()
    if not playlist.is_public and (not user_id or playlist.user_id != int(user_id)):
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'id': playlist.id,
        'name': playlist.name,
        'description': playlist.description,
        'is_public': playlist.is_public,
        'owner': playlist.owner.username,
        'created_at': playlist.created_at,
        'tracks': [{
            'id': t.id,
            'title': t.title,
            'artist': t.artist,
            'duration': t.duration,
            'cover_url': t.cover_url,
            'is_premium': t.is_premium
        } for t in playlist.tracks]
    })

@playlists_bp.route('/<int:playlist_id>', methods=['PUT'])
@jwt_required()
def update_playlist(playlist_id):
    user_id = int(get_jwt_identity())
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    playlist.name = data.get('name', playlist.name)
    playlist.description = data.get('description', playlist.description)
    playlist.is_public = data.get('is_public', playlist.is_public)
    db.session.commit()

    return jsonify({'message': 'Playlist updated'})

@playlists_bp.route('/<int:playlist_id>', methods=['DELETE'])
@jwt_required()
def delete_playlist(playlist_id):
    user_id = int(get_jwt_identity())
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(playlist)
    db.session.commit()
    return jsonify({'message': 'Playlist deleted'})

@playlists_bp.route('/<int:playlist_id>/tracks', methods=['POST'])
@jwt_required()
def add_track_to_playlist(playlist_id):
    user_id = int(get_jwt_identity())
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    track_id = data.get('track_id')
    track = Track.query.get_or_404(track_id)

    if track in playlist.tracks:
        return jsonify({'message': 'Track already in playlist'}), 200

    playlist.tracks.append(track)
    db.session.commit()
    return jsonify({'message': 'Track added'}), 201

@playlists_bp.route('/<int:playlist_id>/tracks/<int:track_id>', methods=['DELETE'])
@jwt_required()
def remove_track_from_playlist(playlist_id, track_id):
    user_id = int(get_jwt_identity())
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    track = Track.query.get_or_404(track_id)
    if track not in playlist.tracks:
        return jsonify({'error': 'Track not in playlist'}), 404

    playlist.tracks.remove(track)
    db.session.commit()
    return jsonify({'message': 'Track removed'})