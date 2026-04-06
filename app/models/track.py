from app.extensions import db

class Track(db.Model):
    __tablename__ = 'tracks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(100))
    album = db.Column(db.String(100))
    genre = db.Column(db.String(50))
    duration = db.Column(db.Integer)
    cover_url = db.Column(db.String(500))
    file_key = db.Column(db.String(500))
    lyrics = db.Column(db.Text)
    play_count = db.Column(db.Integer, default=0)
    is_premium = db.Column(db.Boolean, default=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationships
    favorites = db.relationship('Favorite', backref='track', lazy='dynamic')
    comments = db.relationship('Comment', backref='track', lazy='dynamic')
    listening_events = db.relationship('ListeningEvent', backref='track', lazy='dynamic')
    playlists = db.relationship('Playlist', secondary='playlist_track', back_populates='tracks', lazy='dynamic')

    def __repr__(self):
        return f'<Track {self.title}>'