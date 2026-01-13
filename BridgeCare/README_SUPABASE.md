Quick guide - Supabase setup for BridgeCare

1) Create a file `backend/.env` by copying `backend/.env.example` and filling real values.
   - Make sure you use the SERVICE ROLE KEY for `SUPABASE_SERVICE_ROLE_KEY` when running server-side code.
   - The anon key (`SUPABASE_KEY`) is read-only in many setups (Row-Level Security may block writes).

2) Check that the env file is loaded and used by the server. Example (PowerShell):

```powershell
# From project root
Set-Content -Path backend\.env -Value (Get-Content backend\.env.example)
# Then edit backend\.env in your editor and paste in your keys

# Start the server
python .\app.py
```

3) Use the write-test endpoint to verify server-side write permissions:

```powershell
# Attempt write test (server must be running)
curl -X POST http://127.0.0.1:5000/api/health/write-test
```

- If the response indicates an error and the server printed "using anon key", your `SUPABASE_SERVICE_ROLE_KEY` is not configured.
- Place the service role key in `backend/.env` (or set it in your OS environment) and restart the server.

Security note: keep your service role key secret. Do not commit `backend/.env` to version control.
