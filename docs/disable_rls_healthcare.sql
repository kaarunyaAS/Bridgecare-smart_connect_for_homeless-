-- Disable Row-Level Security (RLS) on healthcare module tables
-- This allows writes with the anon key (SUPABASE_KEY) for development/testing
-- For production, instead create appropriate RLS policies or use SERVICE ROLE key

-- Disable RLS on ngos table
ALTER TABLE IF EXISTS ngos DISABLE ROW LEVEL SECURITY;

-- Disable RLS on healthcare_providers table
ALTER TABLE IF EXISTS healthcare_providers DISABLE ROW LEVEL SECURITY;

-- Disable RLS on volunteers table
ALTER TABLE IF EXISTS volunteers DISABLE ROW LEVEL SECURITY;

-- Disable RLS on patients table
ALTER TABLE IF EXISTS patients DISABLE ROW LEVEL SECURITY;

-- Disable RLS on appointments table
ALTER TABLE IF EXISTS appointments DISABLE ROW LEVEL SECURITY;

-- Disable RLS on treatment_history table
ALTER TABLE IF EXISTS treatment_history DISABLE ROW LEVEL SECURITY;

-- Verify: Show RLS status for all healthcare tables
SELECT schemaname, tablename, rowsecurity FROM pg_tables
WHERE tablename IN ('ngos', 'healthcare_providers', 'volunteers', 'patients', 'appointments', 'treatment_history')
ORDER BY tablename;
