from app.extensions import db, celery
from app.models.track import Track
from app.models.listening_event import ListeningEvent
from datetime import datetime, timedelta
from sqlalchemy import func

@celery.task
def increment_play_count(track_id, user_id, listened_seconds=None, completed=False):
    """Increment track play count and record listening event."""
    track = Track.query.get(track_id)
    if track:
        track.play_count += 1
        db.session.commit()

    event = ListeningEvent(
        user_id=user_id,
        track_id=track_id,
        listened_seconds=listened_seconds or 0,
        completed=completed
    )
    db.session.add(event)
    db.session.commit()

@celery.task
def update_trending_scores():
    """Calculate and store trending scores (e.g., in Redis)."""
    from app.extensions import celery
    from redis import Redis
    import os

    redis_client = Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
    week_ago = datetime.utcnow() - timedelta(days=7)

    # Get play counts per track in last 7 days
    results = db.session.query(
        ListeningEvent.track_id,
        func.count(ListeningEvent.id).label('play_count')
    ).filter(ListeningEvent.created_at >= week_ago)\
     .group_by(ListeningEvent.track_id)\
     .all()

    for track_id, count in results:
        redis_client.zadd('trending_tracks', {track_id: count})

    # Keep only top 500
    redis_client.zremrangebyrank('trending_tracks', 0, -501)

@celery.task
def update_recommendations(user_id):
    """Compute personalized recommendations for a user (simple collaborative filtering)."""
    # Placeholder – you can implement using user listening history kazi alot i need help
    pass