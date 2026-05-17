# healthcare.py (Updated Version)
import os
import pathlib
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from flask import Flask, request, jsonify, send_file,Blueprint
from flask_cors import CORS
import json
import pandas as pd
from io import BytesIO

# backend/api/healthcare.py
from flask import Blueprint, request, jsonify

# Create Blueprint
healthcare_bp  = Blueprint("healthcare_bp", __name__)

# Import centralized supabase client and helpers
from backend.supabase_client import supabase, safe_supabase_write, safe_supabase_query

# ==================== DATABASE VALIDATION FUNCTIONS ====================

def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    try:
        if not supabase:
            return False
        
        # Try a simple query on the table
        supabase.table(table_name).select('*').limit(1).execute()
        return True
    except Exception:
        return False

def get_table_status() -> Dict[str, bool]:
    """Check which tables exist in the database"""
    tables = ['patients', 'appointments', 'treatment_history', 'healthcare_providers', 'ngos', 'volunteers']
    status = {}
    
    for table in tables:
        status[table] = check_table_exists(table)
    
    return status

def create_missing_tables():
    """Create missing tables if they don't exist"""
    table_status = get_table_status()
    
    for table, exists in table_status.items():
        if not exists:
            print(f"⚠️ Table '{table}' does not exist. Creating...")
            # You could add SQL creation commands here
            # For now, just log the missing table

# ==================== HELPER FUNCTIONS ====================

def handle_supabase_error(e: Exception, operation: str) -> Dict[str, Any]:
    """Handle Supabase errors and return standardized response"""
    error_message = f"Error during {operation}: {str(e)}"
    print(f"[ERROR] {error_message}")
    
    # Check for specific error types
    error_str = str(e).lower()
    
    if "relation" in error_str and "does not exist" in error_str:
        # Table doesn't exist
        table_name = error_str.split('"')[1] if '"' in error_str else "unknown"
        return {
            "success": False,
            "error": f"Database table '{table_name}' doesn't exist. Please run the setup SQL first.",
            "code": "TABLE_NOT_FOUND",
            "details": str(e)
        }
    elif "foreign key" in error_str:
        # Foreign key constraint violation
        return {
            "success": False,
            "error": "Reference error. The related record doesn't exist.",
            "code": "FOREIGN_KEY_VIOLATION",
            "details": str(e)
        }
    else:
        return {
            "success": False,
            "error": error_message,
            "details": str(e)
        }

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Optional[Dict[str, Any]]:
    """Validate that all required fields are present in the data"""
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
        return {
            "success": False,
            "error": f"Missing required fields: {', '.join(missing_fields)}",
            "missing_fields": missing_fields,
            "code": "MISSING_FIELDS"
        }
    return None


# ==================== HEALTHCARE API ENDPOINTS ====================

@healthcare_bp.route('/api/health/status', methods=['GET'])
def health_status():
    """Health check endpoint with database status"""
    try:
        # Get database status
        table_status = get_table_status()
        
        # Try a simple query to test connection
        supabase_status = "connected" if supabase else "disconnected"
        
        # Get counts for existing tables
        counts = {}
        for table, exists in table_status.items():
            if exists:
                try:
                    result = supabase.table(table).select('id', count='exact').limit(1).execute()
                    counts[table] = result.count if hasattr(result, 'count') else len(result.data)
                except:
                    counts[table] = 0
        
        return jsonify({
            "success": True,
            "status": "healthy" if supabase else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "supabase": supabase_status,
            "database_tables": table_status,
            "record_counts": counts,
            "version": "1.0.0"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": str(e),
            "database_tables": get_table_status()
        }), 500


@healthcare_bp.route('/api/health/write-test', methods=['POST'])
def health_write_test():
    """Test whether the server can perform write/delete operations on the DB.

    This will attempt to insert a short-lived NGO record and then delete it. It
    returns the results of both operations so you can confirm write permissions.
    """
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        if not check_table_exists('ngos'):
            return jsonify({"success": False, "error": "Table 'ngos' does not exist"}), 400

        test_name = f"write-test-{int(datetime.now().timestamp())}"
        record = {"name": test_name, "contact_person": "health-check", "contact_number": "000"}

        insert_res = safe_supabase_write(lambda: supabase.table('ngos').insert(record).execute(), "health write test - insert")

        if not insert_res.get('success'):
            return jsonify({"success": False, "phase": "insert", "error": insert_res.get('error')}), 500

        inserted = None
        data = insert_res.get('data')
        if isinstance(data, list) and len(data) > 0:
            inserted = data[0]
        elif isinstance(data, dict):
            inserted = data

        if not inserted or not inserted.get('id'):
            # can't reliably clean up without id, return insert result
            return jsonify({"success": True, "inserted": inserted, "cleanup": "skipped - no id returned"})

        # Attempt cleanup
        delete_res = safe_supabase_write(lambda: supabase.table('ngos').delete().eq('id', inserted['id']).execute(), "health write test - delete")

        return jsonify({
            "success": True,
            "insert_result": insert_res,
            "delete_result": delete_res
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@healthcare_bp.route('/api/healthcare/debug/patient-insert', methods=['POST'])
def debug_patient_insert():
    """Debug helper: insert a patient and read it back to confirm persistence."""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        data = request.json or {}
        name = data.get('name', f"dbg-{int(datetime.now().timestamp())}")
        homeless_id = data.get('homeless_id', f"DBG{int(datetime.now().timestamp())}")

        patient_data = {
            'name': name,
            'homeless_id': homeless_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        insert_res = safe_supabase_write(lambda: supabase.table('patients').insert(patient_data).execute(), "debug insert patient")

        # Immediately query by homeless_id
        try:
            qresp = supabase.table('patients').select('*').eq('homeless_id', homeless_id).execute()
            queried = getattr(qresp, 'data', None) if qresp is not None else None
        except Exception as qe:
            queried = None

        # Sanitize insert_res before returning (raw supabase response objects are not JSON serializable)
        insert_sanitized = {k: v for k, v in insert_res.items() if k != 'raw'}
        insert_sanitized['raw'] = repr(insert_res.get('raw'))

        status_code = 200 if insert_res.get('success') else 500
        return jsonify({
            'success': insert_res.get('success', False),
            'insert_result': insert_sanitized,
            'queried_rows': queried
        }), status_code

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@healthcare_bp.route('/api/healthcare/database/fix-treatment-history', methods=['POST'])
def fix_treatment_history_schema():
    """Attempt to remove healthcare_provider_id column from treatment_history table"""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500
        
        # Note: Supabase Python client doesn't support raw SQL execution directly
        # This endpoint provides instructions and the SQL to run
        sql_script = """
-- Remove healthcare_provider_id from treatment_history table
ALTER TABLE IF EXISTS treatment_history 
DROP COLUMN IF EXISTS healthcare_provider_id;

-- Drop related index if exists
DROP INDEX IF EXISTS idx_treatment_history_provider_id;

-- Verify removal
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'treatment_history' 
ORDER BY ordinal_position;
"""
        
        return jsonify({
            "success": True,
            "message": "Please run the SQL script in Supabase SQL Editor",
            "instructions": [
                "1. Open your Supabase project dashboard",
                "2. Go to SQL Editor",
                "3. Copy and paste the SQL script below",
                "4. Click 'Run' to execute",
                "5. After running, try saving a prescription again"
            ],
            "sql_script": sql_script.strip(),
            "file_location": "docs/remove_healthcare_provider_id_from_treatment_history.sql"
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@healthcare_bp.route('/api/healthcare/database/setup', methods=['POST'])
def database_setup():
    """Endpoint to initialize database tables"""
    try:
        # This would typically run SQL setup scripts
        # For now, just check current status
        table_status = get_table_status()
        
        missing_tables = [table for table, exists in table_status.items() if not exists]
        
        if missing_tables:
            return jsonify({
                "success": False,
                "message": f"Missing tables: {', '.join(missing_tables)}",
                "tables": table_status,
                "instructions": "Please run the setup SQL script in Supabase SQL Editor to create missing tables."
            })
        else:
            return jsonify({
                "success": True,
                "message": "All required tables exist",
                "tables": table_status
            })
            
    except Exception as e:
        error_response = handle_supabase_error(e, "database setup check")
        return jsonify(error_response), 500

# ==================== PATIENTS ENDPOINTS (SAFE VERSION) ====================

@healthcare_bp.route('/api/healthcare/patients', methods=['GET'])
def get_patients():
    """Get all patients with optional filters (safe version)"""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500
        
        # Check if patients table exists
        if not check_table_exists('patients'):
            return jsonify({
                "success": False,
                "error": "Patients table doesn't exist. Please run database setup.",
                "code": "TABLE_NOT_FOUND"
            }), 404
        
        # Get query parameters
        ngo_id = request.args.get('ngo_id')
        is_active = request.args.get('is_active', 'true').lower() == 'true'
        search = request.args.get('search', '')
        limit = min(int(request.args.get('limit', 100)), 1000)  # Cap limit
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = supabase.table('patients').select('*')
        
        # Apply filters
        if ngo_id:
            query = query.eq('ngo_id', ngo_id)
        
        if search:
            query = query.or_(f'name.ilike.%{search}%,homeless_id.ilike.%{search}%')
        
        query = query.eq('is_active', is_active)
        query = query.order('created_at', desc=True)
        query = query.range(offset, offset + limit - 1)
        
        # Execute query
        response = query.execute()
        
        # Try to get NGO names if NGOs table exists
        patients_data = response.data
        if check_table_exists('ngos'):
            for patient in patients_data:
                if patient.get('ngo_id'):
                    try:
                        ngo_result = supabase.table('ngos').select('name').eq('id', patient['ngo_id']).single().execute()
                        if ngo_result.data:
                            patient['ngo_name'] = ngo_result.data['name']
                    except:
                        patient['ngo_name'] = None
        
        return jsonify({
            "success": True,
            "data": patients_data,
            "count": len(patients_data),
            "total": response.count if hasattr(response, 'count') else len(patients_data)
        })
        
    except Exception as e:
        error_response = handle_supabase_error(e, "fetching patients")
        return jsonify(error_response), 500

@healthcare_bp.route('/api/healthcare/patients/simple', methods=['GET'])
def get_patients_simple():
    """Get patients with minimal data (no joins)"""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500
        
        if not check_table_exists('patients'):
            return jsonify({
                "success": True,
                "data": [],
                "count": 0,
                "message": "Patients table not found"
            })
        
        response = supabase.table('patients').select('id, name, homeless_id, age, gender, is_active').execute()
        
        return jsonify({
            "success": True,
            "data": response.data,
            "count": len(response.data)
        })
        
    except Exception as e:
        error_response = handle_supabase_error(e, "fetching patients simple")
        return jsonify(error_response), 500


@healthcare_bp.route('/api/healthcare/patients', methods=['POST'])
def create_patient():
    """Create a new patient record in the database."""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        data = request.json or {}

        validation = validate_required_fields(data, ['name', 'homeless_id'])
        if validation:
            return jsonify(validation), 400

        patient_data = {
            'name': data['name'],
            'homeless_id': data['homeless_id'],
            'age': data.get('age'),
            'gender': data.get('gender'),
            'ngo_id': data.get('ngo_id'),
            'contact_number': data.get('contact_number'),
            'is_active': data.get('is_active', True),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        res = safe_supabase_write(lambda: supabase.table('patients').insert(patient_data).execute(), "create patient")
        # For debugging, allow returning raw supabase response when debug=1
        debug = request.args.get('debug') == '1'
        if not res.get('success'):
            payload = {"success": False, "error": res.get('error')}
            if debug:
                payload['raw'] = repr(res.get('raw'))
            return jsonify(payload), 500

        # Normalize returned data - Supabase may return list or dict or nothing depending on policy
        created = None
        d = res.get('data')
        if isinstance(d, list) and d:
            created = d[0]
        elif isinstance(d, dict) and d:
            created = d

        # If the insert didn't return the created row (e.g., due to RLS or returning settings), try to fetch by homeless_id
        if not created:
            fetch = safe_supabase_query(lambda: supabase.table('patients').select('*').eq('homeless_id', patient_data['homeless_id']).single().execute(), None, "fetch patient after insert")
            if fetch.get('success') and fetch.get('data'):
                created = fetch.get('data')

        payload = {"success": True, "data": created}
        if debug:
            payload['raw'] = repr(res.get('raw'))
        return jsonify(payload), 201

    except Exception as e:
        error_response = handle_supabase_error(e, "creating patient")
        return jsonify(error_response), 500


@healthcare_bp.route('/api/healthcare/patients/<patient_id>', methods=['PUT'])
def update_patient(patient_id: str):
    """Update an existing patient record."""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        data = request.json or {}
        if not data:
            return jsonify({"success": False, "error": "No update data provided"}), 400

        # Prepare update payload
        update_payload = {k: v for k, v in data.items() if k in ['name', 'age', 'gender', 'ngo_id', 'contact_number', 'is_active', 'updated_at', 'last_visit_date']}
        update_payload['updated_at'] = datetime.now().isoformat()

        res = safe_supabase_write(lambda: supabase.table('patients').update(update_payload).eq('id', patient_id).execute(), f"update patient {patient_id}")
        if not res.get('success'):
            return jsonify({"success": False, "error": res.get('error')}), 500

        # Try to fetch the updated record to return current state
        fetched = safe_supabase_query(lambda: supabase.table('patients').select('*').eq('id', patient_id).single().execute(), None, f"fetch patient {patient_id} after update")
        if fetched.get('success') and fetched.get('data'):
            return jsonify({"success": True, "data": fetched.get('data')}), 200

        # Fallback: return whatever Supabase returned
        return jsonify({"success": True, "data": res.get('data')}), 200

    except Exception as e:
        error_response = handle_supabase_error(e, "updating patient")
        return jsonify(error_response), 500

# ==================== APPOINTMENTS ENDPOINTS (SAFE VERSION) ====================

@healthcare_bp.route('/api/healthcare/appointments', methods=['GET'])
def get_appointments():
    """Get all appointments with filters (safe version)"""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500
        
        # Check if appointments table exists
        if not check_table_exists('appointments'):
            return jsonify({
                "success": True,
                "data": [],
                "count": 0,
                "message": "Appointments table doesn't exist yet"
            })
        
        # Get query parameters
        status = request.args.get('status')
        date = request.args.get('date')
        patient_id = request.args.get('patient_id')
        ngo_id = request.args.get('ngo_id')
        provider_id = request.args.get('provider_id')
        limit = min(int(request.args.get('limit', 50)), 500)
        offset = int(request.args.get('offset', 0))
        
        # Build query - start without joins
        query = supabase.table('appointments').select('*')
        
        # Apply filters
        if status and status != 'all':
            query = query.eq('status', status)
        
        if date:
            query = query.eq('appointment_date', date)
        
        if patient_id:
            query = query.eq('patient_id', patient_id)
        
        if ngo_id:
            query = query.eq('ngo_id', ngo_id)
        
        if provider_id:
            query = query.eq('healthcare_provider_id', provider_id)
        
        # Order and paginate
        query = query.order('appointment_date', desc=True).order('appointment_time', desc=True)
        query = query.range(offset, offset + limit - 1)
        
        # Execute query
        response = query.execute()
        appointments = response.data
        
        # Enrich data with related information if tables exist
        enriched_appointments = []
        for appointment in appointments:
            enriched = dict(appointment)
            
            # Add patient info if patients table exists
            if appointment.get('patient_id') and check_table_exists('patients'):
                try:
                    patient_result = supabase.table('patients').select('name, homeless_id, age, gender').eq('id', appointment['patient_id']).single().execute()
                    if patient_result.data:
                        enriched['patient'] = patient_result.data
                except:
                    enriched['patient'] = {'name': 'Unknown', 'homeless_id': 'N/A'}
            
            # Add provider info if providers table exists
            if appointment.get('healthcare_provider_id') and check_table_exists('healthcare_providers'):
                try:
                    provider_result = supabase.table('healthcare_providers').select('name, type').eq('id', appointment['healthcare_provider_id']).single().execute()
                    if provider_result.data:
                        enriched['healthcare_provider'] = provider_result.data
                except:
                    enriched['healthcare_provider'] = {'name': 'Unknown Provider'}
            
            # Add NGO info if NGOs table exists
            if appointment.get('ngo_id') and check_table_exists('ngos'):
                try:
                    ngo_result = supabase.table('ngos').select('name').eq('id', appointment['ngo_id']).single().execute()
                    if ngo_result.data:
                        enriched['ngo'] = ngo_result.data
                except:
                    enriched['ngo'] = {'name': 'Unknown NGO'}
            
            enriched_appointments.append(enriched)
        
        return jsonify({
            "success": True,
            "data": enriched_appointments,
            "count": len(enriched_appointments),
            "total": response.count if hasattr(response, 'count') else len(enriched_appointments),
            "note": "Some related data may be missing if tables don't exist"
        })
        
    except Exception as e:
        error_response = handle_supabase_error(e, "fetching appointments")
        return jsonify(error_response), 500


@healthcare_bp.route('/api/healthcare/providers', methods=['GET'])
def get_providers():
    """Return list of healthcare providers."""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        if not check_table_exists('healthcare_providers'):
            return jsonify({"success": True, "data": [], "count": 0, "message": "No providers table"})

        resp = supabase.table('healthcare_providers').select('*').order('name', desc=False).execute()
        data = getattr(resp, 'data', None) if resp is not None else None
        return jsonify({"success": True, "data": data, "count": len(data) if data else 0})
    except Exception as e:
        error_response = handle_supabase_error(e, "fetching providers")
        return jsonify(error_response), 500


@healthcare_bp.route('/api/healthcare/ngos', methods=['GET'])
def get_ngos():
    """Return list of NGOs (users with role='ngo')."""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        resp = supabase.table('users').select('id, name, email').eq('role', 'ngo').order('name', desc=False).execute()
        data = getattr(resp, 'data', None) if resp is not None else None
        return jsonify({"success": True, "data": data or [], "count": len(data) if data else 0})
    except Exception as e:
        error_response = handle_supabase_error(e, "fetching ngos")
        return jsonify(error_response), 500


@healthcare_bp.route('/api/healthcare/appointments/<appointment_id>/prescription', methods=['POST'])
def prescribe_for_appointment(appointment_id: str):
    """Doctor prescribes treatment for an appointment; creates treatment_history and notifies NGO."""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        # Check if treatment_history table exists
        if not check_table_exists('treatment_history'):
            return jsonify({
                "success": False, 
                "error": "Treatment history table doesn't exist. Please run the database setup SQL."
            }), 500

        data = request.json or {}
        diagnosis = data.get('diagnosis')
        prescription = data.get('prescription')
        ngo_id = data.get('ngo_id')  # optional override; otherwise use appointment.ngo_id

        if not diagnosis and not prescription:
            return jsonify({"success": False, "error": "diagnosis or prescription required"}), 400

        # Fetch appointment to get patient and ngo
        ap_resp = safe_supabase_query(lambda: supabase.table('appointments').select('*').eq('id', appointment_id).single().execute(), None, f"fetch appointment {appointment_id}")
        if not ap_resp.get('success') or not ap_resp.get('data'):
            return jsonify({"success": False, "error": "Appointment not found"}), 404

        ap = ap_resp.get('data')
        patient_id = ap.get('patient_id')
        ap_ngo = ap.get('ngo_id')

        # Validate patient_id exists
        if not patient_id:
            return jsonify({"success": False, "error": "Appointment has no associated patient"}), 400

        target_ngo = ngo_id or ap_ngo

        # Insert into treatment_history
        # Build the insert payload - DO NOT include healthcare_provider_id as it doesn't exist in the database
        th = {
            'appointment_id': appointment_id,
            'patient_id': patient_id,
            'prescription': prescription  # Required field
        }
        
        # Optional fields - only include if they have values (avoid None)
        if target_ngo:
            th['ngo_id'] = target_ngo
        if diagnosis:
            th['diagnosis'] = diagnosis
        if data.get('notes'):
            th['notes'] = data.get('notes')

        # Debug: print what we're inserting (without healthcare_provider_id)
        print(f"[DEBUG] Inserting treatment_history with fields: {list(th.keys())}")
        print(f"[DEBUG] Appointment ID: {appointment_id}")
        print(f"[DEBUG] Patient ID: {patient_id}")
        print(f"[DEBUG] Prescription: {prescription[:50] if prescription else 'None'}...")
        
        try:
            # Try using RPC function first (bypasses schema cache validation)
            # This function must be created in the database first
            try:
                rpc_params = {
                    'p_appointment_id': appointment_id,
                    'p_patient_id': str(patient_id),
                    'p_prescription': prescription
                }
                if target_ngo:
                    rpc_params['p_ngo_id'] = str(target_ngo)
                if diagnosis:
                    rpc_params['p_diagnosis'] = diagnosis
                if data.get('notes'):
                    rpc_params['p_notes'] = data.get('notes')
                
                print(f"[DEBUG] Attempting RPC insert_treatment_history with params: {list(rpc_params.keys())}")
                try:
                    rpc_result = safe_supabase_write(
                        lambda: supabase.rpc('insert_treatment_history', rpc_params).execute(),
                        'insert treatment history via RPC'
                    )
                except Exception as rpc_exception:
                    # RPC call itself failed (function doesn't exist or other error)
                    error_str = str(rpc_exception).lower()
                    print(f"[ERROR] RPC call exception: {rpc_exception}")
                    
                    if 'healthcare_provider_id' in error_str or 'schema cache' in error_str or 'PGRST204' in error_str:
                        # This shouldn't happen with RPC, but if it does, the function might not exist
                        raise Exception(f"RPC_FUNCTION_NOT_FOUND: The insert_treatment_history function does not exist. The schema cache error suggests the RPC function was not created. Please run create_insert_treatment_history_function.sql")
                    
                    raise Exception(f"RPC_CALL_FAILED: {rpc_exception}")
                
                if rpc_result.get('success') and rpc_result.get('data'):
                    print(f"[OK] Successfully inserted via RPC function")
                    created_data = rpc_result.get('data')
                    if isinstance(created_data, list) and created_data:
                        created = created_data[0]
                    elif isinstance(created_data, dict):
                        created = created_data
                    else:
                        created = None
                else:
                    # RPC function doesn't exist or failed
                    rpc_error_msg = rpc_result.get('error', 'Unknown RPC error')
                    rpc_error_str = str(rpc_error_msg).lower()
                    print(f"[ERROR] RPC function failed: {rpc_error_msg}")
                    
                    # Check for schema cache error in RPC response (means function doesn't exist or has wrong signature)
                    if 'healthcare_provider_id' in rpc_error_str and ('schema cache' in rpc_error_str or 'PGRST204' in rpc_error_str):
                        raise Exception(f"RPC_FUNCTION_NOT_FOUND: The insert_treatment_history function does not exist or has wrong signature. Please run create_insert_treatment_history_function.sql")
                    
                    # Check if function doesn't exist
                    if 'function' in rpc_error_str and ('does not exist' in rpc_error_str or 'not found' in rpc_error_str or 'PGRST116' in rpc_error_str):
                        raise Exception(f"RPC_FUNCTION_NOT_FOUND: The insert_treatment_history function does not exist in the database. Please run create_insert_treatment_history_function.sql")
                    
                    # For any other RPC error, raise it (don't try direct insert)
                    raise Exception(f"RPC_ERROR: {rpc_error_msg}")
                    
            except Exception as rpc_error:
                error_str = str(rpc_error).lower()
                print(f"[WARN] RPC function failed: {rpc_error}")
                
                # If RPC function doesn't exist, don't try direct insert (will fail with schema cache error)
                if 'function' in error_str and ('does not exist' in error_str or 'not found' in error_str):
                    print(f"[ERROR] RPC function 'insert_treatment_history' does not exist in database")
                    return jsonify({
                        "success": False, 
                        "error": "Database function not found. Please run the SQL scripts to fix this:",
                        "solution": "Run these SQL scripts in Supabase SQL Editor (in order):",
                        "steps": [
                            "1. Open Supabase Dashboard → SQL Editor",
                            "2. Run: docs/remove_healthcare_provider_id_from_treatment_history.sql",
                            "3. Run: docs/create_insert_treatment_history_function.sql",
                            "4. Wait 10-30 seconds",
                            "5. Try saving prescription again"
                        ],
                        "sql_files": [
                            "docs/remove_healthcare_provider_id_from_treatment_history.sql",
                            "docs/create_insert_treatment_history_function.sql"
                        ],
                        "note": "The RPC function bypasses schema cache validation and is required for prescriptions to work."
                    }), 500
                
                # DO NOT fall back to direct insert - it will always fail with schema cache error
                # The RPC function is REQUIRED to bypass schema cache validation
                print(f"[ERROR] RPC function failed - cannot use direct insert (schema cache will fail)")
                return jsonify({
                    "success": False, 
                    "error": "RPC function failed. The insert_treatment_history function is required.",
                    "solution": "Please run the SQL scripts in Supabase SQL Editor (REQUIRED):",
                    "steps": [
                        "1. Open Supabase Dashboard → SQL Editor",
                        "2. Run: docs/remove_healthcare_provider_id_from_treatment_history.sql",
                        "3. Run: docs/create_insert_treatment_history_function.sql (CRITICAL - this creates the RPC function)",
                        "4. Wait 10-30 seconds for cache refresh",
                        "5. Try saving prescription again"
                    ],
                    "sql_files": [
                        "docs/remove_healthcare_provider_id_from_treatment_history.sql",
                        "docs/create_insert_treatment_history_function.sql"
                    ],
                    "why_required": "Direct insert fails due to schema cache validation. The RPC function bypasses this validation and is the only way to insert prescriptions.",
                    "rpc_error": str(rpc_error)
                }), 500
                    
        except Exception as insert_exception:
            error_str = str(insert_exception).lower()
            error_msg = str(insert_exception)
            print(f"[ERROR] Exception during treatment_history insert: {insert_exception}")
            import traceback
            traceback.print_exc()
            
            # Check for schema cache error (shouldn't happen if RPC is used, but just in case)
            if 'healthcare_provider_id' in error_str and ('schema cache' in error_str or 'PGRST204' in error_str):
                return jsonify({
                    "success": False, 
                    "error": "Schema cache validation error. The RPC function is required.",
                    "solution": "Please run the SQL scripts in Supabase SQL Editor:",
                    "steps": [
                        "1. Run: docs/remove_healthcare_provider_id_from_treatment_history.sql",
                        "2. Run: docs/create_insert_treatment_history_function.sql (REQUIRED - creates RPC function)",
                        "3. Wait 10-30 seconds",
                        "4. Try again"
                    ],
                    "sql_scripts": [
                        "docs/remove_healthcare_provider_id_from_treatment_history.sql",
                        "docs/create_insert_treatment_history_function.sql"
                    ],
                    "note": "The RPC function bypasses schema cache validation. Without it, prescriptions cannot be saved."
                }), 500
            
            # Check if it's an RPC function not found error
            if 'rpc_function_not_found' in error_str or 'function' in error_str:
                return jsonify({
                    "success": False, 
                    "error": "RPC function 'insert_treatment_history' not found in database.",
                    "solution": "Please run the SQL script to create the function:",
                    "steps": [
                        "1. Open Supabase Dashboard → SQL Editor",
                        "2. Run: docs/create_insert_treatment_history_function.sql",
                        "3. Wait 10-30 seconds",
                        "4. Try again"
                    ],
                    "sql_file": "docs/create_insert_treatment_history_function.sql"
                }), 500
            
            return jsonify({
                "success": False, 
                "error": f"Exception during insert: {error_msg}",
                "note": "If you see schema cache errors, you must run the SQL scripts to create the RPC function."
            }), 500

        created = None
        d = create_th.get('data')
        if isinstance(d, list) and d:
            created = d[0]
        elif isinstance(d, dict) and d:
            created = d

        # Update appointment status to completed
        safe_supabase_write(lambda: supabase.table('appointments').update({'status': 'completed', 'updated_at': datetime.now().isoformat()}).eq('id', appointment_id).execute(), 'update appointment status after prescription')

        # Create ngo notification if ngo specified
        notif = None
        if target_ngo:
            message = f"Prescription for appointment {appointment_id}: {diagnosis or ''} -- {prescription or ''}"
            notif_payload = {
                'ngo_id': target_ngo,
                'appointment_id': appointment_id,
                'treatment_id': created.get('id') if created else None,
                'message': message
            }
            notif_res = safe_supabase_write(lambda: supabase.table('ngo_notifications').insert(notif_payload).execute(), 'insert ngo notification')
            if notif_res.get('success'):
                notif = notif_res.get('data')

        return jsonify({"success": True, "treatment_history": created, "notification": notif}), 201

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Exception in prescribe_for_appointment: {str(e)}")
        print(f"[ERROR] Traceback:\n{error_trace}")
        error_response = handle_supabase_error(e, "creating prescription")
        # Add traceback for debugging
        if isinstance(error_response, dict):
            error_response['traceback'] = error_trace
        return jsonify(error_response), 500


@healthcare_bp.route('/api/healthcare/treatment-history', methods=['GET'])
def get_treatment_history():
    """Get treatment history with optional filters"""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500
        
        # Check if treatment_history table exists
        if not check_table_exists('treatment_history'):
            return jsonify({
                "success": True,
                "data": [],
                "count": 0,
                "message": "Treatment history table doesn't exist yet"
            })
        
        # Get query parameters
        patient_id = request.args.get('patient_id')
        appointment_id = request.args.get('appointment_id')
        ngo_id = request.args.get('ngo_id')
        limit = min(int(request.args.get('limit', 100)), 500)
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = supabase.table('treatment_history').select('*')
        
        # Apply filters
        if patient_id:
            query = query.eq('patient_id', patient_id)
        
        if appointment_id:
            query = query.eq('appointment_id', appointment_id)
        
        if ngo_id:
            query = query.eq('ngo_id', ngo_id)
        
        # Order by creation date (most recent first)
        query = query.order('created_at', desc=True)
        query = query.range(offset, offset + limit - 1)
        
        # Execute query
        response = query.execute()
        treatments = response.data
        
        # Enrich data with related information
        enriched_treatments = []
        for treatment in treatments:
            enriched = dict(treatment)
            
            # Add patient info if patients table exists
            if treatment.get('patient_id') and check_table_exists('patients'):
                try:
                    patient_result = supabase.table('patients').select('name, homeless_id').eq('id', treatment['patient_id']).single().execute()
                    if patient_result.data:
                        enriched['patient'] = patient_result.data
                except:
                    enriched['patient'] = {'name': 'Unknown', 'homeless_id': 'N/A'}
            
            # Note: healthcare_provider_id has been removed from treatment_history table
            # Provider info is no longer stored in treatment history
            enriched['healthcare_provider'] = {'name': 'Healthcare Provider'}
            
            enriched_treatments.append(enriched)
        
        return jsonify({
            "success": True,
            "data": enriched_treatments,
            "count": len(enriched_treatments),
            "total": response.count if hasattr(response, 'count') else len(enriched_treatments)
        })
        
    except Exception as e:
        error_response = handle_supabase_error(e, "fetching treatment history")
        return jsonify(error_response), 500


@healthcare_bp.route('/api/healthcare/sample-data', methods=['POST'])
def create_sample_data():
    """Create sample NGOs, patients and appointments for testing.

    This endpoint is idempotent: it will not duplicate records with the
    same external identifiers (homeless_id or email). It requires the
    relevant tables to exist in the database.
    """
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        missing = []
        for t in ['users', 'patients', 'appointments']:
            if not check_table_exists(t):
                missing.append(t)
        if missing:
            return jsonify({"success": False, "error": f"Missing tables: {', '.join(missing)}. Run database setup."}), 400

        # Create sample NGO user if not exists
        ngos_to_create = [
            {'email': 'sample_ngo@bridgecare.org', 'name': 'Sample NGO', 'role': 'ngo'},
        ]
        created_ngos = []
        for ngo in ngos_to_create:
            # check by email
            q = safe_supabase_query(lambda: supabase.table('users').select('*').eq('email', ngo['email']).single().execute(), None, 'check ngo')
            if q.get('success') and q.get('data'):
                created_ngos.append(q.get('data'))
            else:
                ins = safe_supabase_write(lambda: supabase.table('users').insert(ngo).execute(), 'insert ngo')
                if ins.get('success'):
                    d = ins.get('data')
                    created_ngos.append(d[0] if isinstance(d, list) else d)

        # Create sample patients
        sample_patients = [
            {'name': 'John Doe', 'homeless_id': 'HM100', 'age': 45, 'gender': 'male'},
            {'name': 'Jane Smith', 'homeless_id': 'HM101', 'age': 36, 'gender': 'female'},
        ]
        created_patients = []
        for p in sample_patients:
            q = safe_supabase_query(lambda: supabase.table('patients').select('*').eq('homeless_id', p['homeless_id']).single().execute(), None, 'check patient')
            if q.get('success') and q.get('data'):
                created_patients.append(q.get('data'))
            else:
                ins = safe_supabase_write(lambda: supabase.table('patients').insert({**p, 'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()}).execute(), 'insert patient')
                if ins.get('success'):
                    d = ins.get('data')
                    created_patients.append(d[0] if isinstance(d, list) else d)

        # Create sample appointments (booked by the above NGO)
        created_appointments = []
        ngo_id = created_ngos[0]['id'] if created_ngos else None
        for idx, pat in enumerate(created_patients, start=1):
            # generate appointment id
            appointment_id = f"APT-SAMPLE-{idx}"
            # check existing by id
            q = safe_supabase_query(lambda: supabase.table('appointments').select('*').eq('id', appointment_id).single().execute(), None, 'check appointment')
            if q.get('success') and q.get('data'):
                created_appointments.append(q.get('data'))
                continue

            appointment_data = {
                'id': appointment_id,
                'patient_id': pat.get('id'),
                'ngo_id': ngo_id,
                'appointment_date': (date.today()).isoformat(),
                'appointment_time': f"0{8+idx}:00" if idx < 3 else '10:00',
                'status': 'scheduled',
                'booking_notes': 'Booked via NGO dashboard (sample)',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            ins = safe_supabase_write(lambda: supabase.table('appointments').insert(appointment_data).execute(), 'insert sample appointment')
            if ins.get('success'):
                d = ins.get('data')
                created_appointments.append(d[0] if isinstance(d, list) else d)

        return jsonify({
            'success': True,
            'ngos': created_ngos,
            'patients': created_patients,
            'appointments': created_appointments
        }), 201

    except Exception as e:
        error_response = handle_supabase_error(e, 'creating sample data')
        return jsonify(error_response), 500


@healthcare_bp.route('/api/healthcare/providers', methods=['POST'])
def create_provider():
    """Create a new healthcare provider (simple endpoint for admin/testing)."""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        data = request.json or {}
        if not data.get('name'):
            return jsonify({"success": False, "error": "Provider name is required"}), 400

        provider = {
            'name': data.get('name'),
            'type': data.get('type'),
            'address': data.get('address'),
            'contact_number': data.get('contact_number'),
            'email': data.get('email'),
            'services': data.get('services')
        }

        res = safe_supabase_write(lambda: supabase.table('healthcare_providers').insert(provider).execute(), 'create provider')
        if not res.get('success'):
            return jsonify({"success": False, "error": res.get('error')}), 500

        # return created provider (if available)
        created = None
        d = res.get('data')
        if isinstance(d, list) and d:
            created = d[0]
        elif isinstance(d, dict) and d:
            created = d

        return jsonify({"success": True, "data": created}), 201

    except Exception as e:
        error_response = handle_supabase_error(e, "creating provider")
        return jsonify(error_response), 500

@healthcare_bp.route('/api/healthcare/appointments', methods=['POST'])
def create_appointment():
    """Create a new appointment (safe version)"""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500
        
        data = request.json
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided in request",
                "code": "NO_DATA"
            }), 400
        
        # Validate required fields
        # healthcare_provider_id is optional now (providers removed from UI)
        validation_error = validate_required_fields(data, [
            'patient_id', 'appointment_date', 'appointment_time'
        ])
        if validation_error:
            return jsonify(validation_error), 400
        
        # Additional validation - ensure patient_id is not empty
        patient_id = data.get('patient_id')
        if not patient_id or (isinstance(patient_id, str) and patient_id.strip() == ''):
            return jsonify({
                "success": False,
                "error": "Patient ID cannot be empty",
                "code": "INVALID_PATIENT_ID"
            }), 400
        
        # Check if required tables exist
        if not check_table_exists('patients'):
            return jsonify({
                "success": False,
                "error": "Patients table doesn't exist. Please create it first.",
                "code": "TABLE_NOT_FOUND"
            }), 400
        
        # Check if appointments table exists
        if not check_table_exists('appointments'):
            return jsonify({
                "success": False,
                "error": "Appointments table doesn't exist. Please create it first.",
                "code": "TABLE_NOT_FOUND"
            }), 400
        
        # Generate appointment ID - use timestamp to ensure uniqueness
        appointment_id = None
        try:
            # Try to get count for sequential ID
            count_response = supabase.table('appointments').select('id', count='exact').execute()
            count = count_response.count if hasattr(count_response, 'count') else (len(count_response.data) if hasattr(count_response, 'data') and count_response.data else 0)
            appointment_id = f"APT{str(count + 1).zfill(4)}"
        except Exception as count_error:
            # Fallback to timestamp-based ID if count fails
            print(f"Warning: Could not get appointment count: {count_error}")
            appointment_id = f"APT{int(datetime.now().timestamp())}"
        
        if not appointment_id:
            appointment_id = f"APT{int(datetime.now().timestamp())}"
        
        # Prepare appointment data (without healthcare_provider_id as it's removed from schema)
        appointment_data = {
            'id': appointment_id,
            'patient_id': data['patient_id'],
            'appointment_date': data['appointment_date'],
            'appointment_time': data['appointment_time'],
            'status': data.get('status', 'scheduled'),
            'priority': data.get('priority', 'normal'),
            'symptoms': data.get('symptoms'),
            'referred_by': data.get('referred_by'),
            'booking_notes': data.get('booking_notes'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Add optional fields if provided - validate foreign keys exist
        if 'ngo_id' in data and data['ngo_id']:
            ngo_id = data['ngo_id']
            # Validate ngo_id exists in users table (appointments.ngo_id references users.id)
            # Check both 'users' and 'ngos' tables in case schema differs
            ngo_valid = False
            try:
                # Try users table first (as per schema)
                if check_table_exists('users'):
                    user_check = safe_supabase_query(
                        lambda: supabase.table('users').select('id').eq('id', ngo_id).limit(1).execute(),
                        None, 'check ngo_id in users'
                    )
                    if user_check.get('success') and user_check.get('data'):
                        ngo_valid = True
                
                # If not found in users, try ngos table (in case actual DB differs from schema)
                if not ngo_valid and check_table_exists('ngos'):
                    ngo_check = safe_supabase_query(
                        lambda: supabase.table('ngos').select('id').eq('id', ngo_id).limit(1).execute(),
                        None, 'check ngo_id in ngos'
                    )
                    if ngo_check.get('success') and ngo_check.get('data'):
                        ngo_valid = True
            except Exception as ngo_check_error:
                print(f"[WARN] Error checking ngo_id: {ngo_check_error}")
            
            if ngo_valid:
                appointment_data['ngo_id'] = ngo_id
            else:
                print(f"[WARN] Invalid ngo_id {ngo_id} - not found in users/ngos table. Skipping ngo_id.")
                # Don't add invalid ngo_id - leave it as NULL
        
        if 'volunteer_id' in data and data['volunteer_id']:
            volunteer_id = data['volunteer_id']
            # Validate volunteer_id exists in users table
            try:
                if check_table_exists('users'):
                    volunteer_check = safe_supabase_query(
                        lambda: supabase.table('users').select('id').eq('id', volunteer_id).limit(1).execute(),
                        None, 'check volunteer_id'
                    )
                    if volunteer_check.get('success') and volunteer_check.get('data'):
                        appointment_data['volunteer_id'] = volunteer_id
                    else:
                        print(f"[WARN] Invalid volunteer_id {volunteer_id} - not found. Skipping volunteer_id.")
            except Exception as vol_check_error:
                print(f"[WARN] Error checking volunteer_id: {vol_check_error}")
        
        # Insert appointment (use safe writer to capture errors)
        print(f"[DEBUG] Attempting to insert appointment with data: {appointment_data}")
        print(f"[DEBUG] Appointment ID: {appointment_id}")
        print(f"[DEBUG] Patient ID: {data['patient_id']}")
        print(f"[DEBUG] Date: {data['appointment_date']}, Time: {data['appointment_time']}")
        
        try:
            insert_result = safe_supabase_write(lambda: supabase.table('appointments').insert(appointment_data).execute(), "insert appointment")
        except Exception as insert_exception:
            print(f"[ERROR] Exception during insert: {insert_exception}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False, 
                "error": f"Exception during insert: {str(insert_exception)}"
            }), 500

        debug = request.args.get('debug') == '1'
        if not insert_result.get('success'):
            error_msg = insert_result.get('error', 'Unknown error')
            print(f"[ERROR] Failed to insert appointment: {error_msg}")
            print(f"[ERROR] Raw result: {insert_result.get('raw')}")
            
            # Try to provide more helpful error messages
            error_str = str(error_msg).lower()
            if 'column' in error_str and 'does not exist' in error_str:
                error_msg = f"Database schema mismatch: {error_msg}. Please check if the appointments table has the correct columns."
            elif 'foreign key' in error_str:
                # Check if it's ngo_id or volunteer_id foreign key error
                if 'ngo_id' in error_str:
                    error_msg = f"Invalid NGO ID: {error_msg}. The NGO ID does not exist in the users/ngos table. Please provide a valid NGO ID or leave it empty."
                elif 'volunteer_id' in error_str:
                    error_msg = f"Invalid Volunteer ID: {error_msg}. The volunteer ID does not exist in the users table. Please provide a valid volunteer ID or leave it empty."
                elif 'patient_id' in error_str:
                    error_msg = f"Invalid Patient ID: {error_msg}. Please ensure the patient exists in the database."
                else:
                    error_msg = f"Foreign key constraint violation: {error_msg}. Please check that all referenced IDs exist in their respective tables."
            elif 'permission' in error_str or 'policy' in error_str or 'rls' in error_str:
                error_msg = f"Permission denied: {error_msg}. Please check Row-Level Security (RLS) policies or use SERVICE ROLE key."
            
            payload = {"success": False, "error": f"Failed to create appointment: {error_msg}"}
            if debug:
                payload['raw'] = repr(insert_result.get('raw'))
            return jsonify(payload), 500

        # Try to update patient's last visit date (if patients table exists)
        try:
            update_result = safe_supabase_write(lambda: supabase.table('patients').update({
                'last_visit_date': data['appointment_date'],
                'updated_at': datetime.now().isoformat()
            }).eq('id', data['patient_id']).execute(), "update patient last visit")

            if not update_result.get('success'):
                print(f"⚠️ Could not update patient last visit: {update_result.get('error')}")
        except Exception as update_error:
            print(f"⚠️ Could not update patient last visit: {update_error}")
        
        # insert_result may contain data as list or dict under 'data'
        created_data = None
        d = insert_result.get('data')
        if isinstance(d, list) and d:
            created_data = d[0]
        elif isinstance(d, dict) and d:
            created_data = d

        # If Supabase didn't return the created appointment, fetch by appointment_id
        if not created_data:
            fetch = safe_supabase_query(lambda: supabase.table('appointments').select('*').eq('id', appointment_id).single().execute(), None, "fetch appointment after insert")
            if fetch.get('success') and fetch.get('data'):
                created_data = fetch.get('data')

        payload = {
            "success": True,
            "data": created_data,
            "message": "Appointment created successfully"
        }
        if debug:
            payload['raw'] = repr(insert_result.get('raw'))
        return jsonify(payload), 201
        
    except Exception as e:
        error_response = handle_supabase_error(e, "creating appointment")
        return jsonify(error_response), 500


@healthcare_bp.route('/api/healthcare/appointments/<appointment_id>/status', methods=['PUT'])
def update_appointment_status(appointment_id: str):
    """Update appointment status"""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        data = request.json or {}
        new_status = data.get('status')

        if not new_status:
            return jsonify({"success": False, "error": "Status is required"}), 400

        res = safe_supabase_write(lambda: supabase.table('appointments').update({
            'status': new_status,
            'updated_at': datetime.now().isoformat()
        }).eq('id', appointment_id).execute(), f"update appointment status {appointment_id}")

        if not res.get('success'):
            return jsonify({"success": False, "error": res.get('error')}), 500

        # Fetch the appointment to return its current state
        fetched = safe_supabase_query(lambda: supabase.table('appointments').select('*').eq('id', appointment_id).single().execute(), None, f"fetch appointment {appointment_id} after status update")
        if fetched.get('success') and fetched.get('data'):
            return jsonify({"success": True, "message": f"Appointment status updated to '{new_status}'", "data": fetched.get('data')}), 200

        return jsonify({"success": True, "message": f"Appointment status updated to '{new_status}'", "data": res.get('data')}), 200

    except Exception as e:
        error_response = handle_supabase_error(e, "updating appointment status")
        return jsonify(error_response), 500


@healthcare_bp.route('/api/healthcare/appointments/<appointment_id>', methods=['PUT'])
def update_appointment(appointment_id: str):
    """Update an existing appointment record (generic fields)."""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        data = request.json or {}
        if not data:
            return jsonify({"success": False, "error": "No update data provided"}), 400

        # Allow only specific fields to be updated (healthcare_provider_id removed from schema)
        allowed = ['appointment_date', 'appointment_time', 'status', 'priority', 'symptoms', 'referred_by', 'booking_notes', 'ngo_id', 'volunteer_id', 'patient_id']
        update_payload = {k: v for k, v in data.items() if k in allowed}
        update_payload['updated_at'] = datetime.now().isoformat()

        res = safe_supabase_write(lambda: supabase.table('appointments').update(update_payload).eq('id', appointment_id).execute(), f"update appointment {appointment_id}")
        if not res.get('success'):
            return jsonify({"success": False, "error": res.get('error')}), 500

        fetched = safe_supabase_query(lambda: supabase.table('appointments').select('*').eq('id', appointment_id).single().execute(), None, f"fetch appointment {appointment_id} after update")
        if fetched.get('success') and fetched.get('data'):
            return jsonify({"success": True, "data": fetched.get('data')}), 200

        return jsonify({"success": True, "data": res.get('data')}), 200

    except Exception as e:
        error_response = handle_supabase_error(e, "updating appointment")
        return jsonify(error_response), 500


@healthcare_bp.route('/api/healthcare/appointments/<appointment_id>', methods=['DELETE'])
def delete_appointment(appointment_id: str):
    """Delete an appointment by id."""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500

        res = safe_supabase_write(lambda: supabase.table('appointments').delete().eq('id', appointment_id).execute(), f"delete appointment {appointment_id}")
        if not res.get('success'):
            return jsonify({"success": False, "error": res.get('error')}), 500

        return jsonify({"success": True, "message": "Appointment deleted"}), 200

    except Exception as e:
        error_response = handle_supabase_error(e, "deleting appointment")
        return jsonify(error_response), 500

# ==================== SIMPLE DASHBOARD ENDPOINTS ====================

@healthcare_bp.route('/api/healthcare/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics (safe version)"""
    try:
        if not supabase:
            return jsonify({
                "success": True,
                "data": {
                    "today_appointments": 0,
                    "total_patients": 0,
                    "active_providers": 0,
                    "completed_treatments": 0,
                    "pending_appointments": 0
                },
                "note": "Database not connected"
            })
        
        today = date.today().isoformat()
        
        # Initialize counts
        stats = {
            "today_appointments": 0,
            "total_patients": 0,
            "active_providers": 0,
            "completed_treatments": 0,
            "pending_appointments": 0
        }
        
        # Get today's appointments (if table exists)
        if check_table_exists('appointments'):
            try:
                today_result = supabase.table('appointments').select('id', count='exact').eq('appointment_date', today).execute()
                stats["today_appointments"] = today_result.count if hasattr(today_result, 'count') else len(today_result.data)
                
                pending_result = supabase.table('appointments').select('id', count='exact').eq('status', 'scheduled').execute()
                stats["pending_appointments"] = pending_result.count if hasattr(pending_result, 'count') else len(pending_result.data)
                
                completed_result = supabase.table('appointments').select('id', count='exact').eq('status', 'completed').execute()
                stats["completed_treatments"] = completed_result.count if hasattr(completed_result, 'count') else len(completed_result.data)
            except:
                pass
        
        # Get total patients (if table exists)
        if check_table_exists('patients'):
            try:
                patients_result = supabase.table('patients').select('id', count='exact').eq('is_active', True).execute()
                stats["total_patients"] = patients_result.count if hasattr(patients_result, 'count') else len(patients_result.data)
            except:
                pass
        
        # Get active providers (if table exists)
        if check_table_exists('healthcare_providers'):
            try:
                providers_result = supabase.table('healthcare_providers').select('id', count='exact').eq('is_verified', True).execute()
                stats["active_providers"] = providers_result.count if hasattr(providers_result, 'count') else len(providers_result.data)
            except:
                pass
        
        return jsonify({
            "success": True,
            "data": stats,
            "database_status": get_table_status()
        })
        
    except Exception as e:
        error_response = handle_supabase_error(e, "fetching dashboard statistics")
        return jsonify(error_response), 500

# ==================== SIMPLE DATA ENTRY ENDPOINTS ====================

@healthcare_bp.route('/api/healthcare/initialize-sample-data', methods=['POST'])
def initialize_sample_data():
    """Initialize sample data for testing"""
    try:
        if not supabase:
            return jsonify({"success": False, "error": "Database not connected"}), 500
        
        # Check which tables exist
        table_status = get_table_status()
        
        results = []
        
        # Create sample NGOs if table exists
        if table_status.get('ngos', False):
            sample_ngos = [
                {"name": "Hope NGO", "contact_person": "John Smith", "contact_number": "+1234567890", "email": "hope@example.com"},
                {"name": "Shelter Care", "contact_person": "Maria Garcia", "contact_number": "+1234567891", "email": "shelter@example.com"},
                {"name": "Street Aid", "contact_person": "Robert Johnson", "contact_number": "+1234567892", "email": "street@example.com"}
            ]
            
            for ngo in sample_ngos:
                res = safe_supabase_write(lambda ngo=ngo: supabase.table('ngos').insert(ngo).execute(), f"insert ngo {ngo.get('name')}")
                if res.get('success'):
                    results.append(f"Created NGO: {ngo['name']}")
                else:
                    results.append(f"Failed to create NGO {ngo['name']}: {res.get('error')}")
        
        # Create sample patients if table exists
        if table_status.get('patients', False):
            sample_patients = [
                {"name": "John Doe", "age": 45, "gender": "male", "homeless_id": "HM001", "contact_number": "+1111111111"},
                {"name": "Mary Johnson", "age": 32, "gender": "female", "homeless_id": "HM002", "contact_number": "+1111111112"},
                {"name": "Robert Smith", "age": 58, "gender": "male", "homeless_id": "HM003", "contact_number": "+1111111113"}
            ]
            
            for patient in sample_patients:
                res = safe_supabase_write(lambda patient=patient: supabase.table('patients').insert(patient).execute(), f"insert patient {patient.get('name')}")
                if res.get('success'):
                    results.append(f"Created patient: {patient['name']}")
                else:
                    results.append(f"Failed to create patient {patient['name']}: {res.get('error')}")
        
        return jsonify({
            "success": True,
            "results": results,
            "tables_status": table_status,
            "message": "Sample data initialization attempted"
        })
        
    except Exception as e:
        error_response = handle_supabase_error(e, "initializing sample data")
        return jsonify(error_response), 500

# ==================== ERROR HANDLERS ====================

@healthcare_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": [
            "GET  /api/health/status",
            "GET  /api/healthcare/patients",
            "GET  /api/healthcare/appointments",
            "POST /api/healthcare/appointments",
            "GET  /api/healthcare/dashboard/stats",
            "POST /api/healthcare/database/setup"
        ]
    }), 404
