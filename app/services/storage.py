import boto3
from botocore.exceptions import ClientError
from flask import current_app

def generate_presigned_url(key, expiration=3600, disposition=None):
    """Generate a presigned URL for S3 object."""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY']
    )
    params = {'Bucket': current_app.config['S3_BUCKET'], 'Key': key}
    if disposition:
        params['ResponseContentDisposition'] = disposition

    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        current_app.logger.error(f"Error generating presigned URL: {e}")
        return None

def upload_file(file_obj, key):
    """Upload a file to S3."""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY']
    )
    try:
        s3_client.upload_fileobj(file_obj, current_app.config['S3_BUCKET'], key)
        return True
    except ClientError as e:
        current_app.logger.error(f"Error uploading file: {e}")
        return False

def delete_file(key):
    """Delete a file from S3."""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY']
    )
    try:
        s3_client.delete_object(Bucket=current_app.config['S3_BUCKET'], Key=key)
        return True
    except ClientError as e:
        current_app.logger.error(f"Error deleting file: {e}")
        return False