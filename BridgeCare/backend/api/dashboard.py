# backend/api/dashboard.py
from flask import Blueprint, request, jsonify, session, url_for
from backend.supabase_client import supabase
import json
from datetime import datetime
import traceback

dashboard_bp = Blueprint('dashboard', __name__)


# Admin dashboard data
@dashboard_bp.route('/admin/data')
def admin_data():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get all users
    users = supabase.table('users').select('*').execute()
    
    # Get all records from different tables
    volunteers = supabase.table('volunteer_data').select('*').execute()
    healthcare = supabase.table('healthcare_data').select('*').execute()
    hotels = supabase.table('hotel_data').select('*').execute()
    ngo_data = supabase.table('ngo_data').select('*').execute()
    donations = supabase.table('donations').select('*').execute()
    
    return jsonify({
        'users': users.data,
        'volunteers': volunteers.data,
        'healthcare': healthcare.data,
        'hotels': hotels.data,
        'ngo_data': ngo_data.data,
        'donations': donations.data
    })

## Volunteer API Routes


# ---------------------------------------------------
# Volunteer ping
# ---------------------------------------------------
@dashboard_bp.route('/api/volunteer/ping', methods=['GET'])
def volunteer_ping():
    return jsonify({'ok': True, 'message': 'volunteer API reachable'}), 200


# ---------------------------------------------------
# GET VOLUNTEER PROFILE
# ---------------------------------------------------
@dashboard_bp.route('/api/volunteer/profile', methods=['GET'])
def get_volunteer_profile():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user_id = session['user_id']
        
        # Get user details first
        user_response = supabase.table('users').select('id, name, email, phone').eq('id', user_id).execute()
        if not user_response.data:
            return jsonify({'error': 'User not found'}), 404
        
        user_data = user_response.data[0]
        
        # Get volunteer_data entry (references users via volunteer_id)
        volunteer_response = supabase.table('volunteer_data').select('*').eq('volunteer_id', user_id).execute()
        
        if volunteer_response.data:
            # Merge volunteer data with user info
            volunteer_info = volunteer_response.data[0]
            volunteer_info.update(user_data)
            return jsonify(volunteer_info), 200
        else:
            # Return just user data (no volunteer_data entry yet)
            return jsonify(user_data), 200
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------
# VOLUNTEER STATISTICS
# ---------------------------------------------------
@dashboard_bp.route('/api/volunteer/stats', methods=['GET'])
def volunteer_stats():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user_id = session['user_id']
        
        # Get volunteer data for stats
        response = supabase.table('volunteer_data').select('*').eq('volunteer_id', user_id).execute()
        
        if response.data:
            volunteer = response.data[0]
            return jsonify({
                'tasks_completed': volunteer.get('hours_volunteered', 0),
                'ongoing_tasks': 0,
                'people_helped': volunteer.get('people_helped', 0),
                'food_delivered': 0,
                'emergency_cases': 0
            }), 200
        else:
            # Return default stats if no volunteer_data entry
            return jsonify({
                'tasks_completed': 0,
                'ongoing_tasks': 0,
                'people_helped': 0,
                'food_delivered': 0,
                'emergency_cases': 0
            }), 200
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------
# UPDATE VOLUNTEER PROFILE
# ---------------------------------------------------
@dashboard_bp.route('/api/volunteer/update_profile', methods=['POST'])
def update_volunteer_profile():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user_id = session['user_id']
        data = request.json
        
        # Update volunteer profile
        update_data = {
            'assigned_region': data.get('assigned_region'),
            'status': data.get('status'),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Update user details
        user_update_data = {
            'name': data.get('name'),
            'email': data.get('email'),
            'phone': data.get('phone')
        }
        
        # Update both tables
        volunteer_response = supabase.table('volunteer_data').update(update_data).eq('volunteer_id', user_id).execute()
        user_response = supabase.table('users').update(user_update_data).eq('id', user_id).execute()
        
        if volunteer_response.data and user_response.data:
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully'
            }), 200
        else:
            return jsonify({'error': 'Failed to update profile'}), 500
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------
# GET VOLUNTEER HISTORY
# ---------------------------------------------------
@dashboard_bp.route('/api/volunteer/history', methods=['GET'])
def get_volunteer_history():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user_id = session['user_id']
        
        # Get homeless individuals registered by this volunteer (use volunteer_id directly)
        response = supabase.table('homeless_people').select('*').eq('volunteer_id', user_id).order('created_at', desc=True).execute()
        return jsonify(response.data if response.data else []), 200
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------
# GET RECENT HOMELESS INDIVIDUALS
# ---------------------------------------------------
@dashboard_bp.route('/api/volunteer/homeless_recent', methods=['GET'])
def get_homeless_recent():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        resp = (
            supabase.table('homeless_people')
            .select('*')
            .order('created_at', desc=True)
            .limit(10)
            .execute()
        )
        if getattr(resp, 'error', None):
            print('DB ERROR homeless_recent ->', resp.error)
            return jsonify({'error': 'Database error', 'db_error': getattr(resp, 'error')}), 500
        return jsonify(resp.data if resp.data else []), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------
# VOLUNTEER ALERTS (alias for alerts used by frontend)
# ---------------------------------------------------
@dashboard_bp.route('/api/volunteer/alerts', methods=['GET'])
def volunteer_alerts():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Try to fetch active alerts; fall back to empty list
        resp = supabase.table('volunteer_alerts').select('*').eq('status', 'active').execute()
        return jsonify(resp.data if resp.data else []), 200
    except Exception:
        return jsonify([]), 200


# ---------------------------------------------------
# REGISTER A NEW HOMELESS PERSON
# ---------------------------------------------------
@dashboard_bp.route('/api/volunteer/register_homeless', methods=['POST'])
def register_homeless():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 401

    # Accept both JSON and form-data
    data = request.get_json(silent=True)
    if not data:
        data = request.form.to_dict()

    if not data:
        return jsonify({'error': 'Missing data (JSON or form-data required)'}), 400

    try:
        # Parse needs from either JSON array or string
        needs = data.get("needs", [])
        if isinstance(needs, str):
            try:
                needs = json.loads(needs)
            except Exception:
                needs = []

        entry = {
            "volunteer_id": session["user_id"],
            "name": data.get("name"),
            "age": int(data.get("age")) if data.get("age") else None,
            "gender": data.get("gender"),
            "location": data.get("location"),
            "health_status": data.get("health_status"),
            "contact_info": json.dumps(needs),
            "notes": data.get("notes", ""),
            "created_at": datetime.utcnow().isoformat()
        }

        print('DEBUG: Inserting entry ->', entry)
        resp = supabase.table("homeless_people").insert(entry).execute()
        print('DEBUG: Insert response ->', getattr(resp, 'data', None), 'error ->', getattr(resp, 'error', None))

        if resp.data:
            return jsonify({"success": True, "data": resp.data[0]}), 201
        else:
            err = getattr(resp, 'error', None)
            return jsonify({"success": False, "message": "Failed to register", "db_error": err}), 400

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------
# GET VOLUNTEER TASKS
# ---------------------------------------------------
@dashboard_bp.route('/api/volunteer/tasks', methods=['GET'])
def volunteer_tasks():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']

    try:
        resp = supabase.table("volunteer_tasks").select("*").eq("assigned_to", user_id).execute()
        if getattr(resp, 'error', None):
            print('DB ERROR volunteer_tasks ->', resp.error)
            return jsonify({'error': 'Database error', 'db_error': getattr(resp, 'error')}), 500
        return jsonify(resp.data if resp.data else []), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------
# UPDATE TASK STATUS (COMPLETE / ESCALATE / ACCEPT)
# ---------------------------------------------------
@dashboard_bp.route('/api/volunteer/tasks/<task_id>/complete', methods=['POST'])
def task_complete(task_id):
    return update_task_status(task_id, "completed")


@dashboard_bp.route('/api/volunteer/tasks/<task_id>/escalate', methods=['POST'])
def task_escalate(task_id):
    return update_task_status(task_id, "escalated")


@dashboard_bp.route('/api/volunteer/tasks/<task_id>/accept', methods=['POST'])
def task_accept(task_id):
    return update_task_status(task_id, "accepted")


# ---------------------------------------------------
# REUSABLE TASK UPDATE FUNCTION
# ---------------------------------------------------
def update_task_status(task_id, status):
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        resp = (
            supabase.table("volunteer_tasks")
            .update({"status": status, "updated_at": datetime.utcnow().isoformat()})
            .eq("id", task_id)
            .execute()
        )

        if getattr(resp, 'error', None):
            print('DB ERROR update_task_status ->', resp.error)
            return jsonify({'success': False, 'db_error': getattr(resp, 'error')}), 400

        return jsonify({"success": True, "status": status, "data": getattr(resp, 'data', None)}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Hotel - add food donation data
@dashboard_bp.route('/hotel/add_donation', methods=['POST'])
def add_food_donation():
    if session.get('role') != 'hotel':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    data['hotel_id'] = session.get('user_id')
    
    response = supabase.table('food_donations').insert(data).execute()
    
    if response.data:
        return jsonify({'success': True, 'message': 'Donation added successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to add donation'}), 400

# NGO - add needs data
@dashboard_bp.route('/ngo/add_needs', methods=['POST'])
def add_needs():
    if session.get('role') != 'ngo':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    data['ngo_id'] = session.get('user_id')
    
    response = supabase.table('needs').insert(data).execute()
    
    if response.data:
        return jsonify({'success': True, 'message': 'Needs added successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to add needs'}), 400

# Donor - add donation data
@dashboard_bp.route('/donor/add_donation', methods=['POST'])
def add_donation():
    # Require a logged-in user; allow donors (or any authenticated user) to post donations
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized: you must be logged in to post a donation'}), 401

    payload = request.json or {}
    # ensure donor_id is set to current user
    payload['donor_id'] = session.get('user_id')

    # normalize created_at server-side to ensure consistent timestamps
    from datetime import datetime
    payload.setdefault('created_at', datetime.utcnow().isoformat())

    # Basic validation
    if not payload.get('donation_type') or not payload.get('quantity'):
        return jsonify({'success': False, 'message': 'donation_type and quantity are required'}), 400

    try:
        response = supabase.table('donations').insert(payload).execute()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Database exception: {e}'}), 500

    # Return detailed response for debugging and confirmation
    resp_data = getattr(response, 'data', None)
    resp_error = getattr(response, 'error', None)

    if resp_data:
        # If supabase returned the created record(s), return the first id when available
        created_id = None
        try:
            if isinstance(resp_data, list) and len(resp_data) > 0:
                created_id = resp_data[0].get('id')
            elif isinstance(resp_data, dict):
                created_id = resp_data.get('id')
        except Exception:
            created_id = None

        return jsonify({'success': True, 'message': 'Donation added successfully', 'id': created_id, 'db_result': resp_data}), 201
    else:
        # include any error information returned by the client
        msg = 'Failed to add donation'
        if resp_error:
            msg += f": {resp_error}"
        # sometimes response is a plain dict
        if isinstance(response, dict) and response.get('error'):
            msg += f": {response.get('error')}"
        return jsonify({'success': False, 'message': msg, 'db_error': resp_error}), 400


# Donor - get donation history (including records stored in `campaigns` table)
@dashboard_bp.route('/donor/history', methods=['GET'])
def donor_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session.get('user_id')

    # Get donor's name from users table
    try:
        user_resp = supabase.table('users').select('name, email').eq('id', user_id).execute()
        user_data = user_resp.data[0] if user_resp.data else {'name': 'Donor', 'email': ''}
    except Exception:
        user_data = {'name': 'Donor', 'email': ''}

    # Fetch donations created in the donations table
    try:
        d_resp = supabase.table('donations').select('*').eq('donor_id', user_id).execute()
        donations_data = d_resp.data or []
    except Exception:
        donations_data = []

    # Also fetch any donation-like records stored in a `campaigns` table
    try:
        c_resp = supabase.table('campaigns').select('*').eq('donor_id', user_id).execute()
        campaigns_data = c_resp.data or []
    except Exception:
        campaigns_data = []

    # Normalize records to a common shape for the frontend
    normalized = []
    for d in donations_data:
        normalized.append({
            'id': d.get('id'),
            'date': d.get('created_at') or d.get('date'),
            'donation_type': d.get('donation_type') or d.get('type') or 'Donation',
            'quantity': d.get('quantity') or d.get('amount') or d.get('value'),
            'description': d.get('description'),
            'status': d.get('status') or 'pending',
            'source': 'donations'
        })

    for c in campaigns_data:
        # campaign records might represent a donation or a pledge; attempt to map fields
        normalized.append({
            'id': c.get('id'),
            'date': c.get('created_at') or c.get('updated_at') or c.get('date'),
            'donation_type': c.get('donation_type') or c.get('type') or c.get('campaign_name') or 'Campaign',
            'quantity': c.get('quantity') or c.get('amount') or c.get('contribution') or c.get('raised'),
            'description': c.get('description') or c.get('notes') or c.get('campaign_description'),
            'status': c.get('status') or 'completed',
            'source': 'campaigns'
        })

    # Compute simple stats
    total_donated = 0
    pending = 0
    completed = 0
    for r in normalized:
        status = (r.get('status') or '').lower()
        if status == 'pending':
            pending += 1
        if status == 'completed' or status == 'done' or status == 'success':
            completed += 1

        # Try to parse numeric amount where possible
        q = r.get('quantity')
        if isinstance(q, (int, float)):
            try:
                total_donated += float(q)
            except Exception:
                pass
        elif isinstance(q, str):
            # strip non-numeric characters like $ and commas
            import re
            m = re.sub(r"[^0-9.\-]", '', q)
            try:
                total_donated += float(m) if m else 0
            except Exception:
                pass

    # Sort by date descending if dates available
    try:
        normalized.sort(key=lambda x: x.get('date') or '', reverse=True)
    except Exception:
        pass

    return jsonify({
        'name': user_data.get('name'),
        'email': user_data.get('email'),
        'donations': normalized,
        'stats': {
            'total_donated': total_donated,
            'pending': pending,
            'completed': completed,
            'count': len(normalized)
        }
    })


# Donor - list active campaigns (frontend expects an array of campaigns)
@dashboard_bp.route('/donor/campaigns', methods=['GET'])
def donor_campaigns():
    # Return available campaigns; no strict auth required but we'll allow only logged-in users
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # try to fetch campaigns; prefer an 'active' status if available
        resp = supabase.table('campaigns').select('*').execute()
        campaigns = resp.data or []
    except Exception:
        campaigns = []

    # Map to expected frontend structure (title, description, goal, raised)
    mapped = []
    for c in campaigns:
        mapped.append({
            'id': c.get('id'),
            'title': c.get('campaign_name') or c.get('title') or c.get('name'),
            'description': c.get('campaign_description') or c.get('description'),
            'goal': c.get('goal') or c.get('target') or c.get('goal_amount') or 0,
            'raised': c.get('raised') or c.get('amount_raised') or c.get('contributions') or 0,
            'status': c.get('status')
        })

    return jsonify({'campaigns': mapped})
# Volunteer API Routes are defined above using the `dashboard_bp` blueprint.