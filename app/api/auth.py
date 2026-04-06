from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from app.extensions import db, limiter
from app.models.user import User
from app.utils.validators import validate_email, validate_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per hour")
def register():
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')

    if not email or not username or not password:
        return jsonify({'error': 'Missing fields'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Invalid email'}), 400
    if not validate_password(password):
        return jsonify({'error': 'Password must be at least 8 characters with letters and numbers'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username taken'}), 409

    user = User(email=email, username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    response = make_response(jsonify({'message': 'Login successful'}))
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    response = make_response(jsonify({'message': 'Token refreshed'}))
    set_access_cookies(response, new_access_token)
    return response

@auth_bp.route('/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'message': 'Logged out'}))
    unset_jwt_cookies(response)
    return response

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(int(user_id))
    return jsonify({
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'subscription_tier': user.subscription_tier,
        'role': user.role,
        'preferences': user.preferences,
        'created_at': user.created_at
    })