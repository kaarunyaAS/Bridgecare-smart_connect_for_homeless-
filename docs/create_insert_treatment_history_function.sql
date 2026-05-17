-- ============================================================================
-- CREATE FUNCTION TO INSERT TREATMENT HISTORY (BYPASSES SCHEMA CACHE ISSUE)
-- ============================================================================
-- This function allows inserting into treatment_history without PostgREST
-- schema cache validation issues. Run this AFTER removing healthcare_provider_id column.
--
-- Steps:
-- 1. First run: remove_healthcare_provider_id_from_treatment_history.sql
-- 2. Then run this script
-- 3. The backend will automatically use this function
-- ============================================================================

-- Create or replace function to insert treatment history
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
    -- Insert into treatment_history
    INSERT INTO treatment_history (
        appointment_id,
        patient_id,
        ngo_id,
        diagnosis,
        prescription,
        notes
    ) VALUES (
        p_appointment_id,
        p_patient_id,
        p_ngo_id,
        p_diagnosis,
        p_prescription,
        p_notes
    )
    RETURNING * INTO new_record;
    
    -- Return the inserted record
    RETURN QUERY SELECT 
        new_record.id,
        new_record.appointment_id,
        new_record.patient_id,
        new_record.ngo_id,
        new_record.diagnosis,
        new_record.prescription,
        new_record.notes,
        new_record.created_at;
END;
$$;

-- Grant execute permission (adjust as needed for your RLS setup)
GRANT EXECUTE ON FUNCTION insert_treatment_history TO authenticated;
GRANT EXECUTE ON FUNCTION insert_treatment_history TO anon;
GRANT EXECUTE ON FUNCTION insert_treatment_history TO service_role;

-- Verify function was created
SELECT 
    routine_name, 
    routine_type,
    data_type
FROM information_schema.routines
WHERE routine_schema = 'public' 
AND routine_name = 'insert_treatment_history';
