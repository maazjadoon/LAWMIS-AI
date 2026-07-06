-- ═══════════════════════════════════════════════════════════════════════════
--  LAWMIS Database Schema — PostgreSQL
--  Auto-executed by Postgres on first container start (via docker-entrypoint-initdb.d)
-- ═══════════════════════════════════════════════════════════════════════════

-- ── Enum types ───────────────────────────────────────────────────────────────
CREATE TYPE status_enum AS ENUM (
    'Pending', 'Under Review', 'Approved', 'Rejected', 'Suspended', 'Expired'
);

-- ── Workshops ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.workshops (
    workshop_id         SERIAL PRIMARY KEY,
    profile_id          INTEGER,
    workshop_name       VARCHAR(255) NOT NULL,
    workshop_code       VARCHAR(100),
    workshop_owner_name VARCHAR(255),
    workshop_email      VARCHAR(255),
    workshop_phone      VARCHAR(50),
    plot_no             VARCHAR(100),
    street_address      TEXT,
    area_locality       VARCHAR(255),
    city                VARCHAR(100),
    tehsil              VARCHAR(100),
    district            VARCHAR(100),
    province            VARCHAR(100),
    postal_code         VARCHAR(20),
    latitude            NUMERIC(10, 7),
    longitude           NUMERIC(10, 7),
    area_type           VARCHAR(50),
    total_area_sqft     NUMERIC(12, 2),
    workshop_type       VARCHAR(100),
    number_of_bays      INTEGER,
    application_date    DATE,
    submitted_at        TIMESTAMP,
    approved_at         TIMESTAMP,
    workshop_status     status_enum DEFAULT 'Pending',
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- ── RTA Inspections ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.rta_inspections (
    inspection_id           SERIAL PRIMARY KEY,
    workshop_id             INTEGER REFERENCES public.workshops(workshop_id),
    inspection_date         DATE,
    inspection_time         TIME,
    inspecting_officer      VARCHAR(255),
    officer_designation     VARCHAR(255),
    visit_number            INTEGER DEFAULT 1,
    score_equipment         NUMERIC(5, 2),
    score_infrastructure    NUMERIC(5, 2),
    score_safety            NUMERIC(5, 2),
    score_staff_competency  NUMERIC(5, 2),
    score_record_keeping    NUMERIC(5, 2),
    total_score             NUMERIC(5, 2),
    inspection_result       VARCHAR(50),
    remarks                 TEXT,
    follow_up_required      BOOLEAN DEFAULT FALSE,
    follow_up_date          DATE,
    created_at              TIMESTAMP DEFAULT NOW()
);

-- ── Payments ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.payments (
    payment_id          SERIAL PRIMARY KEY,
    workshop_id         INTEGER REFERENCES public.workshops(workshop_id),
    profile_id          INTEGER,
    psid_number         VARCHAR(100),
    fee_head            VARCHAR(255),
    fee_amount          NUMERIC(12, 2),
    currency            VARCHAR(10) DEFAULT 'PKR',
    payment_mode        VARCHAR(100),
    bank_name           VARCHAR(255),
    transaction_ref     VARCHAR(255),
    challan_no          VARCHAR(255),
    payment_date        DATE,
    payment_time        TIME,
    payment_status      VARCHAR(50) DEFAULT 'Pending',
    payment_verified_at TIMESTAMP,
    verified_by         VARCHAR(255),
    remarks             TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

-- ── Workshop Licenses ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.workshop_licenses (
    license_id          SERIAL PRIMARY KEY,
    workshop_id         INTEGER REFERENCES public.workshops(workshop_id),
    inspection_id       INTEGER REFERENCES public.rta_inspections(inspection_id),
    payment_id          INTEGER REFERENCES public.payments(payment_id),
    license_number      VARCHAR(100) UNIQUE,
    license_category    VARCHAR(100),
    issue_date          DATE,
    valid_from          DATE,
    valid_until         DATE,
    issued_by_officer   VARCHAR(255),
    issuing_authority   VARCHAR(255),
    license_status      status_enum DEFAULT 'Pending',
    renewal_count       INTEGER DEFAULT 0,
    last_renewal_date   DATE,
    created_at          TIMESTAMP DEFAULT NOW()
);

-- ── Emission Tests ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.emission_tests (
    test_id                 SERIAL PRIMARY KEY,
    workshop_id             INTEGER REFERENCES public.workshops(workshop_id),
    vehicle_id              VARCHAR(100),
    license_id              INTEGER REFERENCES public.workshop_licenses(license_id),
    test_date               DATE,
    test_time               TIME,
    test_datetime           TIMESTAMP,
    technician_name         VARCHAR(255),
    equipment_serial        VARCHAR(100),
    co_pct                  NUMERIC(6, 3),
    co2_pct                 NUMERIC(6, 3),
    co_co2_pct              NUMERIC(6, 3),
    hc_ppm                  NUMERIC(8, 2),
    nox_ppm                 NUMERIC(8, 2),
    o2_pct                  NUMERIC(6, 3),
    lambda                  NUMERIC(6, 3),
    engine_rpm              INTEGER,
    oil_temp_c              NUMERIC(5, 1),
    co_limit_pct            NUMERIC(6, 3),
    hc_limit_ppm            NUMERIC(8, 2),
    nox_limit_ppm           NUMERIC(8, 2),
    test_result             VARCHAR(50),
    certificate_no          VARCHAR(100),
    certificate_valid_until DATE,
    remarks                 TEXT,
    created_at              TIMESTAMP DEFAULT NOW()
);

-- ── Indexes for common query patterns ────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_workshops_status    ON public.workshops(workshop_status);
CREATE INDEX IF NOT EXISTS idx_workshops_city      ON public.workshops(city);
CREATE INDEX IF NOT EXISTS idx_workshops_district  ON public.workshops(district);
CREATE INDEX IF NOT EXISTS idx_licenses_status     ON public.workshop_licenses(license_status);
CREATE INDEX IF NOT EXISTS idx_licenses_valid_until ON public.workshop_licenses(valid_until);
CREATE INDEX IF NOT EXISTS idx_payments_status     ON public.payments(payment_status);
CREATE INDEX IF NOT EXISTS idx_emission_workshop   ON public.emission_tests(workshop_id);
CREATE INDEX IF NOT EXISTS idx_inspection_workshop ON public.rta_inspections(workshop_id);
