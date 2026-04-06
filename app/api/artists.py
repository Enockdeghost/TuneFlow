from flask import Blueprint, jsonify
from app.extensions import db
from app.models.track import Track
from sqlalchemy import func

artists_bp = Blueprint('artists', __name__)

@artists_bp.route('/', methods=['GET'])
def list_artists():
    artists_data = db.session.query(
        Track.artist,
        func.count(Track.id).label('track_count'),
        func.sum(Track.play_count).label('total_plays'),
        func.max(Track.cover_url).label('cover_url')
    ).filter(Track.artist.isnot(None)).group_by(Track.artist).order_by(func.sum(Track.play_count).desc()).limit(50).all()
    artists = [{
        'name': a[0],
        'track_count': a[1],
        'total_plays': a[2],
        'cover_url': a[3] or '/static/img/default-artist.png'
    } for a in artists_data]
    return jsonify(artists)

@artists_bp.route('/<artist_name>/tracks', methods=['GET'])
def artist_tracks(artist_name):
    tracks = Track.query.filter_by(artist=artist_name).order_by(Track.play_count.desc()).all()
    result = [{
        'id': t.id,
        'title': t.title,
        'duration': t.duration,
        'cover_url': t.cover_url,
        'play_count': t.play_count
    } for t in tracks]
    return jsonify(result)