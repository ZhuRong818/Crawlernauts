# backend/routes_auth.py
from flask import Blueprint, request, session, jsonify
from models import db, User, VerificationCode
from datetime import datetime
from mailer import send_verification_email
import re
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data     = request.get_json() or {}
    username = data.get('username')  # e-mail
    password = data.get('password')
    if not username or not password:
        return jsonify(msg="Username and password required"), 400
    if (
        len(password) < 6
        or not re.search(r"[A-Za-z]", password)
        or not re.search(r"\d", password)
    ):
        return jsonify(
            msg="Password must be at least 6 characters and include both letters and numbers"
        ), 400


    existing = User.query.filter_by(username=username).first()


    # can't re-use that email
    if existing and existing.verified:
        return jsonify(msg="Username already taken"), 409
       
    if existing:
        user = existing
        user.set_password(password)
        user.ensure_api_key()
        db.session.commit()
    else:
        # new user
        user = User(username=username)
        user.set_password(password)
        user.ensure_api_key()
        db.session.add(user)
        db.session.commit()


    session.clear()
    session['pending_user_id'] = user.id


    vc = VerificationCode.generate_for(user, ttl_minutes=5)
    try:
        send_verification_email(user.username, vc.code)
    except Exception as e:
        return jsonify(msg=f"mail_error: {e}"), 500


    return jsonify(msg="registered", needsVerify=True), 200




@auth_bp.route('/verify', methods=['POST'])
def verify_email():
    data = request.get_json() or {}
    code = (data.get('code') or '').strip()
    uid  = session.get('pending_user_id')
    if not uid:
        return jsonify(msg="not_logged_in"), 403


    user = User.query.get(uid)
    if not user:
        return jsonify(msg="not_logged_in"), 403


    vc = (VerificationCode.query
          .filter_by(user_id=uid, code=code)
          .first())
    if vc and vc.code != code:
        return jsonify(msg="invalid_or_expired"), 400
    if not vc or vc.expires_at < datetime.utcnow():
        return jsonify(msg="invalid_or_expired"), 400


    user.verified = True
    db.session.delete(vc)
    db.session.commit()


    session.clear()
    session['user_id'] = user.id


    return jsonify(msg="verified", apiKey=user.api_key), 200


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and start a session."""
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify(msg="Username and password required"), 400


    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify(msg="Invalid username of password"), 403


    if not user.verified:
        return jsonify(msg="unverified email"), 403


    session.clear()
    session['user_id'] = user.id
    return jsonify(msg="logged_in"), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Log out the current user by clearing the session."""
    session.clear()
    return jsonify(msg="logged_out"), 200


@auth_bp.route('/me', methods=['GET'])
def me():
    """Return current logged-in user's info (if any)."""
    uid = session.get('user_id')
    user = User.query.get(uid)
    if not user:
        return jsonify(msg="not_logged_in"), 403
    return jsonify(user.as_simple()), 200


@auth_bp.route('/regenerate_key', methods=['POST'])
def regenerate_key():
    """Generate a new API key for the current user."""
    uid = session.get('user_id')
    user = User.query.get(uid)
    user.api_key = User.generate_api_key()  # replace with a new key
    db.session.commit()
    return jsonify(apiKey=user.api_key, msg="key_regenerated"), 200


@auth_bp.route('/verify/send', methods=['POST'])
def send_verification_code():
    """Generate and send a new verification code if needed."""
    uid = session.get("user_id")


    user = User.query.get(uid)
    if user.verified:
        return jsonify(msg="already_verified"), 200


    # do not resend yet
    existing = VerificationCode.query.filter_by(user_id=uid).order_by(VerificationCode.expires_at.desc()).first()
    if existing and existing.expires_at > datetime.utcnow():
        return jsonify(msg="already_sent"), 409


    vc = VerificationCode.generate_for(user, ttl_minutes=1)
    try:
        send_verification_email(user.username, vc.code)
    except Exception as e:
        return jsonify(msg=f"mail_error: {e}"), 500


    return jsonify(msg="sent"), 200
