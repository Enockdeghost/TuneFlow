from flask import Blueprint, jsonify
from app.extensions import db
from app.models.track import Track
from sqlalchemy import func

genres_bp = Blueprint('genres', __name__)

@genres_bp.route('/', methods=['GET'])
def list_genres():
    genres_data = db.session.query(
        Track.genre,
        func.count(Track.id).label('track_count')
    ).filter(Track.genre.isnot(None)).group_by(Track.genre).order_by(func.count(Track.id).desc()).all()
    genres = [{'name': g[0], 'track_count': g[1]} for g in genres_data]
    return jsonify(genres)

@genres_bp.route('/<genre_name>/tracks', methods=['GET'])
def genre_tracks(genre_name):
    tracks = Track.query.filter_by(genre=genre_name).order_by(Track.play_count.desc()).all()
    result = [{
        'id': t.id,
        'title': t.title,
        'artist': t.artist,
        'duration': t.duration,
        'cover_url': t.cover_url,
        'play_count': t.play_count
    } for t in tracks]
    return jsonify(result)