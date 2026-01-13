# Fix Prescription Saving Error - Complete Guide

## Problem
Getting error: `Could not find the 'healthcare_provider_id' column of 'treatment_history' in the schema cache` (PGRST204)

This happens because Supabase's PostgREST schema cache expects a column that doesn't exist in the actual database.

## Solution (2 Steps)

### Step 1: Remove the Column
Run this SQL in Supabase SQL Editor:

```sql
-- Remove healthcare_provider_id column
ALTER TABLE IF EXISTS treatment_history 
DROP COLUMN IF EXISTS healthcare_provider_id;

-- Drop related index
DROP INDEX IF EXISTS idx_treatment_history_provider_id;
```

**File:** `docs/remove_healthcare_provider_id_from_treatment_history.sql`

### Step 2: Create RPC Function (Bypasses Schema Cache)
Run this SQL in Supabase SQL Editor:

```sql
-- Create function to insert treatment history
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

**File:** `docs/create_insert_treatment_history_function.sql`

## How to Run

1. **Open Supabase Dashboard**
   - Go to https://app.supabase.com
   - Select your project
   - Click "SQL Editor" in left sidebar

2. **Run Step 1 Script**
   - Click "New query"
   - Copy/paste the SQL from Step 1
   - Click "Run" (or Ctrl+Enter)
   - Wait for success message

3. **Run Step 2 Script**
   - Click "New query" again
   - Copy/paste the SQL from Step 2
   - Click "Run"
   - Wait for success message

4. **Wait 10-30 seconds** for Supabase schema cache to refresh

5. **Test**
   - Try saving a prescription
   - It should work now!

## How It Works

- **Step 1** removes the problematic column from the database
- **Step 2** creates a PostgreSQL function that bypasses PostgREST's schema validation
- The backend code automatically tries the RPC function first, then falls back to direct insert
- This ensures prescriptions save correctly even if schema cache is stale

## Verification

After running both scripts, verify with:

```sql
-- Check columns (healthcare_provider_id should NOT be in the list)
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'treatment_history';

-- Check function exists
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_name = 'insert_treatment_history';
```

## Troubleshooting

- **Still getting error?** Wait longer (up to 1 minute) for cache refresh
- **Function not found?** Make sure Step 2 ran successfully
- **Permission denied?** Check RLS policies or use SERVICE ROLE key
