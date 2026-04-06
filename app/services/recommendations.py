from sqlalchemy import func, and_
from app.extensions import db
from app.models.track import Track
from app.models.listening_event import ListeningEvent
from app.models.favorite import Favorite
from app.models.user import User
import random

def get_trending_tracks(limit=20):
    """Get trending tracks based on play count in last 7 days."""
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    trending = db.session.query(
        Track,
        func.count(ListeningEvent.id).label('plays')
    ).join(ListeningEvent, ListeningEvent.track_id == Track.id)\
     .filter(ListeningEvent.created_at >= week_ago)\
     .group_by(Track.id)\
     .order_by(func.count(ListeningEvent.id).desc())\
     .limit(limit).all()
    return [t[0] for t in trending]

def get_recommendations_for_user(user_id, limit=20):
    """Simple collaborative filtering based on genre preferences."""
    # Find top genres from user's listening history
    top_genres = db.session.query(
        Track.genre,
        func.count(ListeningEvent.id).label('count')
    ).join(ListeningEvent, ListeningEvent.track_id == Track.id)\
     .filter(ListeningEvent.user_id == user_id)\
     .filter(Track.genre.isnot(None))\
     .group_by(Track.genre)\
     .order_by(func.count(ListeningEvent.id).desc())\
     .limit(3).all()

    if not top_genres:
        # Fallback to popular tracks
        return get_trending_tracks(limit)

    genre_list = [g[0] for g in top_genres if g[0]]
    # Get tracks from those genres, excluding already listened tracks
    listened_track_ids = db.session.query(ListeningEvent.track_id)\
        .filter_by(user_id=user_id).subquery()
    recommendations = Track.query.filter(
        Track.genre.in_(genre_list),
        Track.id.notin_(listened_track_ids)
    ).order_by(Track.play_count.desc()).limit(limit).all()

    if len(recommendations) < limit:
        # Fill with trending if not enough
        trending = get_trending_tracks(limit)
        for t in trending:
            if t not in recommendations:
                recommendations.append(t)
            if len(recommendations) >= limit:
                break
    return recommendations

def get_similar_tracks(track_id, limit=10):
    """Content-based: find tracks with same genre/artist."""
    track = Track.query.get(track_id)
    if not track:
        return []
    query = Track.query.filter(Track.id != track_id)
    if track.genre:
        query = query.filter(Track.genre == track.genre)
    if track.artist:
        query = query.filter(Track.artist == track.artist)
    return query.order_by(Track.play_count.desc()).limit(limit).all()