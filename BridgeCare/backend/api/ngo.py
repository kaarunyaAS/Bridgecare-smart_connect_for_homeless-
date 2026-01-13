from datetime import datetime
from typing import Dict, Any, List

from flask import Blueprint, jsonify, request, session

from backend.supabase_client import supabase, safe_supabase_query, safe_supabase_write
import uuid

ngo_bp = Blueprint("ngo_bp", __name__, url_prefix="/api/ngo")


# ---------------------------- Helpers ---------------------------- #
def _require_ngo():
    if "user_id" not in session or session.get("role") != "ngo":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return None


def _table_exists(name: str) -> bool:
    try:
        supabase.table(name).select("id").limit(1).execute()
        return True
    except Exception:
        return False


def _safe_count(table: str, **filters) -> int:
    if not _table_exists(table):
        return 0
    try:
        query = supabase.table(table).select("id", count="exact")
        for key, val in filters.items():
            query = query.eq(key, val)
        resp = query.execute()
        return getattr(resp, "count", None) or (len(getattr(resp, "data", None) or []))
    except Exception:
        return 0


def _count_table(table: str, filters: Dict[str, Any] = None) -> int:
    """Reliable count using count=exact with optional filters; falls back to 0 on errors."""
    if not _table_exists(table):
        return 0
    try:
        filters = filters or {}
        query = supabase.table(table).select("id", count="exact")
        for k, v in filters.items():
            query = query.eq(k, v)
        resp = query.execute()
        if hasattr(resp, "count") and resp.count is not None:
            return resp.count
        data = getattr(resp, "data", None)
        return len(data) if data else 0
    except Exception:
        return 0


def _insert_with_schema_fallback(table: str, payload: Dict[str, Any], operation: str):
    """Attempt insert; on schema cache missing-column errors, drop the column and retry once."""
    res = safe_supabase_write(lambda: supabase.table(table).insert(payload).execute(), operation)
    if res.get("success"):
        return res

    err = str(res.get("error", "")).lower()
    # Handle schema cache missing column errors (PGRST204)
    if "could not find the" in err and "in the schema cache" in err:
        # Try to detect column name between quotes if present
        col = None
        try:
            # error text example: "Could not find the 'ngo_id' column of 'homeless_people'..."
            import re
            m = re.search(r"'([a-zA-Z0-9_]+)'\s+column", err)
            if m:
                col = m.group(1)
        except Exception:
            col = None
        if col and col in payload:
            payload = {k: v for k, v in payload.items() if k != col}
            return safe_supabase_write(lambda: supabase.table(table).insert(payload).execute(), f"{operation}-retry-no-{col}")
    return res


def _describe_table(table: str) -> Dict[str, Any]:
    """Return basic table info: exists flag and a sample of columns (best-effort)."""
    exists = _table_exists(table)
    if not exists:
        return {"exists": False, "columns": []}
    try:
        resp = supabase.table(table).select("*").limit(1).execute()
        rows = getattr(resp, "data", None) or []
        cols = list(rows[0].keys()) if rows else []
        return {"exists": True, "columns": cols}
    except Exception as e:
        return {"exists": True, "columns": [], "error": str(e)}


# ---------------------------- Health & Summary ---------------------------- #
@ngo_bp.route("/health", methods=["GET"])
def health():
    auth_err = _require_ngo()
    if auth_err:
        return auth_err

    tables = ["homeless_people", "patients", "volunteer_data", "donations", "meal_requests", "appointments"]
    status = {t: _table_exists(t) for t in tables}
    return jsonify({"success": True, "tables": status, "timestamp": datetime.utcnow().isoformat()})


@ngo_bp.route("/summary", methods=["GET"])
def summary():
    # Allow summary even when not logged in; scope to NGO when session exists
    ngo_id = session.get("user_id") if "user_id" in session else None
    # Counts prefer ngo_id filter when available, otherwise fall back to all rows
    people_filters = {"ngo_id": ngo_id} if ngo_id else {}
    appt_filters = {"status": "scheduled"}
    if ngo_id:
        appt_filters["ngo_id"] = ngo_id

    data = {
        "homeless_count": _count_table("homeless_people"),
        "people_count": _count_table("patients", people_filters),
        "volunteer_count": _count_table("users", {"role": "volunteer"}),
        "open_meals": _count_table("donations", {"status": "available"}),
        "upcoming_appointments": _count_table("appointments", appt_filters),
    }
    return jsonify({"success": True, "data": data})


@ngo_bp.route("/schema-check", methods=["GET"])
def schema_check():
    """Report presence and sample columns for key NGO tables to debug schema cache issues."""
    auth_err = _require_ngo()
    if auth_err:
        return auth_err

    tables = ["homeless_people", "patients", "volunteer_data", "donations", "meal_requests", "appointments", "users", "ngos"]
    info = {t: _describe_table(t) for t in tables}
    return jsonify({"success": True, "tables": info, "timestamp": datetime.utcnow().isoformat()})


# ---------------------------- Homeless People ---------------------------- #
@ngo_bp.route("/homeless", methods=["GET", "POST"])
def homeless():
    auth_err = _require_ngo()
    if auth_err and request.method != "GET":
        return auth_err

    if not _table_exists("homeless_people"):
        return jsonify({"success": True, "data": [], "message": "homeless_people table missing. See docs/create_ngo_dashboard_tables.sql"}), 200

    if request.method == "GET":
        limit = min(int(request.args.get("limit", 50)), 200)
        resp = safe_supabase_query(
            lambda: supabase.table("homeless_people").select("*").order("created_at", desc=True).limit(limit).execute(),
            [],
            "list homeless_people",
        )
        data = resp.get("data", []) or []
        if not data:
            data = [
                {"id": "SAMPLE-HM-1", "name": "Demo Person A", "location": "Central Park", "health_status": "mild fever", "created_at": datetime.utcnow().isoformat()},
                {"id": "SAMPLE-HM-2", "name": "Demo Person B", "location": "Market Street", "health_status": "injury dressing", "created_at": datetime.utcnow().isoformat()},
            ]
        return jsonify({"success": True, "data": data})

    payload = request.json or {}
    age_val = payload.get("age")
    try:
        age_val = int(age_val) if age_val not in (None, "", []) else None
    except Exception:
        age_val = None

    entry = {
        "ngo_id": session.get("user_id"),
        "name": payload.get("name"),
        "age": age_val,
        "gender": payload.get("gender"),
        "location": payload.get("location"),
        "health_status": payload.get("health_status"),
        "notes": payload.get("notes"),
        "created_at": datetime.utcnow().isoformat(),
    }
    result = _insert_with_schema_fallback("homeless_people", entry, "insert homeless")
    status = 201 if result.get("success") else 400
    return jsonify({"success": result.get("success"), "data": result.get("data"), "error": result.get("error")}), status


# ---------------------------- People (Patients) ---------------------------- #
@ngo_bp.route("/people", methods=["GET", "POST"])
def people():
    auth_err = _require_ngo()
    if auth_err and request.method != "GET":
        return auth_err

    if not _table_exists("patients"):
        return jsonify({
            "success": False,
            "error": "patients table missing. Create it first (see docs/create_ngo_dashboard_tables.sql)."
        }), 400

    ngo_id = session.get("user_id")

    if request.method == "GET":
        limit = min(int(request.args.get("limit", 100)), 300)
        def _query():
            q = supabase.table("patients").select("*").order("created_at", desc=True)
            if ngo_id:
                q = q.eq("ngo_id", ngo_id)
            return q.limit(limit).execute()

        resp = safe_supabase_query(_query, [], "list patients")
        data = resp.get("data", []) or []
        if not data:
            data = [
                {"id": "SAMPLE-PAT-1", "name": "Ravi Kumar", "homeless_id": "HM-DEMO-1", "age": 42, "gender": "male", "contact_number": "+1 555 3333"},
                {"id": "SAMPLE-PAT-2", "name": "Meena Devi", "homeless_id": "HM-DEMO-2", "age": 35, "gender": "female", "contact_number": "+1 555 4444"},
            ]
        return jsonify({"success": True, "data": data})

    payload = request.json or {}
    if not payload.get("name") or not payload.get("homeless_id"):
        return jsonify({"success": False, "error": "name and homeless_id are required"}), 400

    age_val = payload.get("age")
    try:
        age_val = int(age_val) if age_val not in (None, "", []) else None
    except Exception:
        age_val = None

    person = {
        "name": payload.get("name"),
        "homeless_id": payload.get("homeless_id"),
        "age": age_val,
        "gender": payload.get("gender"),
        "ngo_id": ngo_id,
        "contact_number": payload.get("contact_number"),
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    # If the database enforces ngo_id FK to a different table, remove ngo_id on FK failure
    result = _insert_with_schema_fallback("patients", person, "insert patient")
    if not result.get("success"):
        err = str(result.get("error", "")).lower()
        if "foreign key" in err and "ngo_id" in err:
            trimmed = {k: v for k, v in person.items() if k != "ngo_id"}
            result = _insert_with_schema_fallback("patients", trimmed, "insert patient (no ngo_id)")
    status = 201 if result.get("success") else 400
    return jsonify({"success": result.get("success"), "data": result.get("data"), "error": result.get("error")}), status


# ---------------------------- Appointments ---------------------------- #
@ngo_bp.route("/appointments", methods=["GET", "POST"])
def appointments():
    auth_err = _require_ngo()
    if auth_err and request.method != "GET":
        return auth_err

    if not _table_exists("appointments"):
        return jsonify({"success": False, "error": "appointments table missing. See docs/create_ngo_dashboard_tables.sql"}), 400

    ngo_id = session.get("user_id")

    if request.method == "GET":
        status_filter = request.args.get("status")
        query = supabase.table("appointments").select("*").order("appointment_date", desc=True)
        if ngo_id:
            query = query.eq("ngo_id", ngo_id)
        if status_filter and status_filter != "all":
            query = query.eq("status", status_filter)

        resp = safe_supabase_query(lambda: query.limit(100).execute(), [], "list appointments")
        data = resp.get("data", []) or []
        # enrich with patient names when possible
        if _table_exists("patients"):
            for ap in data:
                pid = ap.get("patient_id")
                if pid:
                    try:
                        p = supabase.table("patients").select("name").eq("id", pid).single().execute()
                        if getattr(p, "data", None):
                            ap["patient_name"] = p.data.get("name")
                    except Exception:
                        pass
                elif ap.get("booking_notes"):
                    ap["patient_name"] = ap.get("booking_notes")
        if not data:
            data = [
                {"id": "SAMPLE-APT-1", "patient_id": "SAMPLE-PAT-1", "appointment_date": "2025-12-16", "appointment_time": "09:00", "status": "scheduled"},
                {"id": "SAMPLE-APT-2", "patient_id": "SAMPLE-PAT-2", "appointment_date": "2025-12-17", "appointment_time": "11:00", "status": "scheduled"},
            ]
        return jsonify({"success": True, "data": data})

    payload = request.json or {}
    required = ["appointment_date", "appointment_time"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return jsonify({"success": False, "error": f"Missing fields: {', '.join(missing)}"}), 400

    # Allow free-text patient; if not a valid UUID, store it in booking_notes and keep patient_id null
    patient_id = payload.get("patient_id")
    patient_note = None
    if patient_id:
        try:
            uuid.UUID(str(patient_id))
        except Exception:
            patient_note = f"Patient (typed): {patient_id}"
            patient_id = None

    # generate appointment id from timestamp
    appointment_id = f"APT{int(datetime.utcnow().timestamp())}"
    data = {
        "id": appointment_id,
        "ngo_id": ngo_id,
        "appointment_date": payload["appointment_date"],
        "appointment_time": payload["appointment_time"],
        "status": payload.get("status", "scheduled"),
        "priority": payload.get("priority", "normal"),
        "symptoms": payload.get("symptoms"),
        "booking_notes": payload.get("booking_notes") or patient_note,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    if patient_id:
        data["patient_id"] = patient_id

    result = safe_supabase_write(lambda: supabase.table("appointments").insert(data).execute(), "create appointment")
    status = 201 if result.get("success") else 400
    return jsonify({"success": result.get("success"), "data": result.get("data"), "error": result.get("error")}), status


# ---------------------------- Food / Hotel ---------------------------- #
@ngo_bp.route("/donations", methods=["GET"])
def donations():
    auth_err = _require_ngo()
    if auth_err and request.method != "GET":
        return auth_err

    if not _table_exists("donations"):
        return jsonify({"success": True, "data": [], "message": "donations table missing"}), 200

    # Try available first; if none, return latest donations as fallback so UI has something to select
    def _available_query():
        return (
            supabase.table("donations")
            .select("*")
            .eq("status", "available")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

    resp = safe_supabase_query(_available_query, [], "list donations available")
    data = resp.get("data") or []

    if not data:
        resp = safe_supabase_query(
            lambda: supabase.table("donations").select("*").order("created_at", desc=True).limit(50).execute(),
            [],
            "list donations fallback",
        )
        data = resp.get("data") or []

    # If still empty, return sample items (not persisted) so UI has options
    if not data:
        data = [
            {"id": "SAMPLE-DON-1", "meal_type": "Veg Meals", "quantity": 25, "status": "available"},
            {"id": "SAMPLE-DON-2", "meal_type": "Bread Packs", "quantity": 40, "status": "available"},
        ]

    return jsonify({"success": True, "data": data})


@ngo_bp.route("/orders", methods=["GET", "POST", "OPTIONS"])
def orders():
    auth_err = _require_ngo()
    if auth_err:
        return auth_err

    if not _table_exists("meal_requests"):
        return jsonify({
            "success": False,
            "error": "meal_requests table missing. Run docs/create_ngo_dashboard_tables.sql in Supabase SQL editor."
        }), 400

    if request.method == "GET":
        ngo_id = session.get("user_id")
        query = supabase.table("meal_requests").select("*").order("created_at", desc=True)
        if ngo_id:
            query = query.eq("ngo_id", ngo_id)
        resp = safe_supabase_query(lambda: query.limit(100).execute(), [], "list meal requests")
        data = resp.get("data") or []
        return jsonify({"success": True, "data": data})

    payload = request.json or {}
    if not payload.get("quantity"):
        return jsonify({"success": False, "error": "quantity is required"}), 400

    # normalize optional FKs: treat empty string as null to avoid UUID cast errors
    donation_id = payload.get("donation_id") or None
    hotel_id = payload.get("hotel_id") or None
    qty = payload.get("quantity")
    try:
        qty = int(qty)
    except Exception:
        qty = None

    order = {
        "ngo_id": session.get("user_id"),
        "donation_id": donation_id,  # optional
        "requested_quantity": qty,
        "hotel_id": hotel_id,
        "notes": payload.get("notes"),
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    result = safe_supabase_write(lambda: supabase.table("meal_requests").insert(order).execute(), "create meal request")
    status = 201 if result.get("success") else 400
    return jsonify({"success": result.get("success"), "data": result.get("data"), "error": result.get("error")}), status


@ngo_bp.route("/hotels", methods=["GET"])
def hotels():
    auth_err = _require_ngo()
    if auth_err and request.method != "GET":
        return auth_err

    if not _table_exists("hotels"):
        samples = [
            {"id": "SAMPLE-HOTEL-1", "name": "Blue Sky Hotel", "address": "Central Road", "contact_number": "+1 555 111"},
            {"id": "SAMPLE-HOTEL-2", "name": "City Comfort Inn", "address": "Market Street", "contact_number": "+1 555 222"},
        ]
        return jsonify({"success": True, "data": samples, "message": "hotels table missing (showing sample data)"}), 200

    resp = safe_supabase_query(
        lambda: supabase.table("hotels").select("id, name, address, contact_number").order("name").execute(),
        [],
        "list hotels",
    )
    data = resp.get("data") or []
    if not data:
        data = [
            {"id": "SAMPLE-HOTEL-1", "name": "Blue Sky Hotel", "address": "Central Road", "contact_number": "+1 555 111"},
            {"id": "SAMPLE-HOTEL-2", "name": "City Comfort Inn", "address": "Market Street", "contact_number": "+1 555 222"},
        ]
    return jsonify({"success": True, "data": data})


@ngo_bp.route("/hotels", methods=["POST"])
def add_hotel():
    auth_err = _require_ngo()
    if auth_err:
        return auth_err

    if not _table_exists("hotels"):
        return jsonify({"success": False, "error": "hotels table missing. Please create it first."}), 400

    payload = request.json or {}
    if not payload.get("name"):
        return jsonify({"success": False, "error": "Hotel name is required"}), 400

    hotel = {
        "name": payload.get("name"),
        "address": payload.get("address"),
        "contact_number": payload.get("contact_number"),
        "created_at": datetime.utcnow().isoformat(),
    }
    res = safe_supabase_write(lambda: supabase.table("hotels").insert(hotel).execute(), "insert hotel")
    status = 201 if res.get("success") else 400
    return jsonify({"success": res.get("success"), "data": res.get("data"), "error": res.get("error")}), status


# ---------------------------- Volunteers ---------------------------- #
@ngo_bp.route("/volunteers", methods=["GET"])
def volunteers():
    auth_err = _require_ngo()
    if auth_err and request.method != "GET":
        return auth_err

    volunteers_data: List[Dict[str, Any]] = []

    if _table_exists("users"):
        user_resp = safe_supabase_query(
            lambda: supabase.table("users").select("id, name, email, phone").eq("role", "volunteer").order("name").execute(),
            [],
            "list volunteers",
        )
        volunteers_data = user_resp.get("data", []) or []

        # enrich with volunteer_data when available
        if volunteers_data and _table_exists("volunteer_data"):
            ids = [v["id"] for v in volunteers_data if v.get("id")]
            if ids:
                meta_resp = safe_supabase_query(
                    lambda: supabase.table("volunteer_data").select("*").in_("volunteer_id", ids).execute(),
                    [],
                    "volunteer_data bulk fetch",
                )
                meta_lookup = {}
                for row in meta_resp.get("data", []) or []:
                    meta_lookup[row.get("volunteer_id")] = row
                for v in volunteers_data:
                    v["meta"] = meta_lookup.get(v.get("id"), {})

    if not volunteers_data:
        volunteers_data = [
            {"id": "SAMPLE-VOL-1", "name": "John Helper", "email": "john@example.com", "phone": "+1 555 1111",
             "meta": {"assigned_region": "Central", "status": "active"}},
            {"id": "SAMPLE-VOL-2", "name": "Sara Aid", "email": "sara@example.com", "phone": "+1 555 2222",
             "meta": {"assigned_region": "North", "status": "on_break"}},
        ]

    return jsonify({"success": True, "data": volunteers_data})


@ngo_bp.route("/volunteers/<volunteer_id>", methods=["PUT"])
def update_volunteer(volunteer_id: str):
    auth_err = _require_ngo()
    if auth_err:
        return auth_err

    payload = request.json or {}
    updates = {}
    if "name" in payload:
        updates["name"] = payload["name"]
    if "email" in payload:
        updates["email"] = payload["email"]
    if "phone" in payload:
        updates["phone"] = payload["phone"]

    if updates:
        safe_supabase_write(lambda: supabase.table("users").update(updates).eq("id", volunteer_id).execute(), "update volunteer user")

    # volunteer_data fields
    meta_updates = {}
    if "assigned_region" in payload:
        meta_updates["assigned_region"] = payload["assigned_region"]
    if "status" in payload:
        meta_updates["status"] = payload["status"]
    if meta_updates:
        meta_updates["updated_at"] = datetime.utcnow().isoformat()
        # Some databases may miss columns like assigned_region/status; retry without missing columns if schema cache complains
        res = safe_supabase_write(
            lambda: supabase.table("volunteer_data").update(meta_updates).eq("volunteer_id", volunteer_id).execute(),
            "update volunteer meta",
        )
        if not res.get("success"):
            err = str(res.get("error", "")).lower()
            if "could not find the" in err and "in the schema cache" in err:
                for k in list(meta_updates.keys()):
                    if k != "updated_at":
                        meta_updates.pop(k, None)
                        break
                safe_supabase_write(
                    lambda: supabase.table("volunteer_data").update(meta_updates).eq("volunteer_id", volunteer_id).execute(),
                    "update volunteer meta (trimmed)",
                )

    return jsonify({"success": True, "message": "Volunteer updated"})
