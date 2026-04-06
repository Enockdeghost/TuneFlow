import os
import tempfile
import boto3
import mutagen
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4
from PIL import Image
import io
import wave
from flask import current_app
from app.extensions import celery, db
from app.models.track import Track
import logging

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO = {
    '.mp3': MP3,
    '.flac': FLAC,
    '.ogg': OggVorbis,
    '.m4a': MP4,
    '.mp4': MP4
}

def get_audio_metadata(file_path):
    """Extract metadata from audio file."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_AUDIO:
        raise ValueError(f"Unsupported audio format: {ext}")
    audio = SUPPORTED_AUDIO[ext](file_path)
    info = {
        'duration': int(audio.info.length),
        'bitrate': getattr(audio.info, 'bitrate', None),
        'sample_rate': getattr(audio.info, 'sample_rate', None)
    }
    # Try to extract tags
    if hasattr(audio, 'tags') and audio.tags:
        tags = audio.tags
        info['title'] = tags.get('TIT2', tags.get('title', [None]))[0]
        info['artist'] = tags.get('TPE1', tags.get('artist', [None]))[0]
        info['album'] = tags.get('TALB', tags.get('album', [None]))[0]
        info['genre'] = tags.get('TCON', tags.get('genre', [None]))[0]
    return info

def extract_cover_art(file_path):
    """Extract embedded cover art and return as bytes."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_AUDIO:
        return None
    audio = SUPPORTED_AUDIO[ext](file_path)
    if ext == '.mp3':
        if hasattr(audio, 'tags'):
            for tag in audio.tags.values():
                if tag.FrameID == 'APIC':
                    return tag.data
    elif ext in ('.m4a', '.mp4'):
        if hasattr(audio, 'tags') and 'covr' in audio.tags:
            return audio.tags['covr'][0]
    elif ext == '.flac':
        if hasattr(audio, 'pictures') and audio.pictures:
            return audio.pictures[0].data
    elif ext == '.ogg':
        # Ogg may have METADATA_BLOCK_PICTURE
        if hasattr(audio, 'get'):
            pic_data = audio.get('METADATA_BLOCK_PICTURE')
            if pic_data:
                return pic_data[0]
    return None

def generate_waveform_data(file_path, samples=200):
    """Generate waveform data points for visualization."""
    try:
        import wave
        import numpy as np
        import audioop
    except ImportError:
        logger.warning("numpy not installed, skipping waveform generation")
        return []

    try:
        wav = wave.open(file_path, 'rb')
    except:
        # Use pydub to convert if needed
        try:
            from pydub import AudioSegment
            sound = AudioSegment.from_file(file_path)
            # convert to mono, raw PCM
            samples_array = sound.get_array_of_samples()
            if sound.channels == 2:
                samples_array = samples_array[::2]  # mono
            chunk_size = len(samples_array) // samples
            waveform = []
            for i in range(samples):
                chunk = samples_array[i*chunk_size:(i+1)*chunk_size]
                if chunk:
                    waveform.append(abs(max(chunk, key=abs)) / 32768.0)  # normalize
                else:
                    waveform.append(0)
            return waveform
        except:
            return []

    # Handle WAV directly
    nchannels = wav.getnchannels()
    sampwidth = wav.getsampwidth()
    nframes = wav.getnframes()
    framerate = wav.getframerate()
    duration = nframes / framerate
    data = wav.readframes(nframes)
    if nchannels > 1:
        # average channels
        if sampwidth == 1:
            data = audioop.tomono(data, sampwidth, 1, 1)
        else:
            data = audioop.tomono(data, sampwidth, 0.5, 0.5)
    # Convert to numpy array
    if sampwidth == 1:
        dtype = np.uint8
    elif sampwidth == 2:
        dtype = np.int16
    else:
        dtype = np.int32
    samples_array = np.frombuffer(data, dtype=dtype)
    # Normalize
    max_val = np.iinfo(dtype).max
    samples_array = samples_array.astype(np.float32) / max_val
    chunk_size = max(1, len(samples_array) // samples)
    waveform = []
    for i in range(samples):
        chunk = samples_array[i*chunk_size:(i+1)*chunk_size]
        if len(chunk):
            waveform.append(float(np.max(np.abs(chunk))))
        else:
            waveform.append(0.0)
    wav.close()
    return waveform

@celery.task
def process_uploaded_audio(track_id, file_key, original_filename):
    """
    Process an uploaded audio file:
    - Extract metadata
    - Generate waveform data
    - Extract/upload cover art
    - Update track record
    """
    s3 = boto3.client(
        's3',
        aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY']
    )
    bucket = current_app.config['S3_BUCKET']
    temp_dir = tempfile.mkdtemp()
    local_path = os.path.join(temp_dir, os.path.basename(file_key))

    try:
        # Download from S3
        s3.download_file(bucket, file_key, local_path)
        logger.info(f"Downloaded {file_key} to {local_path}")

        # Extract metadata
        metadata = get_audio_metadata(local_path)
        duration = metadata.get('duration')
        bitrate = metadata.get('bitrate')
        sample_rate = metadata.get('sample_rate')

        # Extract cover art
        cover_data = extract_cover_art(local_path)
        cover_url = None
        if cover_data:
            # Upload cover to S3 with a derived key
            cover_key = f"covers/{track_id}_{os.path.basename(file_key)}.jpg"
            # Convert to jpeg if needed
            try:
                img = Image.open(io.BytesIO(cover_data))
                img.thumbnail((300, 300))
                jpeg_buffer = io.BytesIO()
                img.save(jpeg_buffer, format='JPEG')
                cover_data = jpeg_buffer.getvalue()
                s3.put_object(Bucket=bucket, Key=cover_key, Body=cover_data, ContentType='image/jpeg')
                cover_url = f"{current_app.config.get('CDN_DOMAIN', '')}/{cover_key}"
            except:
                # Fallback: upload raw
                s3.put_object(Bucket=bucket, Key=cover_key, Body=cover_data)
                cover_url = f"{current_app.config.get('CDN_DOMAIN', '')}/{cover_key}"

        # Generate waveform
        waveform = generate_waveform_data(local_path, 200)
        # Store waveform as JSON in track model or separate model
        # For simplicity, store as JSON in track.waveform (add column)
        # We'll assume track has a waveform_data column (JSON)

        # Update track record
        track = Track.query.get(track_id)
        if track:
            track.duration = duration
            if metadata.get('title'):
                track.title = metadata['title']
            if metadata.get('artist'):
                track.artist = metadata['artist']
            if metadata.get('album'):
                track.album = metadata['album']
            if metadata.get('genre'):
                track.genre = metadata['genre']
            if cover_url:
                track.cover_url = cover_url
            # track.waveform_data = waveform  # if you added column
            db.session.commit()

        logger.info(f"Processed track {track_id}")

    except Exception as e:
        logger.exception(f"Error processing track {track_id}: {e}")
    finally:
        # Clean up temp files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

@celery.task
def generate_track_preview(track_id, start_sec=30, duration=30):
    """Generate a preview clip (e.g., 30 seconds) for the track."""
    # Placeholder: implement using pydub or ffmpeg
    pass