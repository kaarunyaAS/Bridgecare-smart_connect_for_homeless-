from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
from flask_cors import CORS

from backend.api.auth import auth_bp
from backend.api.dashboard import dashboard_bp
from backend.api.user_management import user_bp
from backend.api.healthcare import healthcare_bp
from backend.api.ngo import ngo_bp
from backend.api.admin_api import admin_api_bp
from backend.supabase_client import supabase, safe_supabase_write

import json
from datetime import datetime

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(user_bp)
# Register the healthcare blueprint once (it already defines full paths)
app.register_blueprint(healthcare_bp)
app.register_blueprint(ngo_bp)
app.register_blueprint(admin_api_bp)

@app.route('/')
def index():
    return render_template('index.html')

# Dashboard routes
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('role') != 'admin':
        return redirect('/' + session.get('role', 'donor'))
    return render_template('admin.html')

@app.route('/healthcare')
def healthcare_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('role') != 'healthcare':
        return redirect('/' + session.get('role', 'donor'))
    return render_template('healthcare.html')

@app.route('/hotel')
def hotel_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('role') != 'hotel':
        return redirect('/' + session.get('role', 'donor'))
    return render_template('hotel.html')

@app.route('/ngo')
def ngo_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('role') != 'ngo':
        return redirect('/' + session.get('role', 'donor'))
    return render_template('ngo.html')

@app.route('/volunteer')
def volunteer_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('role') != 'volunteer':
        return redirect('/' + session.get('role', 'donor'))
    return render_template('volunteer.html')

@app.route('/donor')
def donor_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('role') != 'donor':
        return redirect('/' + session.get('role', 'donor'))
    return render_template('donor.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/logout-success')
def logout_success():
    """Show logout success message"""
    return render_template('logout_success.html')


# Fallback POST handler for volunteer homeless registration.
# This ensures the route exists even if the volunteer blueprint isn't registered correctly.
@app.route('/api/volunteer/register_homeless', methods=['POST'])
def fallback_register_homeless():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        user_id = session['user_id']
        # Use user_id directly as volunteer_id (FK to users table)

        data = request.form
        needs = json.loads(data.get('needs', '[]'))

        homeless_data = {
            'volunteer_id': user_id,
            'name': data.get('name'),
            'age': int(data.get('age')) if data.get('age') else None,
            'gender': data.get('gender'),
            'location': data.get('location'),
            'health_status': data.get('health_status'),
            'contact_info': json.dumps(needs) if needs else None,
            'created_at': datetime.utcnow().isoformat()
        }

        print('FALLBACK DEBUG: inserting homeless_data ->', homeless_data)
        res = safe_supabase_write(lambda: supabase.table('homeless_people').insert(homeless_data).execute(), "insert homeless")
        print('FALLBACK DEBUG: insert result ->', res)

        if res.get('success') and res.get('data'):
            return jsonify({'success': True, 'message': 'Homeless individual registered successfully', 'data': res.get('data')[0]}), 201
        else:
            return jsonify({'success': False, 'message': 'Failed to register individual', 'db_error': res.get('error')}), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# Accept trailing-slash variant and OPTIONS (for preflight) and delegate to the same handler
@app.route('/api/volunteer/register_homeless/', methods=['POST', 'OPTIONS'])
def fallback_register_homeless_slash():
    # Delegate to existing handler function
    return fallback_register_homeless()


@app.route('/api/volunteer/register_homeless', methods=['GET'])
def fallback_register_homeless_get():
    # simple GET for quick verification in browser
    return jsonify({'ok': True, 'note': 'register_homeless endpoint (GET) is reachable'})


@app.route('/__routes')
def show_routes():
    # Debug helper: list registered routes and methods
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({'endpoint': rule.endpoint, 'rule': str(rule), 'methods': sorted(list(rule.methods))})
    return jsonify({'routes': routes})


# Debug endpoint: supabase env info (does NOT return secret values)
@app.route('/api/debug/supabase-info')
def supabase_info():
    import os
    has_service_key = bool(os.environ.get('SUPABASE_SERVICE_ROLE_KEY'))
    has_anon_key = bool(os.environ.get('SUPABASE_KEY'))
    return jsonify({
        'supabase_url_present': bool(os.environ.get('SUPABASE_URL')),
        'has_service_role_key': has_service_key,
        'has_anon_key': has_anon_key,
        'advice': 'If writes fail, ensure SUPABASE_SERVICE_ROLE_KEY is set for server-side writes or create appropriate RLS policies for anon key.'
    })


if __name__ == '__main__':
    # Print registered routes at startup for debugging
    print('Registered routes:')
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {sorted(list(rule.methods))}")
    # use_reloader=False to avoid WinError 10038 on Windows (socket reloader issue)
    app.run(debug=True, use_reloader=False)

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": [
            "GET  /api/status",
            "GET  /api/healthcare/patients",
            "POST /api/healthcare/patients",
            "GET  /api/healthcare/appointments",
            "POST /api/healthcare/appointments",
            "GET  /api/healthcare/providers",
            "GET  /api/healthcare/dashboard/stats",
            "GET  /api/healthcare/database/check"
        ]
    }), 404

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": [
            "GET  /api/status",
            "GET  /api/healthcare/patients",
            "POST /api/healthcare/patients",
            "GET  /api/healthcare/appointments",
            "POST /api/healthcare/appointments",
            "GET  /api/healthcare/providers",
            "GET  /api/healthcare/dashboard/stats",
            "GET  /api/healthcare/database/check"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "message": "Please check the server logs for details"
    }), 500

# ==================== MAIN EXECUTION ====================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 BridgeCare Platform - Starting Server")
    print("=" * 50)
    print("📊 Supabase client: configured in backend modules (see .env)")
    print("🔑 Database keys are loaded from environment (not printed for security)")
    
    # Note: database table checks are performed by the healthcare blueprint at /api/health/status
    print("\n🔍 Database status will be available at /api/health/status (if the API is running)")
    
    print("\n🌐 Server Information:")
    print("   Local: http://localhost:5000")
    print("   Healthcare Dashboard: http://localhost:5000/healthcare")
    print("   API Status: http://localhost:5000/api/status")
    
    print("\n📋 Available API Endpoints:")
    print("   Healthcare:")
    print("     GET  /api/healthcare/patients")
    print("     POST /api/healthcare/patients")
    print("     GET  /api/healthcare/appointments")
    print("     POST /api/healthcare/appointments")
    print("     GET  /api/healthcare/providers")
    print("     GET  /api/healthcare/dashboard/stats")
    print("     GET  /api/healthcare/database/check")
    print("     POST /api/healthcare/initialize-sample")
    
    print("\n" + "=" * 50)
    print("✅ Server is ready! Press Ctrl+C to stop.")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)