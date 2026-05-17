-- ============================================================================
-- REMOVE healthcare_provider_id FROM treatment_history TABLE
-- ============================================================================
-- This script removes the healthcare_provider_id column from treatment_history table
-- 
-- IMPORTANT: Run this script in your Supabase SQL editor to fix the prescription
-- saving error. The error occurs because Supabase's schema cache expects this
-- column but it doesn't exist in the actual database table.
--
-- Steps:
-- 1. Open your Supabase project dashboard (https://app.supabase.com)
-- 2. Select your project
-- 3. Go to SQL Editor (left sidebar)
-- 4. Click "New query"
-- 5. Paste this entire script
-- 6. Click "Run" or press Ctrl+Enter
-- 7. After running, refresh Supabase schema cache (may take a few seconds)
-- 8. Try saving a prescription again - it should work!
-- ============================================================================

-- Step 1: Drop the column if it exists
ALTER TABLE IF EXISTS treatment_history 
DROP COLUMN IF EXISTS healthcare_provider_id;

-- Step 2: Drop the index if it exists (if there was one)
DROP INDEX IF EXISTS idx_treatment_history_provider_id;

-- Step 3: Verify the column was removed
-- You should see: id, appointment_id, patient_id, ngo_id, diagnosis, prescription, notes, created_at
-- (healthcare_provider_id should NOT be in the list)
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'treatment_history'
ORDER BY ordinal_position;

-- ============================================================================
-- If you still get errors after running this:
-- 1. Wait a few seconds for Supabase schema cache to refresh
-- 2. Try restarting your Flask server
-- 3. Check that the column was actually removed by running the SELECT above
-- ============================================================================
