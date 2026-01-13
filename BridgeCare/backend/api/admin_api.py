from datetime import datetime
from typing import Dict, Any, List

from flask import Blueprint, jsonify, request, session

from backend.supabase_client import supabase, safe_supabase_query, safe_supabase_write

admin_api_bp = Blueprint("admin_api_bp", __name__, url_prefix="/api/admin")


def _count(table: str, filters: Dict[str, Any] = None) -> int:
    try:
        query = supabase.table(table).select("id", count="exact")
        for k, v in (filters or {}).items():
            query = query.eq(k, v)
        resp = query.execute()
        if hasattr(resp, "count") and resp.count is not None:
            return resp.count
        data = getattr(resp, "data", None) or []
        return len(data)
    except Exception:
        return 0


def _list_ngos() -> List[Dict[str, Any]]:
    resp = safe_supabase_query(
        lambda: supabase.table("users").select("id, name, email, phone, created_at").eq("role", "ngo").order("created_at", desc=True).execute(),
        [],
        "admin list ngos",
    )
    return resp.get("data") or []


@admin_api_bp.route("/summary", methods=["GET"])
def summary():
    # basic auth: require admin session
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = {
        "users": _count("users"),
        "ngos": _count("users", {"role": "ngo"}),
        "volunteers": _count("users", {"role": "volunteer"}),
        "hotels": _count("users", {"role": "hotel"}) if supabase else 0,
        "donations": _count("donations"),
        "appointments": _count("appointments"),
        "homeless": _count("homeless_people"),
    }
    return jsonify({"success": True, "data": data})


@admin_api_bp.route("/ngos", methods=["GET"])
def ngos():
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({"success": True, "data": _list_ngos()})


@admin_api_bp.route("/ngos/<ngo_id>", methods=["PUT"])
def update_ngo(ngo_id: str):
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    payload = request.json or {}
    updates = {}
    for key in ["name", "email", "phone"]:
        if key in payload:
            updates[key] = payload[key]
    if not updates:
        return jsonify({"success": False, "error": "No fields to update"}), 400

    updates["updated_at"] = datetime.utcnow().isoformat()
    res = safe_supabase_write(lambda: supabase.table("users").update(updates).eq("id", ngo_id).execute(), "admin update ngo")
    if not res.get("success"):
        return jsonify({"success": False, "error": res.get("error")}), 400

    # return refreshed record
    refreshed = safe_supabase_query(
        lambda: supabase.table("users").select("id, name, email, phone, created_at").eq("id", ngo_id).single().execute(),
        None,
        "admin get ngo",
    )
    return jsonify({"success": True, "data": refreshed.get("data")})


@admin_api_bp.route("/settings", methods=["GET"])
def settings():
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    # Simple system snapshot
    info = {
        "supabase_url_present": bool(supabase),
        "timestamp": datetime.utcnow().isoformat(),
    }
    return jsonify({"success": True, "data": info})
