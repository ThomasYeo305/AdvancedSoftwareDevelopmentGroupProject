-- ================================================================
-- PAMS — Paragon Apartment Management System
-- SQLite Schema + Seed Data
-- Open in: DB Browser for SQLite  /  any SQLite-compatible tool
-- ================================================================

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- ----------------------------------------------------------------
-- DROP existing tables (allows clean re-run)
-- ----------------------------------------------------------------
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS complaints;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS leases;
DROP TABLE IF EXISTS maintenance;
DROP TABLE IF EXISTS tenants;
DROP TABLE IF EXISTS apartments;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS locations;

-- ----------------------------------------------------------------
-- TABLE: locations
-- ----------------------------------------------------------------
CREATE TABLE locations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    created_at TEXT    NOT NULL DEFAULT (date('now'))
);

-- ----------------------------------------------------------------
-- TABLE: users  (RBAC — 5 roles, PBKDF2-SHA256 passwords)
-- ----------------------------------------------------------------
CREATE TABLE users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL UNIQUE,
    password   TEXT    NOT NULL,
    full_name  TEXT    NOT NULL,
    role       TEXT    NOT NULL CHECK(role IN (
                   'Administrator','Manager','Front-Desk Staff',
                   'Finance Manager','Maintenance Staff')),
    location   TEXT    NOT NULL,
    email      TEXT    NOT NULL DEFAULT '',
    active     INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (date('now'))
);

-- ----------------------------------------------------------------
-- TABLE: apartments
-- ----------------------------------------------------------------
CREATE TABLE apartments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    apt_number   TEXT    NOT NULL UNIQUE,
    location     TEXT    NOT NULL,
    type         TEXT    NOT NULL,
    rooms        INTEGER NOT NULL DEFAULT 1,
    monthly_rent REAL    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'Vacant'
                     CHECK(status IN ('Vacant','Occupied','Maintenance')),
    floor        INTEGER NOT NULL DEFAULT 1,
    description  TEXT    NOT NULL DEFAULT ''
);

-- ----------------------------------------------------------------
-- TABLE: tenants
-- ----------------------------------------------------------------
CREATE TABLE tenants (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    ni_number              TEXT    NOT NULL UNIQUE,
    full_name              TEXT    NOT NULL,
    phone                  TEXT    NOT NULL DEFAULT '',
    email                  TEXT    NOT NULL DEFAULT '',
    occupation             TEXT    NOT NULL DEFAULT '',
    reference              TEXT    NOT NULL DEFAULT '',
    apartment_requirements TEXT    NOT NULL DEFAULT '',
    apt_id                 INTEGER REFERENCES apartments(id) ON DELETE SET NULL,
    lease_start            TEXT,
    lease_end              TEXT,
    deposit                REAL    NOT NULL DEFAULT 0,
    monthly_rent           REAL    NOT NULL DEFAULT 0,
    status                 TEXT    NOT NULL DEFAULT 'Active'
                               CHECK(status IN ('Active','Leaving','Inactive','Archived')),
    notes                  TEXT    NOT NULL DEFAULT '',
    early_leave_notice_date TEXT,
    created_at             TEXT    NOT NULL DEFAULT (date('now'))
);

-- ----------------------------------------------------------------
-- TABLE: leases
-- ----------------------------------------------------------------
CREATE TABLE leases (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id              INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    apartment_id           INTEGER NOT NULL REFERENCES apartments(id) ON DELETE CASCADE,
    start_date             TEXT    NOT NULL,
    end_date               TEXT    NOT NULL,
    monthly_rent           REAL    NOT NULL,
    deposit                REAL    NOT NULL DEFAULT 0,
    status                 TEXT    NOT NULL DEFAULT 'Active'
                               CHECK(status IN ('Active','Terminated','Expired','Archived')),
    early_termination_date TEXT,
    penalty_amount         REAL    DEFAULT 0,
    created_at             TEXT    NOT NULL DEFAULT (date('now'))
);

-- ----------------------------------------------------------------
-- TABLE: payments  (invoices + receipts)
-- ----------------------------------------------------------------
CREATE TABLE payments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lease_id      INTEGER REFERENCES leases(id) ON DELETE SET NULL,
    amount        REAL    NOT NULL,
    due_date      TEXT    NOT NULL,
    paid_date     TEXT,
    status        TEXT    NOT NULL DEFAULT 'Pending'
                      CHECK(status IN ('Pending','Paid','Overdue')),
    type          TEXT    NOT NULL DEFAULT 'Rent',
    late_notified INTEGER NOT NULL DEFAULT 0,
    notes         TEXT    NOT NULL DEFAULT ''
);

-- ----------------------------------------------------------------
-- TABLE: maintenance
-- ----------------------------------------------------------------
CREATE TABLE maintenance (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id          INTEGER REFERENCES tenants(id) ON DELETE SET NULL,
    apt_id             INTEGER REFERENCES apartments(id) ON DELETE CASCADE,
    title              TEXT    NOT NULL,
    description        TEXT    NOT NULL DEFAULT '',
    priority           TEXT    NOT NULL DEFAULT 'Medium'
                           CHECK(priority IN ('Low','Medium','High','Critical')),
    status             TEXT    NOT NULL DEFAULT 'Open'
                           CHECK(status IN ('Open','Assigned','Scheduled','In Progress','Resolved')),
    reported_date      TEXT    NOT NULL DEFAULT (date('now')),
    scheduled_date     TEXT,
    resolved_date      TEXT,
    assigned_to        INTEGER REFERENCES users(id) ON DELETE SET NULL,
    cost               REAL    NOT NULL DEFAULT 0,
    time_spent         REAL    NOT NULL DEFAULT 0,
    communication_sent INTEGER NOT NULL DEFAULT 0,
    notes              TEXT    NOT NULL DEFAULT ''
);

-- ----------------------------------------------------------------
-- TABLE: complaints
-- ----------------------------------------------------------------
CREATE TABLE complaints (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    status      TEXT    NOT NULL DEFAULT 'Open'
                    CHECK(status IN ('Open','In Progress','Resolved')),
    created_at  TEXT    NOT NULL DEFAULT (date('now')),
    resolved_at TEXT
);

-- ----------------------------------------------------------------
-- TABLE: audit_log  (security / NFR1)
-- ----------------------------------------------------------------
CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    action      TEXT    NOT NULL,
    entity_type TEXT,
    entity_id   TEXT,
    old_value   TEXT,
    new_value   TEXT,
    timestamp   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------
-- INDEXES  (performance / NFR4)
-- ----------------------------------------------------------------
CREATE INDEX idx_tenants_apt       ON tenants(apt_id);
CREATE INDEX idx_tenants_status    ON tenants(status);
CREATE INDEX idx_payments_tenant   ON payments(tenant_id);
CREATE INDEX idx_payments_status   ON payments(status);
CREATE INDEX idx_payments_due      ON payments(due_date);
CREATE INDEX idx_maint_apt         ON maintenance(apt_id);
CREATE INDEX idx_maint_status      ON maintenance(status);
CREATE INDEX idx_complaints_tenant ON complaints(tenant_id);


-- ----------------------------------------------------------------
-- SEED DATA
-- ----------------------------------------------------------------

-- Locations
INSERT INTO locations(name) VALUES('Bristol');
INSERT INTO locations(name) VALUES('Cardiff');
INSERT INTO locations(name) VALUES('London');
INSERT INTO locations(name) VALUES('Manchester');

-- Users  (passwords are PBKDF2-SHA256 hashed)
-- Credentials:  admin_bristol/admin123  manager/manager123
--               frontdesk1/front123     finance1/finance123
--               maint1/maint123
INSERT INTO users(username,password,full_name,role,location,email) VALUES('admin_bristol','017daef6ac5d2602e9ed501a027e1e5d1f88657e37c0b4f6194f6c5cf5668a5b','Alice Morrison','Administrator','Bristol','alice@paragon.com');
INSERT INTO users(username,password,full_name,role,location,email) VALUES('admin_london','017daef6ac5d2602e9ed501a027e1e5d1f88657e37c0b4f6194f6c5cf5668a5b','David Okafor','Administrator','London','david@paragon.com');
INSERT INTO users(username,password,full_name,role,location,email) VALUES('admin_manc','017daef6ac5d2602e9ed501a027e1e5d1f88657e37c0b4f6194f6c5cf5668a5b','Fiona Walsh','Administrator','Manchester','fiona@paragon.com');
INSERT INTO users(username,password,full_name,role,location,email) VALUES('admin_cardiff','017daef6ac5d2602e9ed501a027e1e5d1f88657e37c0b4f6194f6c5cf5668a5b','Rhys Evans','Administrator','Cardiff','rhys@paragon.com');
INSERT INTO users(username,password,full_name,role,location,email) VALUES('manager','7e0e7e5b6cea4c4f4822dd6f5d39828b8f41f4f267116e2d02fa69f353dac9d3','Sarah Whitfield','Manager','Bristol','sarah@paragon.com');
INSERT INTO users(username,password,full_name,role,location,email) VALUES('frontdesk1','7b4cf7c10281a0aaac1411f483943146c8e9cee5729f6bf149261440502740d1','James Patel','Front-Desk Staff','Bristol','james@paragon.com');
INSERT INTO users(username,password,full_name,role,location,email) VALUES('frontdesk2','7b4cf7c10281a0aaac1411f483943146c8e9cee5729f6bf149261440502740d1','Lily Chen','Front-Desk Staff','Manchester','lily@paragon.com');
INSERT INTO users(username,password,full_name,role,location,email) VALUES('finance1','1c1b42ab802e26c8a9ce73afa19cfc4566db918050a24ce2aacd741e3c3a2f27','Robert Hughes','Finance Manager','Bristol','robert@paragon.com');
INSERT INTO users(username,password,full_name,role,location,email) VALUES('finance2','1c1b42ab802e26c8a9ce73afa19cfc4566db918050a24ce2aacd741e3c3a2f27','Natasha Peters','Finance Manager','London','natasha@paragon.com');
INSERT INTO users(username,password,full_name,role,location,email) VALUES('maint1','a04a6acdfb59372b3c76a4f2481c5f07a8425b3898c968151f64a2d234899d4b','Carlos Rivera','Maintenance Staff','Bristol','carlos@paragon.com');
INSERT INTO users(username,password,full_name,role,location,email) VALUES('maint2','a04a6acdfb59372b3c76a4f2481c5f07a8425b3898c968151f64a2d234899d4b','Priya Singh','Maintenance Staff','London','priya@paragon.com');

-- Apartments
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-101','Bristol','Studio',1,850.0,'Occupied',1,'Modern studio with open-plan living');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-102','Bristol','1-Bedroom',1,1050.0,'Occupied',1,'Bright 1-bed with private balcony');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-103','Bristol','2-Bedroom',2,1400.0,'Vacant',1,'Spacious 2-bed, freshly renovated');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-201','Bristol','2-Bedroom',2,1350.0,'Occupied',2,'South-facing 2-bed, river views');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-202','Bristol','3-Bedroom',3,1800.0,'Occupied',2,'Large family unit with garden access');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-301','Bristol','Penthouse',4,3200.0,'Vacant',3,'Luxury penthouse, 360-degree views');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-104','Bristol','Studio',1,820.0,'Maintenance',1,'Undergoing refurbishment');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-L01','London','Studio',1,1400.0,'Occupied',1,'Bridge view studio, zone 1');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-L02','London','1-Bedroom',1,1750.0,'Occupied',1,'Prime Shoreditch location');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-L03','London','2-Bedroom',2,2400.0,'Vacant',2,'Excellent transport links');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-L04','London','3-Bedroom',3,3100.0,'Occupied',3,'Luxury flat, concierge service');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-M01','Manchester','2-Bedroom',2,1100.0,'Occupied',1,'City centre, close to amenities');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-M02','Manchester','1-Bedroom',1,900.0,'Vacant',1,'Northern Quarter, character property');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-M03','Manchester','Studio',1,750.0,'Occupied',1,'Compact modern studio');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-C01','Cardiff','1-Bedroom',1,850.0,'Occupied',1,'Cardiff Bay area, waterfront');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-C02','Cardiff','2-Bedroom',2,1100.0,'Vacant',1,'Quiet residential area, parking included');
INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES('APT-C03','Cardiff','Studio',1,700.0,'Occupied',1,'City centre, compact and efficient');

-- Tenants
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-AA123456A','Oliver Thompson','07700111001','oliver@email.com','Software Engineer','John Smith','1-Bedroom',2,'2025-10-06','2027-03-30',1050.0,1050.0,'Active','');
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-BB234567B','Emma Williams','07700111002','emma@email.com','Nurse','Dr. Jones','1-Bedroom',1,'2026-01-04','2026-12-30',850.0,850.0,'Active','');
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-CC345678C','Noah Brown','07700111003','noah@email.com','Teacher','Mary Green','2-Bedroom',4,'2026-03-05','2027-02-28',1350.0,1350.0,'Active','');
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-DD456789D','Sophia Davis','07700111004','sophia@email.com','Accountant','Peter Davis','3-Bedroom',5,'2025-12-05','2026-11-30',1800.0,1800.0,'Active','');
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-EE567890E','Liam Wilson','07700111005','liam@email.com','Architect','Jane Wilson','Studio',8,'2026-02-03','2027-01-29',1400.0,1400.0,'Active','');
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-FF678901F','Isabella Moore','07700111006','isab@email.com','Marketing Manager','Tom Moore','1-Bedroom',9,'2025-11-05','2026-10-31',1750.0,1750.0,'Active','');
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-GG789012G','Mason Taylor','07700111007','mason@email.com','Chef','Cathy Taylor','2-Bedroom',12,'2025-10-06','2026-10-01',1100.0,1100.0,'Active','');
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-HH890123H','Ava Anderson','07700111008','ava@email.com','Solicitor','Bob Anderson','1-Bedroom',15,'2026-01-04','2026-12-30',850.0,850.0,'Active','');
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-II901234I','Jack Robinson','07700111009','jack@email.com','Doctor','NHS Trust','3-Bedroom',11,'2026-02-03','2027-01-29',3100.0,3100.0,'Active','');
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-JJ012345J','Zoe Martinez','07700111010','zoe@email.com','Designer','Creative Co','Studio',14,'2026-03-05','2027-02-28',750.0,750.0,'Active','');
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-KK123456K','Harry Evans','07700111011','harry@email.com','Engineer','Rhys Evans','Studio',17,'2025-12-05','2026-11-30',700.0,700.0,'Active','');
INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,status,notes) VALUES('NI-LL234567L','Sophie Clarke','07700111012','sophie@email.com','Pharmacist','NHS Trust','2-Bedroom',10,'2026-03-05','2027-02-28',2400.0,2400.0,'Active','');

-- Leases
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(1,2,'2025-10-06','2027-03-30',1050.0,1050.0,'Active');
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(2,1,'2026-01-04','2026-12-30',850.0,850.0,'Active');
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(3,4,'2026-03-05','2027-02-28',1350.0,1350.0,'Active');
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(4,5,'2025-12-05','2026-11-30',1800.0,1800.0,'Active');
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(5,8,'2026-02-03','2027-01-29',1400.0,1400.0,'Active');
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(6,9,'2025-11-05','2026-10-31',1750.0,1750.0,'Active');
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(7,12,'2025-10-06','2026-10-01',1100.0,1100.0,'Active');
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(8,15,'2026-01-04','2026-12-30',850.0,850.0,'Active');
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(9,11,'2026-02-03','2027-01-29',3100.0,3100.0,'Active');
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(10,14,'2026-03-05','2027-02-28',750.0,750.0,'Active');
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(11,17,'2025-12-05','2026-11-30',700.0,700.0,'Active');
INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status) VALUES(12,10,'2026-03-05','2027-02-28',2400.0,2400.0,'Active');

-- Payments (3 months history per tenant)
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(1,1050.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(1,1050.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(1,1050.0,'2026-03-01',NULL,'Overdue','Rent',1);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(2,850.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(2,850.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(2,850.0,'2026-03-01',NULL,'Overdue','Rent',1);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(3,1350.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(3,1350.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(3,1350.0,'2026-03-01',NULL,'Overdue','Rent',1);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(4,1800.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(4,1800.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(4,1800.0,'2026-03-01',NULL,'Overdue','Rent',1);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(5,1400.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(5,1400.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(5,1400.0,'2026-03-01',NULL,'Overdue','Rent',1);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(6,1750.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(6,1750.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(6,1750.0,'2026-03-01',NULL,'Overdue','Rent',1);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(7,1100.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(7,1100.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(7,1100.0,'2026-03-01',NULL,'Overdue','Rent',1);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(8,850.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(8,850.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(8,850.0,'2026-03-01',NULL,'Overdue','Rent',1);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(9,3100.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(9,3100.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(9,3100.0,'2026-03-01',NULL,'Overdue','Rent',1);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(10,750.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(10,750.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(10,750.0,'2026-03-01',NULL,'Overdue','Rent',1);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(11,700.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(11,700.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(11,700.0,'2026-03-01',NULL,'Overdue','Rent',1);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(12,2400.0,'2026-01-01','2026-01-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(12,2400.0,'2026-02-01','2026-02-01','Paid','Rent',0);
INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified) VALUES(12,2400.0,'2026-03-01',NULL,'Overdue','Rent',1);

-- Maintenance Requests
INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,communication_sent,notes) VALUES(1,2,'Leaking Tap','Kitchen tap dripping continuously','High','Resolved','2026-03-15','2026-03-17','2026-03-18',10,120.0,3.0,1,'Parts replaced');
INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,communication_sent,notes) VALUES(2,1,'Broken Heater','Radiator not working in bedroom','High','In Progress','2026-03-30','2026-04-06',NULL,10,0.0,0.0,1,'Replacement part ordered');
INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,communication_sent,notes) VALUES(3,4,'Cracked Window','Bedroom window has a crack','Medium','Open','2026-04-02',NULL,NULL,10,0.0,0.0,0,'');
INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,communication_sent,notes) VALUES(4,5,'Lift Fault','Lift on floor 2 not stopping at floor','Critical','Open','2026-04-03',NULL,NULL,10,0.0,0.0,0,'');
INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,communication_sent,notes) VALUES(5,8,'Pest Control','Cockroaches reported in kitchen','Medium','Resolved','2026-03-05','2026-03-09','2026-03-10',11,200.0,5.0,1,'Professional extermination completed');
INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,communication_sent,notes) VALUES(6,9,'Faulty Electrics','Intermittent power cuts in living room','High','In Progress','2026-04-01','2026-04-05',NULL,11,0.0,0.0,1,'Electrician booked');
INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,communication_sent,notes) VALUES(7,12,'Damp Patch','Damp patch on bathroom ceiling','Medium','Assigned','2026-03-28','2026-04-07',NULL,10,0.0,0.0,1,'Damp specialist assigned');
INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,communication_sent,notes) VALUES(8,15,'Blocked Drain','Shower drain slow to empty','Low','Resolved','2026-03-21','2026-03-23','2026-03-23',10,45.0,1.5,1,'Drain rod cleared blockage');
INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,communication_sent,notes) VALUES(9,11,'Intercom Fault','Intercom system not responding','Medium','Scheduled','2026-03-31','2026-04-09',NULL,11,0.0,0.0,1,'Engineer visit booked');
INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,communication_sent,notes) VALUES(10,14,'Mould in Bathroom','Black mould appearing on ceiling','High','Open','2026-04-01',NULL,NULL,10,0.0,0.0,0,'');

-- Complaints
INSERT INTO complaints(tenant_id,title,description,status,created_at,resolved_at) VALUES(1,'Noisy Neighbours','Upstairs neighbours very loud past midnight','Open','2026-04-01',NULL);
INSERT INTO complaints(tenant_id,title,description,status,created_at,resolved_at) VALUES(3,'Parking Issue','Another tenant using my allocated parking space','Open','2026-04-02',NULL);
INSERT INTO complaints(tenant_id,title,description,status,created_at,resolved_at) VALUES(5,'Water Pressure Low','Hot water pressure has been very low for a week','Resolved','2026-03-25','2026-03-27');
INSERT INTO complaints(tenant_id,title,description,status,created_at,resolved_at) VALUES(7,'Rubbish Collection','Communal bins not collected for two weeks','In Progress','2026-03-30',NULL);
INSERT INTO complaints(tenant_id,title,description,status,created_at,resolved_at) VALUES(9,'Intercom Broken','Front door intercom system not working','Open','2026-04-03',NULL);
INSERT INTO complaints(tenant_id,title,description,status,created_at,resolved_at) VALUES(4,'Heating Insufficient','Central heating inadequate in cold weather','In Progress','2026-03-29',NULL);
INSERT INTO complaints(tenant_id,title,description,status,created_at,resolved_at) VALUES(10,'Pest Sighting','Mice spotted in communal hallway','Open','2026-04-02',NULL);
INSERT INTO complaints(tenant_id,title,description,status,created_at,resolved_at) VALUES(12,'Neighbour Dispute','Dispute over shared utility bills','Resolved','2026-03-20','2026-03-25');

COMMIT;

PRAGMA foreign_keys = ON;

-- ================================================================
-- Login credentials summary
-- ================================================================
-- Role               Username          Password
-- Administrator      admin_bristol     admin123
-- Administrator      admin_london      admin123
-- Administrator      admin_manc        admin123
-- Administrator      admin_cardiff     admin123
-- Manager            manager           manager123
-- Front-Desk Staff   frontdesk1        front123
-- Front-Desk Staff   frontdesk2        front123
-- Finance Manager    finance1          finance123
-- Finance Manager    finance2          finance123
-- Maintenance Staff  maint1            maint123
-- Maintenance Staff  maint2            maint123
-- ================================================================