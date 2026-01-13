-- Complete database schema for BridgeCare Supabase project
-- Run these queries in Supabase SQL Editor

-- 1. USERS TABLE (Core user management)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    organization VARCHAR(255),
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'healthcare', 'hotel', 'ngo', 'volunteer', 'donor')),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. VOLUNTEER_DATA TABLE (Volunteer-specific information)
CREATE TABLE IF NOT EXISTS volunteer_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    volunteer_id UUID REFERENCES users(id) ON DELETE CASCADE,
    availability VARCHAR(255),
    skills TEXT,
    hours_volunteered INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. HEALTHCARE_DATA TABLE (Healthcare center information)
CREATE TABLE IF NOT EXISTS healthcare_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    healthcare_id UUID REFERENCES users(id) ON DELETE CASCADE,
    facility_name VARCHAR(255),
    services TEXT,
    bed_capacity INTEGER,
    current_patients INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. HOTEL_DATA TABLE (Food/Hotel donation information)
CREATE TABLE IF NOT EXISTS hotel_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id UUID REFERENCES users(id) ON DELETE CASCADE,
    establishment_name VARCHAR(255),
    food_type VARCHAR(255),
    quantity_available INTEGER,
    dietary_restrictions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. NGO_DATA TABLE (NGO-specific information)
CREATE TABLE IF NOT EXISTS ngo_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ngo_id UUID REFERENCES users(id) ON DELETE CASCADE,
    organization_name VARCHAR(255),
    focus_area TEXT,
    beneficiaries INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. HOMELESS_PEOPLE TABLE (Records of homeless individuals registered by volunteers)
CREATE TABLE IF NOT EXISTS homeless_people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    volunteer_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    age INTEGER,
    gender VARCHAR(50),
    location VARCHAR(255),
    health_status TEXT,
    contact_info VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. PATIENTS TABLE (Healthcare patient records)
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    healthcare_id UUID REFERENCES users(id) ON DELETE CASCADE,
    patient_name VARCHAR(255),
    age INTEGER,
    gender VARCHAR(50),
    condition TEXT,
    admission_date TIMESTAMP,
    discharge_date TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. FOOD_DONATIONS TABLE (Food items donated by hotels)
CREATE TABLE IF NOT EXISTS food_donations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id UUID REFERENCES users(id) ON DELETE CASCADE,
    food_type VARCHAR(255),
    quantity INTEGER,
    expiry_date TIMESTAMP,
    pickup_location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'available' CHECK (status IN ('available', 'collected', 'expired')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. NEEDS TABLE (NGO-registered needs)
CREATE TABLE IF NOT EXISTS needs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ngo_id UUID REFERENCES users(id) ON DELETE CASCADE,
    need_type VARCHAR(255),
    description TEXT,
    priority VARCHAR(50) CHECK (priority IN ('low', 'medium', 'high')),
    quantity_needed INTEGER,
    quantity_fulfilled INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. DONATIONS TABLE (General donations from donors)
CREATE TABLE IF NOT EXISTS donations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    donor_id UUID REFERENCES users(id) ON DELETE CASCADE,
    donation_type VARCHAR(255),
    amount DECIMAL(10, 2),
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'received')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. LOGIN_ACTIVITIES TABLE (Track user login history)
CREATE TABLE IF NOT EXISTS login_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(255),
    role VARCHAR(50),
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    status VARCHAR(50) DEFAULT 'success' CHECK (status IN ('success', 'failed'))
);

-- INDEXES for better query performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_volunteer_data_volunteer_id ON volunteer_data(volunteer_id);
CREATE INDEX idx_healthcare_data_healthcare_id ON healthcare_data(healthcare_id);
CREATE INDEX idx_hotel_data_hotel_id ON hotel_data(hotel_id);
CREATE INDEX idx_ngo_data_ngo_id ON ngo_data(ngo_id);
CREATE INDEX idx_homeless_people_volunteer_id ON homeless_people(volunteer_id);
CREATE INDEX idx_patients_healthcare_id ON patients(healthcare_id);
CREATE INDEX idx_food_donations_hotel_id ON food_donations(hotel_id);
CREATE INDEX idx_needs_ngo_id ON needs(ngo_id);
CREATE INDEX idx_donations_donor_id ON donations(donor_id);
CREATE INDEX idx_food_donations_status ON food_donations(status);
CREATE INDEX idx_donations_status ON donations(status);
CREATE INDEX idx_login_activities_user_id ON login_activities(user_id);
CREATE INDEX idx_login_activities_email ON login_activities(email);
CREATE INDEX idx_login_activities_login_time ON login_activities(login_time);

-- ============================================================================
-- AUTHENTICATION SQL QUERIES
-- ============================================================================

-- REGISTRATION QUERY
-- 1. Insert new user during registration
INSERT INTO users (name, email, phone, organization, role, password_hash)
VALUES ('User Name', 'user@example.com', '1234567890', 'Organization', 'donor', 'hashed_password_hash');

-- Alternative: WITH RETURNING clause (to get the inserted user data back)
INSERT INTO users (name, email, phone, organization, role, password_hash)
VALUES ('User Name', 'user@example.com', '1234567890', 'Organization', 'donor', 'hashed_password_hash')
RETURNING id, name, email, role, created_at;

-- ============================================================================
-- LOGIN QUERY
-- ============================================================================

-- 2. Check if user exists and verify password
-- Query: Get user by email and password hash (for login)
SELECT id, name, email, role, phone, organization, created_at
FROM users
WHERE email = 'user@example.com' AND password_hash = 'hashed_password_hash';

-- Alternative: Just check if email exists (first step of login)
SELECT id, email, role, password_hash
FROM users
WHERE email = 'user@example.com';

-- ============================================================================
-- ADDITIONAL AUTH QUERIES
-- ============================================================================

-- 3. Check if email already registered (during registration validation)
SELECT EXISTS (
    SELECT 1 FROM users WHERE email = 'user@example.com'
) as email_exists;

-- 4. Update last login timestamp
UPDATE users
SET updated_at = CURRENT_TIMESTAMP
WHERE id = 'user_uuid_here'
RETURNING id, updated_at;

-- 5. Get user profile by ID (after login)
SELECT id, name, email, phone, organization, role, created_at, updated_at
FROM users
WHERE id = 'user_uuid_here';

-- 6. Update user password
UPDATE users
SET password_hash = 'new_hashed_password'
WHERE id = 'user_uuid_here'
RETURNING id, email, updated_at;

-- 7. Get user by ID and role (for session/authorization)
SELECT id, name, email, role
FROM users
WHERE id = 'user_uuid_here' AND role = 'donor';

-- 8. Logout (no database action needed, just clear session)
-- But if you want to track last logout:
UPDATE users
SET updated_at = CURRENT_TIMESTAMP
WHERE id = 'user_uuid_here';

-- ============================================================================
-- ROLE-BASED QUERIES (After Login)
-- ============================================================================

-- 9. Get all users by role (Admin dashboard)
SELECT id, name, email, phone, organization, role, created_at
FROM users
WHERE role = 'volunteer'
ORDER BY created_at DESC;

-- 10. Get volunteer-specific data (after volunteer login)
SELECT u.id, u.name, u.email, v.availability, v.skills, v.hours_volunteered
FROM users u
LEFT JOIN volunteer_data v ON u.id = v.volunteer_id
WHERE u.id = 'volunteer_uuid_here';

-- 11. Get healthcare-specific data (after healthcare login)
SELECT u.id, u.name, u.email, h.facility_name, h.services, h.bed_capacity, h.current_patients
FROM users u
LEFT JOIN healthcare_data h ON u.id = h.healthcare_id
WHERE u.id = 'healthcare_uuid_here';

-- 12. Get donor-specific data (after donor login)
SELECT u.id, u.name, u.email, COUNT(d.id) as total_donations, COALESCE(SUM(d.amount), 0) as total_donated
FROM users u
LEFT JOIN donations d ON u.id = d.donor_id
WHERE u.id = 'donor_uuid_here'
GROUP BY u.id, u.name, u.email;

-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Insert sample users for different roles
INSERT INTO users (name, email, phone, organization, role, password_hash) VALUES
('Admin User', 'admin@bridgecare.com', '9876543210', 'BridgeCare', 'admin', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
('Dr. Smith', 'doctor@healthcare.com', '5551234567', 'City Hospital', 'healthcare', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
('John Volunteer', 'john@volunteer.org', '5559876543', 'Community Aid', 'volunteer', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
('Hotel Manager', 'manager@hotel.com', '5552468135', 'Grand Hotel', 'hotel', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
('NGO Director', 'director@ngo.com', '5553692581', 'Help Foundation', 'ngo', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
('Jane Donor', 'jane@donor.com', '5554185926', 'Generous Giving', 'donor', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');

-- ============================================================================
-- APPOINTMENTS TABLE
-- Stores appointments booked for patients with healthcare providers
CREATE TABLE IF NOT EXISTS appointments (
    id TEXT PRIMARY KEY,
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    healthcare_provider_id UUID REFERENCES healthcare_providers(id) ON DELETE SET NULL,
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

CREATE INDEX IF NOT EXISTS idx_appointments_patient_id ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_provider_id ON appointments(healthcare_provider_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);

-- ============================================================================
-- HEALTHCARE_PROVIDERS TABLE
-- Stores hospitals, clinics and other provider details
CREATE TABLE IF NOT EXISTS healthcare_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100),
    address TEXT,
    contact_number VARCHAR(50),
    email VARCHAR(255),
    services TEXT,
    capacity INTEGER,
    current_load INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_healthcare_providers_name ON healthcare_providers(name);

-- TREATMENT HISTORY
CREATE TABLE IF NOT EXISTS treatment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id TEXT REFERENCES appointments(id) ON DELETE SET NULL,
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    ngo_id UUID REFERENCES users(id) ON DELETE SET NULL,
    diagnosis TEXT,
    prescription TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_treatment_history_patient_id ON treatment_history(patient_id);
CREATE INDEX IF NOT EXISTS idx_treatment_history_appointment_id ON treatment_history(appointment_id);

-- NGO NOTIFICATIONS (store prescriptions/notifications sent to NGOs)
CREATE TABLE IF NOT EXISTS ngo_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ngo_id UUID REFERENCES users(id) ON DELETE CASCADE,
    appointment_id TEXT,
    treatment_id UUID REFERENCES treatment_history(id) ON DELETE SET NULL,
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_ngo_notifications_ngo_id ON ngo_notifications(ngo_id);