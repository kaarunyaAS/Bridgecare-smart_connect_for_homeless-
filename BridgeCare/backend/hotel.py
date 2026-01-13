from flask import Blueprint, request, jsonify, session
from backend.supabase_client import supabase
from datetime import datetime, timedelta
import logging

hotel_bp = Blueprint('hotel', __name__, url_prefix='/api/hotel')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    try:
        # Try to select from the table (limit 0 to avoid loading data)
        supabase.table(table_name).select('*').limit(0).execute()
        return True
    except Exception as e:
        logger.warning(f"Table {table_name} might not exist: {e}")
        return False

def create_missing_tables():
    """Create missing tables if they don't exist"""
    tables_to_check = [
        'hotels', 'meal_requests', 'donations', 'hotel_inventory',
        'donation_schedule', 'hotel_notifications', 'hotel_feedback',
        'hotel_volunteer_coordination'
    ]
    
    for table in tables_to_check:
        if not check_table_exists(table):
            logger.info(f"Table {table} doesn't exist, attempting to create...")
            # You would execute the SQL to create the table here
            # For now, we'll just log
            logger.warning(f"Table {table} needs to be created. Run the SQL script first.")

@hotel_bp.before_request
def check_hotel_auth():
    """Check if user is authenticated as a hotel"""
    if request.endpoint in ['hotel.auth_check', 'hotel.login']:
        return
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    token = auth_header.split(' ')[1]
    
    # Verify token and check role
    try:
        # Get user from session or verify token
        if 'user_id' not in session or session.get('role') != 'hotel':
            # First check if hotels table exists
            if not check_table_exists('hotels'):
                create_missing_tables()
                return jsonify({'error': 'System initialization required'}), 503
            
            # Verify with Supabase
            user_response = supabase.auth.get_user(token)
            if user_response.user:
                user = user_response.user
                # Check if user is a hotel
                hotel_check = supabase.table('hotels').select('*').eq('user_id', user.id).execute()
                if not hotel_check.data:
                    return jsonify({'error': 'Not a hotel account'}), 403
                
                # Store in session
                session['user_id'] = user.id
                session['role'] = 'hotel'
                session['hotel_id'] = hotel_check.data[0]['id']
            else:
                return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"Auth error: {e}")
        return jsonify({'error': 'Authentication failed'}), 401

@hotel_bp.route('/init', methods=['GET'])
def initialize_tables():
    """Initialize hotel-related tables (admin only)"""
    try:
        create_missing_tables()
        return jsonify({'message': 'Table initialization completed'}), 200
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        return jsonify({'error': 'Failed to initialize tables'}), 500

@hotel_bp.route('/dashboard/stats', methods=['GET'])
def dashboard_stats():
    """Get hotel dashboard statistics"""
    try:
        hotel_id = session.get('hotel_id')
        
        # Initialize counters
        total_meals = 0
        completed_donations = 0
        pending_requests = 0
        urgent_requests = 0
        recent_requests = []
        recent_donations = []
        
        # Check if donations table exists
        if check_table_exists('donations'):
            # Get total meals donated
            total_donations = supabase.table('donations').select('quantity').eq('hotel_id', hotel_id).execute()
            if total_donations.data:
                total_meals = sum(d['quantity'] for d in total_donations.data)
            
            # Get completed donations
            completed_donations_resp = supabase.table('donations').select('id').eq('hotel_id', hotel_id).eq('status', 'completed').execute()
            completed_donations = len(completed_donations_resp.data) if completed_donations_resp.data else 0
            
            # Get recent donations (last 10)
            recent_donations_resp = supabase.table('donations').select('*, beneficiaries(name)').eq('hotel_id', hotel_id).order('created_at', desc=True).limit(10).execute()
            recent_donations = recent_donations_resp.data if recent_donations_resp.data else []
        
        # Check if meal_requests table exists
        if check_table_exists('meal_requests'):
            # Get pending requests assigned to this hotel
            pending_requests_resp = supabase.table('meal_requests').select('id').eq('assigned_hotel_id', hotel_id).eq('status', 'pending').execute()
            pending_requests = len(pending_requests_resp.data) if pending_requests_resp.data else 0
            
            # Get urgent requests
            urgent_requests_resp = supabase.table('meal_requests').select('id').eq('assigned_hotel_id', hotel_id).eq('priority', 'high').eq('status', 'pending').execute()
            urgent_requests = len(urgent_requests_resp.data) if urgent_requests_resp.data else 0
            
            # Get recent requests (last 10)
            recent_requests_resp = supabase.table('meal_requests').select('*, organizations(name)').eq('assigned_hotel_id', hotel_id).order('created_at', desc=True).limit(10).execute()
            recent_requests = recent_requests_resp.data if recent_requests_resp.data else []
        
        return jsonify({
            'total_meals': total_meals,
            'completed_donations': completed_donations,
            'pending_requests': pending_requests,
            'urgent_requests': urgent_requests,
            'recent_requests': recent_requests,
            'recent_donations': recent_donations
        }), 200
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return jsonify({'error': 'Failed to load dashboard statistics'}), 500

# All other routes remain the same, but with table existence checks...

@hotel_bp.route('/donations', methods=['POST'])
def create_donation():
    """Create a new meal donation"""
    try:
        # Check if donations table exists
        if not check_table_exists('donations'):
            return jsonify({'error': 'Donations system not initialized'}), 503
        
        hotel_id = session.get('hotel_id')
        data = request.json
        
        # Validate required fields
        required_fields = ['meal_type', 'quantity', 'pickup_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create donation record
        donation_data = {
            'hotel_id': hotel_id,
            'meal_type': data['meal_type'],
            'quantity': data['quantity'],
            'description': data.get('description', ''),
            'pickup_time': data['pickup_time'],
            'priority': data.get('priority', 'medium'),
            'status': 'available',
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = supabase.table('donations').insert(donation_data).execute()
        
        if result.data:
            # Check if notifications table exists
            if check_table_exists('notifications'):
                # Create notification for NGOs
                notification_data = {
                    'type': 'new_donation',
                    'title': 'New Meal Donation Available',
                    'message': f'Hotel has donated {data["quantity"]} {data["meal_type"]} meals',
                    'related_id': result.data[0]['id'],
                    'created_at': datetime.utcnow().isoformat()
                }
                
                supabase.table('notifications').insert(notification_data).execute()
            
            return jsonify({
                'message': 'Donation created successfully',
                'donation_id': result.data[0]['id']
            }), 201
        else:
            return jsonify({'error': 'Failed to create donation'}), 500
            
    except Exception as e:
        logger.error(f"Create donation error: {e}")
        return jsonify({'error': 'Failed to create donation'}), 500

@hotel_bp.route('/donations', methods=['GET'])
def get_donations():
    """Get hotel's donations with filtering"""
    try:
        # Check if donations table exists
        if not check_table_exists('donations'):
            return jsonify({'error': 'Donations system not initialized'}), 503
        
        hotel_id = session.get('hotel_id')
        
        # Get query parameters
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = supabase.table('donations').select('*, beneficiaries(name)').eq('hotel_id', hotel_id)
        
        # Apply filters
        if status:
            query = query.eq('status', status)
        
        if start_date:
            query = query.gte('created_at', start_date)
        
        if end_date:
            query = query.lte('created_at', end_date)
        
        # Order by creation date
        query = query.order('created_at', desc=True)
        
        result = query.execute()
        
        return jsonify(result.data if result.data else []), 200
        
    except Exception as e:
        logger.error(f"Get donations error: {e}")
        return jsonify({'error': 'Failed to get donations'}), 500

# ... (other routes with similar table existence checks)

@hotel_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for hotel system"""
    try:
        tables = [
            'hotels', 'meal_requests', 'donations', 'hotel_inventory',
            'donation_schedule', 'hotel_notifications', 'hotel_feedback',
            'hotel_volunteer_coordination'
        ]
        
        table_status = {}
        for table in tables:
            table_status[table] = check_table_exists(table)
        
        # Check if user is authenticated
        auth_status = 'user_id' in session and session.get('role') == 'hotel'
        
        return jsonify({
            'status': 'ok',
            'authenticated': auth_status,
            'tables': table_status,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Add this to register the blueprint in your main app
# app.register_blueprint(hotel_bp)