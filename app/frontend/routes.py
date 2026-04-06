from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, unset_jwt_cookies, create_access_token, set_access_cookies
from app.extensions import db
from app.models.user import User
from app.models.track import Track
from app.models.playlist import Playlist
from app.models.favorite import Favorite
from app.models.listening_event import ListeningEvent
from app.models.comment import Comment
from app.models.follow import Follow
from sqlalchemy import func, desc
import datetime
import os
from werkzeug.utils import secure_filename
import uuid

from . import frontend

def get_current_user():
    try:
        user_id = get_jwt_identity()
        if user_id:
            return User.query.get(int(user_id))
    except:
        pass
    return None

UPLOAD_FOLDER = 'app/static/uploads'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'ogg', 'm4a'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@frontend.route('/')
def index():
    user = get_current_user()
    trending = Track.query.order_by(Track.play_count.desc()).limit(10).all()
    recent = Track.query.order_by(Track.created_at.desc()).limit(10).all()

    # Jump Back In – recently played by the user
    recent_played = []
    if user:
        recent_played = db.session.query(Track).join(ListeningEvent, ListeningEvent.track_id == Track.id)\
            .filter(ListeningEvent.user_id == user.id)\
            .order_by(desc(ListeningEvent.created_at))\
            .limit(10).all()

    made_for_you = []
    if user:
        top_genres = db.session.query(
            Track.genre, func.count(ListeningEvent.id).label('cnt')
        ).join(ListeningEvent, ListeningEvent.track_id == Track.id)\
         .filter(ListeningEvent.user_id == user.id, Track.genre.isnot(None))\
         .group_by(Track.genre)\
         .order_by(desc('cnt'))\
         .limit(3).all()
        if top_genres:
            genre_list = [g[0] for g in top_genres]
            listened_ids = db.session.query(ListeningEvent.track_id).filter_by(user_id=user.id).subquery()
            made_for_you = Track.query.filter(
                Track.genre.in_(genre_list),
                Track.id.notin_(listened_ids)
            ).order_by(Track.play_count.desc()).limit(10).all()
        if not made_for_you:
            made_for_you = trending[:10]
    else:
        made_for_you = trending[:10]

    # Popular public playlists
    popular_playlists = Playlist.query.filter_by(is_public=True).order_by(Playlist.created_at.desc()).limit(10).all()

    return render_template('index.html',
                         trending=trending,
                         recent=recent,
                         recent_played=recent_played,
                         made_for_you=made_for_you,
                         popular_playlists=popular_playlists)


@frontend.route('/library')
@jwt_required()
def library():
    user = get_current_user()
    favorites = Favorite.query.filter_by(user_id=user.id).join(Track).order_by(Favorite.created_at.desc()).limit(50).all()
    favorite_tracks = [fav.track for fav in favorites]
    playlists = Playlist.query.filter_by(user_id=user.id).all()
    user_tracks = Track.query.filter_by(uploaded_by=user.id).order_by(Track.created_at.desc()).all()
    return render_template('library.html', favorites=favorite_tracks, playlists=playlists, user_tracks=user_tracks)

@frontend.route('/playlists')
@jwt_required()
def playlists():
    user = get_current_user()
    playlists = Playlist.query.filter_by(user_id=user.id).order_by(Playlist.created_at.desc()).all()
    return render_template('playlists.html', playlists=playlists)

@frontend.route('/playlist/<int:playlist_id>')
def playlist_detail(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    user = get_current_user()
    if not playlist.is_public and (not user or playlist.user_id != user.id):
        flash('This playlist is private.', 'danger')
        return redirect(url_for('frontend.index'))
    return render_template('playlist_detail.html', playlist=playlist)

@frontend.route('/create-playlist', methods=['GET', 'POST'])
@jwt_required()
def create_playlist():
    user = get_current_user()
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_public = 'is_public' in request.form
        if not name:
            flash('Playlist name required', 'danger')
        else:
            playlist = Playlist(name=name, description=description, is_public=is_public, user_id=user.id)
            db.session.add(playlist)
            db.session.commit()
            flash('Playlist created', 'success')
            return redirect(url_for('frontend.playlist_detail', playlist_id=playlist.id))
    return render_template('create_playlist.html')

@frontend.route('/edit-playlist/<int:playlist_id>', methods=['GET', 'POST'])
@jwt_required()
def edit_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    user = get_current_user()
    if playlist.user_id != user.id:
        flash('You are not the owner of this playlist.', 'danger')
        return redirect(url_for('frontend.playlist_detail', playlist_id=playlist.id))
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_public = 'is_public' in request.form
        if not name:
            flash('Playlist name required', 'danger')
        else:
            playlist.name = name
            playlist.description = description
            playlist.is_public = is_public
            db.session.commit()
            flash('Playlist updated', 'success')
            return redirect(url_for('frontend.playlist_detail', playlist_id=playlist.id))
    return render_template('edit_playlist.html', playlist=playlist)

@frontend.route('/search')
def search():
    q = request.args.get('q', '')
    tracks = []
    if q:
        tracks = Track.query.filter(
            Track.title.ilike(f'%{q}%') |
            Track.artist.ilike(f'%{q}%') |
            Track.album.ilike(f'%{q}%')
        ).limit(50).all()
    return render_template('search.html', q=q, tracks=tracks)

@frontend.route('/track/<int:track_id>')
def track_detail(track_id):
    track = Track.query.get_or_404(track_id)
    related = Track.query.filter(Track.genre == track.genre, Track.id != track.id).limit(5).all()
    return render_template('track_detail.html', track=track, related=related)

@frontend.route('/profile')
@jwt_required()
def profile():
    profile_user = get_current_user()
    # Listening stats
    total_seconds = db.session.query(db.func.sum(ListeningEvent.listened_seconds)).filter_by(user_id=profile_user.id).scalar() or 0
    favorites_count = Favorite.query.filter_by(user_id=profile_user.id).count()
    playlists_count = Playlist.query.filter_by(user_id=profile_user.id).count()
    comments_count = Comment.query.filter_by(user_id=profile_user.id).count()
    following_count = Follow.query.filter_by(follower_id=profile_user.id).count()
    followers_count = Follow.query.filter_by(followed_id=profile_user.id).count()

    # Top Artists
    top_artists = db.session.query(
        Track.artist,
        func.count(ListeningEvent.id).label('play_count')
    ).join(ListeningEvent, ListeningEvent.track_id == Track.id)\
     .filter(ListeningEvent.user_id == profile_user.id, Track.artist.isnot(None))\
     .group_by(Track.artist)\
     .order_by(func.count(ListeningEvent.id).desc())\
     .limit(6).all()
    top_artists = [{'name': a[0], 'plays': a[1]} for a in top_artists]

    # Top Genres
    top_genres = db.session.query(
        Track.genre,
        func.count(ListeningEvent.id).label('play_count')
    ).join(ListeningEvent, ListeningEvent.track_id == Track.id)\
     .filter(ListeningEvent.user_id == profile_user.id, Track.genre.isnot(None))\
     .group_by(Track.genre)\
     .order_by(func.count(ListeningEvent.id).desc())\
     .limit(6).all()
    top_genres = [{'genre': g[0], 'plays': g[1]} for g in top_genres]

    user_tracks = Track.query.filter_by(uploaded_by=profile_user.id).order_by(Track.created_at.desc()).limit(10).all()

    listening_stats = {
        'total_seconds': total_seconds,
        'favorites': favorites_count,
        'playlists': playlists_count,
        'comments': comments_count,
        'following': following_count,
        'followers': followers_count,
        'top_artists': top_artists,
        'top_genres': top_genres
    }
    return render_template('profile.html', profile_user=profile_user, stats=listening_stats, user_tracks=user_tracks)

@frontend.route('/favorites')
@jwt_required()
def favorites():
    user = get_current_user()
    favorites = Favorite.query.filter_by(user_id=user.id).join(Track).order_by(Favorite.created_at.desc()).all()
    tracks = [fav.track for fav in favorites]
    return render_template('favorites.html', tracks=tracks)

@frontend.route('/history')
@jwt_required()
def history():
    user = get_current_user()
    events = ListeningEvent.query.filter_by(user_id=user.id).order_by(ListeningEvent.created_at.desc()).limit(50).all()
    tracks = [event.track for event in events]
    return render_template('history.html', tracks=tracks)

@frontend.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            access_token = create_access_token(identity=str(user.id))
            response = redirect(url_for('frontend.index'))
            set_access_cookies(response, access_token)
            return response
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@frontend.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        if not email or not username or not password:
            flash('All fields required', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username taken', 'danger')
        else:
            user = User(email=email, username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            access_token = create_access_token(identity=str(user.id))
            response = redirect(url_for('frontend.index'))
            set_access_cookies(response, access_token)
            return response
    return render_template('register.html')

@frontend.route('/settings')
@jwt_required()
def settings():
    return render_template('settings.html')

@frontend.route('/api/user/change-password', methods=['POST'])
@jwt_required()
def change_password():
    user = get_current_user()
    data = request.get_json()
    current = data.get('current_password')
    new = data.get('new_password')
    if not user.check_password(current):
        return jsonify({'error': 'Current password is incorrect'}), 401
    if len(new) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    user.set_password(new)
    db.session.commit()
    return jsonify({'message': 'Password updated'}), 200

@frontend.route('/api/user/delete-uploads', methods=['DELETE'])
@jwt_required()
def delete_uploads():
    user = get_current_user()
    tracks = Track.query.filter_by(uploaded_by=user.id).all()
    for track in tracks:
        # Delete physical file
        file_path = os.path.join('app/static/uploads', track.file_key)
        if os.path.exists(file_path):
            os.remove(file_path)
        # Delete related records
        Favorite.query.filter_by(track_id=track.id).delete()
        Comment.query.filter_by(track_id=track.id).delete()
        ListeningEvent.query.filter_by(track_id=track.id).delete()
        db.session.delete(track)
    db.session.commit()
    return jsonify({'message': 'All uploaded tracks deleted'}), 200

@frontend.route('/api/user/delete-account', methods=['DELETE'])
@jwt_required()
def delete_account():
    user = get_current_user()
    # First delete all user's uploaded tracks files (optional)
    from app.models.track import Track
    import os
    tracks = Track.query.filter_by(uploaded_by=user.id).all()
    for track in tracks:
        file_path = os.path.join('app/static/uploads', track.file_key)
        if os.path.exists(file_path):
            os.remove(file_path)
    # Then delete the user (cascade will handle playlists, favorites, etc.)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Account deleted'}), 200

@frontend.route('/logout')
def logout():
    response = redirect(url_for('frontend.index'))
    unset_jwt_cookies(response)
    return response

@frontend.route('/api/user/delete-track/<int:track_id>', methods=['DELETE'])
@jwt_required()
def delete_single_track(track_id):
    user = get_current_user()
    track = Track.query.get_or_404(track_id)
    if track.uploaded_by != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    file_path = os.path.join('app/static/uploads', track.file_key)
    if os.path.exists(file_path):
        os.remove(file_path)

    Favorite.query.filter_by(track_id=track.id).delete()
    Comment.query.filter_by(track_id=track.id).delete()
    ListeningEvent.query.filter_by(track_id=track.id).delete()

    # Finally delete the track
    db.session.delete(track)
    db.session.commit()

    return jsonify({'message': 'Track deleted successfully'}), 200



@frontend.route('/upload', methods=['GET', 'POST'])
@jwt_required()
def upload_track():
    user = get_current_user()
    if request.method == 'POST':
        if 'audio_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['audio_file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(file_path)

            title = request.form.get('title', '').strip()
            artist = request.form.get('artist', '').strip()
            album = request.form.get('album', '').strip()
            genre = request.form.get('genre', '').strip()
            duration = 0

            cover_url = None
            if 'cover_image' in request.files:
                cover_file = request.files['cover_image']
                if cover_file and cover_file.filename:
                    cover_filename = secure_filename(cover_file.filename)
                    cover_unique = f"{uuid.uuid4().hex}_{cover_filename}"
                    cover_path = os.path.join(UPLOAD_FOLDER, cover_unique)
                    cover_file.save(cover_path)
                    cover_url = url_for('static', filename=f'uploads/{cover_unique}')

            track = Track(
                title=title or os.path.splitext(filename)[0],
                artist=artist,
                album=album,
                genre=genre,
                duration=duration,
                cover_url=cover_url,
                file_key=unique_filename,
                is_premium=False,
                uploaded_by=user.id
            )
            db.session.add(track)
            db.session.commit()
            flash('Track uploaded successfully!', 'success')
            return redirect(url_for('frontend.track_detail', track_id=track.id))
        else:
            flash('Invalid file type. Allowed: mp3, wav, flac, ogg, m4a', 'danger')
            return redirect(request.url)
    return render_template('upload_track.html')

@frontend.route('/community')
def community():
    tracks = Track.query.filter(Track.uploaded_by.isnot(None)).order_by(desc(Track.created_at)).all()
    return render_template('community.html', tracks=tracks)

@frontend.route('/trending')
def trending():
    tracks = Track.query.order_by(Track.play_count.desc()).limit(50).all()
    return render_template('trending.html', tracks=tracks)

@frontend.route('/artists')
def artists():
    artists_data = db.session.query(
        Track.artist,
        func.count(Track.id).label('track_count'),
        func.sum(Track.play_count).label('total_plays'),
        func.max(Track.cover_url).label('cover_url')
    ).filter(Track.artist.isnot(None)).group_by(Track.artist).order_by(func.sum(Track.play_count).desc()).limit(50).all()
    artists = [{'name': a[0], 'track_count': a[1], 'total_plays': a[2], 'cover_url': a[3] or url_for('static', filename='img/default-artist.png')} for a in artists_data]
    return render_template('artists.html', artists=artists)

@frontend.route('/artist/<artist_name>')
def artist_detail(artist_name):
    tracks = Track.query.filter_by(artist=artist_name).order_by(Track.play_count.desc()).all()
    return render_template('artist_detail.html', artist=artist_name, tracks=tracks)

@frontend.route('/genres')
def genres():
    genres_data = db.session.query(
        Track.genre,
        func.count(Track.id).label('track_count')
    ).filter(Track.genre.isnot(None)).group_by(Track.genre).order_by(func.count(Track.id).desc()).all()
    genres = [{'name': g[0], 'track_count': g[1]} for g in genres_data]
    return render_template('genres.html', genres=genres)

@frontend.route('/genre/<genre_name>')
def genre_detail(genre_name):
    tracks = Track.query.filter_by(genre=genre_name).order_by(Track.play_count.desc()).all()
    return render_template('genre_detail.html', genre=genre_name, tracks=tracks)