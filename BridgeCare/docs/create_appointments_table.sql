-- ============================================================================
-- APPOINTMENTS TABLE CREATION SCRIPT
-- ============================================================================
-- This script creates the appointments table for the BridgeCare healthcare module
-- Run this in your Supabase SQL editor or PostgreSQL database

-- APPOINTMENTS TABLE
-- Stores appointments booked for patients
CREATE TABLE IF NOT EXISTS appointments (
    id TEXT PRIMARY KEY,
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    ngo_id UUID REFERENCES users(id) ON DELETE SET NULL,
    volunteer_id UUID REFERENCES users(id) ON DELETE SET NULL,
    appointment_date DATE,
    appointment_time TIME,
    status VARCHAR(50) DEFAULT 'scheduled' CHECK (status IN ('scheduled','completed','cancelled','no_show')),
    priority VARCHAR(50) DEFAULT 'normal' CHECK (priority IN ('low','normal','high')),
    symptoms TEXT,
    referred_by VARCHAR(255),
    booking_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_appointments_patient_id ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_ngo_id ON appointments(ngo_id);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);

-- Disable Row-Level Security (RLS) for development/testing
-- Uncomment the line below if you need to disable RLS for the appointments table
-- ALTER TABLE IF EXISTS appointments DISABLE ROW LEVEL SECURITY;

-- Verify table creation
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'appointments'
ORDER BY ordinal_position;

