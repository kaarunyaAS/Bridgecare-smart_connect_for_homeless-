# backend/api/user_management.py
from flask import Blueprint, request, jsonify, session
from backend.supabase_client import supabase, safe_supabase_write

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile')
def get_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    response = supabase.table('users').select('*').eq('id', session['user_id']).execute()
    
    if response.data:
        return jsonify(response.data[0])
    else:
        return jsonify({'error': 'User not found'}), 404

@user_bp.route('/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    
    res = safe_supabase_write(lambda: supabase.table('users').update(data).eq('id', session['user_id']).select().execute(), "update user profile")

    if res.get('success'):
        d = res.get('data')
        if isinstance(d, list) and d:
            return jsonify({'success': True, 'data': d[0]})
        elif isinstance(d, dict):
            return jsonify({'success': True, 'data': d})
        else:
            return jsonify({'success': True, 'data': None})
    else:
        return jsonify({'success': False, 'message': f"Failed to update profile: {res.get('error')}"}), 400