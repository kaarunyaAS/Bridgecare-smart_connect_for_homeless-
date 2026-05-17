-- Tables required for the NGO dashboard UI.
-- Run this script in the Supabase SQL Editor before using the new screens.

-- Tracks homeless people recorded by NGOs/volunteers
create table if not exists homeless_people (
    id uuid primary key default gen_random_uuid(),
    ngo_id uuid references users(id) on delete set null,
    volunteer_id uuid references users(id) on delete set null,
    name text not null,
    age int,
    gender text,
    location text,
    health_status text,
    notes text,
    contact_info jsonb,
    created_at timestamptz default now()
);

-- People currently supported by the NGO (used by appointments)
create table if not exists patients (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    homeless_id text not null,
    age int,
    gender text,
    ngo_id uuid references users(id) on delete set null,
    contact_number text,
    is_active boolean default true,
    last_visit_date date,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
create index if not exists idx_patients_ngo_id on patients(ngo_id);
create unique index if not exists idx_patients_homeless_id on patients(homeless_id);

-- Food / hotel requests placed by NGOs against donations
create table if not exists meal_requests (
    id uuid primary key default gen_random_uuid(),
    ngo_id uuid references users(id) on delete cascade,
    donation_id uuid references donations(id) on delete set null,
    requested_quantity int not null,
    notes text,
    status text default 'pending',
    created_at timestamptz default now()
);
create index if not exists idx_meal_requests_ngo_id on meal_requests(ngo_id);
create index if not exists idx_meal_requests_status on meal_requests(status);

-- Extended volunteer metadata (optional)
create table if not exists volunteer_data (
    id uuid primary key default gen_random_uuid(),
    volunteer_id uuid references users(id) on delete cascade,
    assigned_region text,
    status text,
    hours_volunteered int default 0,
    people_helped int default 0,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
create unique index if not exists idx_volunteer_data_volunteer on volunteer_data(volunteer_id);
