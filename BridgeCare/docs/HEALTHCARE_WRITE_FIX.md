# Healthcare Module - Fix Data Not Updating (Writes Failing)

## Problem
Patient and appointment data is not being inserted/updated/deleted in Supabase tables. The server runs fine but writes don't persist.

## Root Cause
The Flask server is using the **anon key** (SUPABASE_KEY) instead of the **service role key** (SUPABASE_SERVICE_ROLE_KEY). Supabase Row-Level Security (RLS) policies on the healthcare tables **block anon-key writes** by default.

Symptom: Check server logs — you'll see:
```
⚠️ Supabase: SERVICE ROLE key not found; using anon key (writes may be restricted)
```

## Solution: Choose One

### Option A: Disable RLS (Simple, for Development/Testing)
Allow the anon key to write by disabling Row-Level Security on healthcare tables.

**Steps:**
1. Open Supabase SQL Editor (https://app.supabase.com → Project → SQL Editor)
2. Copy and paste the SQL from `docs/disable_rls_healthcare.sql`
3. Execute the SQL
4. Restart the Flask server (it will reconnect to DB)
5. Test: POST to http://localhost:5000/api/healthcare/patients with a sample patient
   - You should see success messages in server logs

**SQL Command:**
```sql
-- Run this in Supabase SQL Editor
ALTER TABLE IF EXISTS ngos DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS healthcare_providers DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS volunteers DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS patients DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS appointments DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS treatment_history DISABLE ROW LEVEL SECURITY;
```

### Option B: Provide Service Role Key to Server (Recommended for Production)
Give the Flask server the service role key so it can bypass RLS.

**Steps:**
1. Get your Supabase **SERVICE ROLE KEY** from:
   - Supabase Dashboard → Settings → API → Service Role Key
   - ⚠️ KEEP THIS SECRET - never commit it or share publicly
2. Create/edit `backend/.env` in your project:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=eyJ...anon-key...
   SUPABASE_SERVICE_ROLE_KEY=eyJ...service-role-key...
   ```
3. Restart Flask server:
   ```powershell
   cd d:\project_main\BridgeCare
   python app.py
   ```
4. Check server logs — you should see:
   ```
   ✅ Supabase: using SERVICE ROLE key for server-side operations
   ```
5. Test a write operation — it should succeed

## Verify the Fix

### Test 1: Check which key is being used
```powershell
curl http://127.0.0.1:5000/api/debug/supabase-info
```
Response should show:
- `has_service_role_key: true` OR `has_service_role_key: false`
- `has_anon_key: true`

### Test 2: Create a patient
```powershell
$body = @{
    name = 'Test Patient'
    homeless_id = 'HMTEST001'
} | ConvertTo-Json

curl -X POST http://127.0.0.1:5000/api/healthcare/patients `
  -H "Content-Type: application/json" `
  -d $body
```
Expected response:
```json
{
  "success": true,
  "data": [{"id": "...", "name": "Test Patient", "homeless_id": "HMTEST001", ...}],
  "message": "Patient created successfully"
}
```

### Test 3: Create an appointment
```powershell
$body = @{
    patient_id = 'PASTE_PATIENT_UUID_FROM_TEST_2'
    healthcare_provider_id = 'PASTE_PROVIDER_UUID'
    appointment_date = (Get-Date -Format 'yyyy-MM-dd')
    appointment_time = '10:00'
} | ConvertTo-Json

curl -X POST http://127.0.0.1:5000/api/healthcare/appointments `
  -H "Content-Type: application/json" `
  -d $body
```

### Test 4: Initialize sample data
```powershell
curl -X POST http://127.0.0.1:5000/api/healthcare/initialize-sample-data
```
This will attempt to insert sample NGOs and patients.

## Debug: View Error Details

When a write fails, the server logs now show detailed error messages. Start the server in a terminal and watch for logs like:
```
❌ [insert patient] Supabase error: new row violates row-level security policy
❌ [insert appointment] Exception: ...
✅ [insert patient] Write successful
```

## Table Status Check

Get a full report of table existence and RLS status:
```powershell
curl http://127.0.0.1:5000/api/health/status
```

Response includes:
- `database_tables`: which healthcare tables exist
- `record_counts`: how many rows in each table
- `supabase`: connection status

## If Writes Still Fail

1. **Check RLS status in Supabase:**
   - Dashboard → Tables → select each healthcare table → Authentication → Row Level Security
   - If enabled and policies are present, verify they allow anon users or include the necessary conditions

2. **Check table structure:**
   - Does the table exist? (GET /api/health/status shows existence)
   - Are all required columns present?
   - Do foreign keys reference existing tables?

3. **Check Supabase logs:**
   - Supabase Dashboard → Logs → Edge Functions or Database
   - Look for RLS policy violation or constraint errors

4. **Enable verbose server logging** (if debugging):
   - Server already logs detailed errors
   - Watch the terminal where Flask runs when making POST requests

## Next Steps

- [ ] Choose Option A (disable RLS) or Option B (add service role key)
- [ ] Apply the fix
- [ ] Restart Flask server
- [ ] Test one of the verification steps above
- [ ] Confirm data appears in Supabase (Dashboard → Tables → patients/appointments)
