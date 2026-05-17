import os
import pathlib
from supabase import create_client, Client
from dotenv import load_dotenv, find_dotenv

# Ensure we load the project's .env (backend/.env) even when running from project root
env_path = pathlib.Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # fallback: search upward for a .env file
    dotenv_file = find_dotenv()
    if dotenv_file:
        load_dotenv(dotenv_file)

url: str = os.environ.get("SUPABASE_URL")
# Prefer a service role key for server-side operations; fall back to anon key if service key not set
service_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
anon_key: str = os.environ.get("SUPABASE_KEY")

if not url:
    raise ValueError("SUPABASE_URL must be set in environment variables")

# choose key: prefer service key for writes to bypass RLS when appropriate
chosen_key = service_key or anon_key
if not chosen_key:
    raise ValueError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY must be set in environment variables")

if service_key and not anon_key:
    # explicit: using service key only
    supabase: Client = create_client(url, service_key)
else:
    # prefer service key if present, else anon key
    supabase: Client = create_client(url, chosen_key)

if service_key:
    print("[OK] Supabase: using SERVICE ROLE key for server-side operations")
else:
    print("[WARN] Supabase: SERVICE ROLE key not found; using anon key (writes may be restricted)")


def safe_supabase_write(query_func, operation_name=""):
    """Execute a supabase write operation (insert/update/delete) and return a normalized result.

    query_func should be a zero-arg callable that executes the supabase operation and returns the response.
    """
    try:
        result = query_func()

        # Some client versions return object with .error/.data, others return dicts
        if hasattr(result, 'error') and result.error:
            error_msg = str(result.error)
            print(f"[ERROR] [{operation_name}] Supabase error: {error_msg}")
            return {"success": False, "error": error_msg, "raw": result}

        if isinstance(result, dict):
            if result.get('error'):
                error_msg = str(result.get('error'))
                print(f"[ERROR] [{operation_name}] Supabase error: {error_msg}")
                return {"success": False, "error": error_msg, "raw": result}
            print(f"[OK] [{operation_name}] Write successful")
            return {"success": True, "data": result.get('data'), "raw": result}

        print(f"[OK] [{operation_name}] Write successful")
        return {"success": True, "data": getattr(result, 'data', None), "raw": result}

    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] [{operation_name}] Exception: {error_msg}")
        return {"success": False, "error": error_msg}


def safe_supabase_query(query_func, fallback_value=None, operation_name=""):
    """Safely execute a Supabase query with error handling (reads)."""
    try:
        if not supabase:
            return fallback_value

        result = query_func()

        if hasattr(result, 'error') and result.error:
            print(f"[ERROR] Supabase query error during {operation_name}: {result.error}")
            return {"success": False, "data": None, "error": str(result.error), "raw": result}

        if isinstance(result, dict) and result.get('error'):
            print(f"[ERROR] Supabase query error during {operation_name}: {result.get('error')}")
            return {"success": False, "data": None, "error": str(result.get('error')), "raw": result}

        # Normalize successful result into a dict
        data = None
        if isinstance(result, dict):
            data = result.get('data')
        else:
            data = getattr(result, 'data', None)
        return {"success": True, "data": data, "raw": result}
    except Exception as e:
        print(f"[WARN] Error in {operation_name}: {e}")
        return {"success": False, "data": None, "error": str(e)}