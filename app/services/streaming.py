import os
import boto3
from flask import current_app, request, send_file, abort
from botocore.exceptions import ClientError
import io

def stream_from_s3(file_key, range_header=None):
    """Stream audio file from S3 with support for range requests."""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY']
    )
    try:
        if range_header:
            # Parse range header (bytes=start-end)
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0]) if range_match[0] else None
            end = int(range_match[1]) if range_match[1] else None
            if end:
                length = end - start + 1
            else:
                length = None
            response = s3_client.get_object(
                Bucket=current_app.config['S3_BUCKET'],
                Key=file_key,
                Range=f'bytes={start}-{end}' if end else f'bytes={start}-'
            )
            data = response['Body'].read()
            return data, response.get('ContentRange'), response['ContentLength'], 206
        else:
            response = s3_client.get_object(
                Bucket=current_app.config['S3_BUCKET'],
                Key=file_key
            )
            data = response['Body'].read()
            return data, None, response['ContentLength'], 200
    except ClientError as e:
        current_app.logger.error(f"Error streaming from S3: {e}")
        abort(404)