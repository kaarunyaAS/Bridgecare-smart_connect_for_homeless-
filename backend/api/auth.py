from flask import Blueprint, request, jsonify, session, redirect, url_for
from backend.supabase_client import supabase, safe_supabase_write
import hashlib
import traceback


auth_bp = Blueprint('auth', __name__)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        # Expect JSON body with: name, email, phone, organization, role, password
        data = request.get_json() or {}
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        organization = data.get('organization')
        role = data.get('role')
        password = data.get('password')

        if not name or not email or not role or not password:
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        # Check if user already exists
        existing = supabase.table('users').select('*').eq('email', email).execute()

        # supabase response uses .data
        existing_rows = getattr(existing, 'data', None)
        if existing_rows:
            return jsonify({"success": False, "message": "User with this email already exists"}), 400

        # Insert user record
        user_record = {
            'name': name,
            'email': email,
            'phone': phone,
            'organization': organization,
            'role': role,
            'password_hash': hash_password(password)
        }

        res = safe_supabase_write(lambda: supabase.table('users').insert(user_record).execute(), "auth register user")
        if not res.get('success'):
            return jsonify({"success": False, "message": f"Failed to create user: {res.get('error')}"}), 500

        return jsonify({"success": True, "message": "Registration successful"}), 201
    except Exception as e:
        # Log traceback to console and return JSON error so client sees message instead of plain 500
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Internal error: {e}"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        # Expect JSON body with: email, password
        data = request.get_json() or {}
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"success": False, "message": "Email and password are required"}), 400

        # Query user by email
        result = supabase.table('users').select('*').eq('email', email).execute()
        users = getattr(result, 'data', None)

        if not users or len(users) == 0:
            return jsonify({"success": False, "message": "Invalid email or password"}), 401

        user = users[0]
        password_hash = hash_password(password)

        # Verify password
        if user.get('password_hash') != password_hash:
            return jsonify({"success": False, "message": "Invalid email or password"}), 401

        # Store user info in session
        session['user_id'] = user.get('id')
        session['email'] = user.get('email')
        session['role'] = user.get('role')
        session['name'] = user.get('name')

        # Log the login activity
        try:
            login_activity = {
                'user_id': user.get('id'),
                'email': user.get('email'),
                'role': user.get('role'),
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', 'Unknown'),
                'status': 'success'
            }
            safe_supabase_write(lambda: supabase.table('login_activities').insert(login_activity).execute(), "log login activity")
        except Exception as log_err:
            # Log the error but don't fail the login
            traceback.print_exc()
            print(f"Failed to log login activity: {log_err}")

        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user.get('id'),
                "name": user.get('name'),
                "email": user.get('email'),
                "role": user.get('role')
            }
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Internal error: {e}"}), 500

@auth_bp.route('/logout')
def logout():
    try:
        # Clear all session data
        session.clear()
        # Redirect to home page after logout
        return redirect(url_for('index'))
    except Exception as e:
        traceback.print_exc()
        return redirect(url_for('index'))

@auth_bp.route('/logout-json', methods=['POST'])
def logout_json():
    """JSON logout endpoint for AJAX calls"""
    try:
        # Clear all session data
        session.clear()
        return jsonify({"success": True, "message": "Logged out successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Internal error: {e}"}), 500


@auth_bp.route('/api/auth/current-user', methods=['GET'])
def current_user():
    """Return the current logged-in user info from session (if any)."""
    try:
        if 'user_id' not in session:
            return jsonify({"success": False, "user": None}), 200

        return jsonify({
            "success": True,
            "user": {
                "id": session.get('user_id'),
                "name": session.get('name'),
                "email": session.get('email'),
                "role": session.get('role')
            }
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route('/api/auth/fake-login', methods=['POST'])
def fake_login():
    """Development helper: set a fake session for testing dashboard rendering.

    Accepts optional JSON: {"role":"hotel", "id":"<id>", "name":"Hotel Test","email":"h@test"}
    This endpoint is intended for local development only.
    """
    try:
        data = request.get_json() or {}
        role = data.get('role', 'hotel')
        user_id = data.get('id', 'test-hotel-1')
        name = data.get('name', 'Hotel Test')
        email = data.get('email', 'hotel@example.org')

        session['user_id'] = user_id
        session['role'] = role
        session['name'] = name
        session['email'] = email

        return jsonify({"success": True, "message": "Fake session set", "user": {"id": user_id, "role": role, "name": name}}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500