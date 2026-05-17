# ⚠️ URGENT: Fix Prescription Error - Step by Step

## The Error You're Seeing

```
Could not find the 'healthcare_provider_id' column of 'treatment_history' in the schema cache
```

This error happens because Supabase's schema cache expects a column that doesn't exist.

## ✅ SOLUTION: Run These 2 SQL Scripts (REQUIRED)

### Step 1: Remove the Column

**Open Supabase SQL Editor and run this:**

```sql
-- Remove healthcare_provider_id column
ALTER TABLE IF EXISTS treatment_history 
DROP COLUMN IF EXISTS healthcare_provider_id;

-- Drop related index
DROP INDEX IF EXISTS idx_treatment_history_provider_id;
```

**File location:** `docs/remove_healthcare_provider_id_from_treatment_history.sql`

### Step 2: Create RPC Function (THIS IS CRITICAL!)

**Open Supabase SQL Editor and run this:**

```sql
-- Create function to insert treatment history (bypasses schema cache)
CREATE OR REPLACE FUNCTION insert_treatment_history(
    p_appointment_id TEXT,
    p_patient_id UUID,
    p_ngo_id UUID DEFAULT NULL,
    p_diagnosis TEXT DEFAULT NULL,
    p_prescription TEXT,
    p_notes TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    appointment_id TEXT,
    patient_id UUID,
    ngo_id UUID,
    diagnosis TEXT,
    prescription TEXT,
    notes TEXT,
    created_at TIMESTAMP
) 
LANGUAGE plpgsql
AS $$
DECLARE
    new_record RECORD;
BEGIN
    INSERT INTO treatment_history (
        appointment_id, patient_id, ngo_id, diagnosis, prescription, notes
    ) VALUES (
        p_appointment_id, p_patient_id, p_ngo_id, p_diagnosis, p_prescription, p_notes
    )
    RETURNING * INTO new_record;
    
    RETURN QUERY SELECT 
        new_record.id, new_record.appointment_id, new_record.patient_id,
        new_record.ngo_id, new_record.diagnosis, new_record.prescription,
        new_record.notes, new_record.created_at;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION insert_treatment_history TO authenticated;
GRANT EXECUTE ON FUNCTION insert_treatment_history TO anon;
GRANT EXECUTE ON FUNCTION insert_treatment_history TO service_role;
```

**File location:** `docs/create_insert_treatment_history_function.sql`

## 📋 Detailed Steps

1. **Go to Supabase Dashboard**
   - Visit: https://app.supabase.com
   - Select your project

2. **Open SQL Editor**
   - Click "SQL Editor" in left sidebar
   - Click "New query"

3. **Run Step 1 Script**
   - Copy the SQL from Step 1 above
   - Paste into SQL Editor
   - Click "Run" (or Ctrl+Enter)
   - Wait for "Success" message

4. **Run Step 2 Script** (IMPORTANT!)
   - Click "New query" again
   - Copy the SQL from Step 2 above
   - Paste into SQL Editor
   - Click "Run"
   - Wait for "Success" message

5. **Wait 10-30 seconds** for schema cache to refresh

6. **Test**
   - Try saving a prescription
   - It should work now!

## ⚠️ Why This Error Keeps Happening

The error keeps appearing because:
- The RPC function doesn't exist in your database yet
- Without the RPC function, the code falls back to direct insert
- Direct insert hits Supabase's schema cache validation
- Schema cache still expects `healthcare_provider_id` column

**The RPC function (Step 2) bypasses schema cache validation** - that's why it's critical!

## ✅ Verification

After running both scripts, verify:

```sql
-- Check function exists
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_name = 'insert_treatment_history';
-- Should return 1 row

-- Check columns (healthcare_provider_id should NOT be in list)
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'treatment_history';
-- Should show: id, appointment_id, patient_id, ngo_id, diagnosis, prescription, notes, created_at
```

## 🚨 If Still Not Working

1. **Check function exists:** Run the verification query above
2. **Wait longer:** Schema cache can take up to 1 minute to refresh
3. **Restart Flask server:** Sometimes helps clear caches
4. **Check Supabase logs:** Look for any errors in Supabase dashboard

## Summary

**You MUST run BOTH SQL scripts:**
1. ✅ Remove column (Step 1)
2. ✅ Create RPC function (Step 2) - **THIS IS REQUIRED!**

Without Step 2, prescriptions will keep failing!
