from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User
from app.models.track import Track
from app.models.follow import Follow
from app.models.comment import Comment

social_bp = Blueprint('social', __name__)

@social_bp.route('/follow/<int:user_id>', methods=['POST'])
@jwt_required()
def follow_user(user_id):
    follower_id = int(get_jwt_identity())
    if follower_id == user_id:
        return jsonify({'error': 'Cannot follow yourself'}), 400

    follow = Follow.query.filter_by(follower_id=follower_id, followed_id=user_id).first()
    if follow:
        return jsonify({'message': 'Already following'}), 200

    follow = Follow(follower_id=follower_id, followed_id=user_id)
    db.session.add(follow)
    db.session.commit()
    return jsonify({'message': 'Followed'}), 201

@social_bp.route('/unfollow/<int:user_id>', methods=['POST'])
@jwt_required()
def unfollow_user(user_id):
    follower_id = int(get_jwt_identity())
    follow = Follow.query.filter_by(follower_id=follower_id, followed_id=user_id).first()
    if not follow:
        return jsonify({'error': 'Not following'}), 400

    db.session.delete(follow)
    db.session.commit()
    return jsonify({'message': 'Unfollowed'}), 200

@social_bp.route('/followers/<int:user_id>', methods=['GET'])
def get_followers(user_id):
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    followers = Follow.query.filter_by(followed_id=user_id)\
        .order_by(Follow.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'users': [{
            'id': f.follower.id,
            'username': f.follower.username,
            'followed_at': f.created_at
        } for f in followers.items],
        'total': followers.total,
        'page': page,
        'pages': followers.pages
    })

@social_bp.route('/following/<int:user_id>', methods=['GET'])
def get_following(user_id):
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    following = Follow.query.filter_by(follower_id=user_id)\
        .order_by(Follow.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'users': [{
            'id': f.followed.id,
            'username': f.followed.username,
            'followed_at': f.created_at
        } for f in following.items],
        'total': following.total,
        'page': page,
        'pages': following.pages
    })

@social_bp.route('/track/<int:track_id>/comments', methods=['GET'])
def get_comments(track_id):
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    comments = Comment.query.filter_by(track_id=track_id)\
        .order_by(Comment.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'comments': [{
            'id': c.id,
            'user': c.author.username,
            'user_id': c.user_id,
            'text': c.text,
            'created_at': c.created_at
        } for c in comments.items],
        'total': comments.total,
        'page': page,
        'pages': comments.pages
    })

@social_bp.route('/track/<int:track_id>/comments', methods=['POST'])
@jwt_required()
def add_comment(track_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    text = data.get('text')

    if not text:
        return jsonify({'error': 'Comment text required'}), 400

    comment = Comment(user_id=user_id, track_id=track_id, text=text)
    db.session.add(comment)
    db.session.commit()

    return jsonify({
        'id': comment.id,
        'user': comment.author.username,
        'text': comment.text,
        'created_at': comment.created_at,
        'message': 'Comment added'
    }), 201

@social_bp.route('/comment/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    user_id = int(get_jwt_identity())
    comment = Comment.query.get_or_404(comment_id)

    if comment.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(comment)
    db.session.commit()
    return jsonify({'message': 'Comment deleted'}), 200