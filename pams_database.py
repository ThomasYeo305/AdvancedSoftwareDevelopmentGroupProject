#!/usr/bin/env python3
# ================================================================
# PAMS — pams_database.py
# Paragon Apartment Management System
# Standalone SQLite Database Builder
#
# Run this script once to create and seed pams.db:
#     python pams_database.py
#
# It will create pams.db in the same folder as this script.
# Safe to re-run — drops and recreates all tables cleanly.
#
# Module: UFCF8S-30-2  Advanced Software Development
# ================================================================

import sqlite3
import hashlib
import datetime
import os

# ── Config ──────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pams.db")
SALT    = b"PAMS_Paragon_Secure_2025"

# ── Helpers ─────────────────────────────────────────────────
def hsh(password: str) -> str:
    """PBKDF2-SHA256 password hash — matches database.py auth."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), SALT, 100_000).hex()

def d(offset: int = 0) -> str:
    """Return ISO date string relative to today."""
    return (datetime.date.today() + datetime.timedelta(days=offset)).isoformat()

def lease_range(back_months: int, fwd_months: int):
    """Return (start, end) ISO date strings for a lease period."""
    start = (datetime.date.today() - datetime.timedelta(days=30 * back_months)).isoformat()
    end   = (datetime.date.today() + datetime.timedelta(days=30 * fwd_months)).isoformat()
    return start, end


# ================================================================
# SCHEMA
# ================================================================
SCHEMA = """
PRAGMA foreign_keys = OFF;

-- ── Drop existing tables (clean re-run) ─────────────────────
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS complaints;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS leases;
DROP TABLE IF EXISTS maintenance;
DROP TABLE IF EXISTS tenants;
DROP TABLE IF EXISTS apartments;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS locations;

-- ── locations ────────────────────────────────────────────────
CREATE TABLE locations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    created_at TEXT    NOT NULL DEFAULT (date('now'))
);

-- ── users  (RBAC — 5 roles, PBKDF2-SHA256 passwords) ────────
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

-- ── apartments ───────────────────────────────────────────────
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

-- ── tenants ──────────────────────────────────────────────────
CREATE TABLE tenants (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ni_number               TEXT    NOT NULL UNIQUE,
    full_name               TEXT    NOT NULL,
    phone                   TEXT    NOT NULL DEFAULT '',
    email                   TEXT    NOT NULL DEFAULT '',
    occupation              TEXT    NOT NULL DEFAULT '',
    reference               TEXT    NOT NULL DEFAULT '',
    apartment_requirements  TEXT    NOT NULL DEFAULT '',
    apt_id                  INTEGER REFERENCES apartments(id) ON DELETE SET NULL,
    lease_start             TEXT,
    lease_end               TEXT,
    deposit                 REAL    NOT NULL DEFAULT 0,
    monthly_rent            REAL    NOT NULL DEFAULT 0,
    status                  TEXT    NOT NULL DEFAULT 'Active'
                                CHECK(status IN ('Active','Leaving','Inactive','Archived')),
    notes                   TEXT    NOT NULL DEFAULT '',
    early_leave_notice_date TEXT,
    created_at              TEXT    NOT NULL DEFAULT (date('now'))
);

-- ── leases ───────────────────────────────────────────────────
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

-- ── payments  (invoices + receipts) ─────────────────────────
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

-- ── maintenance ──────────────────────────────────────────────
CREATE TABLE maintenance (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id          INTEGER REFERENCES tenants(id)    ON DELETE SET NULL,
    apt_id             INTEGER REFERENCES apartments(id)  ON DELETE CASCADE,
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

-- ── complaints ───────────────────────────────────────────────
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

-- ── audit_log  (security / NFR1) ────────────────────────────
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

-- ── indexes  (performance / NFR4) ───────────────────────────
CREATE INDEX idx_tenants_apt       ON tenants(apt_id);
CREATE INDEX idx_tenants_status    ON tenants(status);
CREATE INDEX idx_payments_tenant   ON payments(tenant_id);
CREATE INDEX idx_payments_status   ON payments(status);
CREATE INDEX idx_payments_due      ON payments(due_date);
CREATE INDEX idx_maint_apt         ON maintenance(apt_id);
CREATE INDEX idx_maint_status      ON maintenance(status);
CREATE INDEX idx_complaints_tenant ON complaints(tenant_id);

PRAGMA foreign_keys = ON;
"""


# ================================================================
# SEED DATA
# ================================================================
def seed(conn: sqlite3.Connection):
    cur = conn.cursor()

    # ── Locations ────────────────────────────────────────────
    locations = ["Bristol", "Cardiff", "London", "Manchester"]
    cur.executemany(
        "INSERT INTO locations(name) VALUES(?)",
        [(loc,) for loc in locations]
    )

    # ── Users ────────────────────────────────────────────────
    # Format: (username, password, full_name, role, location, email)
    users = [
        ("admin_bristol", hsh("admin123"),   "Alice Morrison",  "Administrator",    "Bristol",    "alice@paragon.com"),
        ("admin_london",  hsh("admin123"),   "David Okafor",    "Administrator",    "London",     "david@paragon.com"),
        ("admin_manc",    hsh("admin123"),   "Fiona Walsh",     "Administrator",    "Manchester", "fiona@paragon.com"),
        ("admin_cardiff", hsh("admin123"),   "Rhys Evans",      "Administrator",    "Cardiff",    "rhys@paragon.com"),
        ("manager",       hsh("manager123"), "Sarah Whitfield", "Manager",          "Bristol",    "sarah@paragon.com"),
        ("frontdesk1",    hsh("front123"),   "James Patel",     "Front-Desk Staff", "Bristol",    "james@paragon.com"),
        ("frontdesk2",    hsh("front123"),   "Lily Chen",       "Front-Desk Staff", "Manchester", "lily@paragon.com"),
        ("frontdesk3",    hsh("front123"),   "Amara Diallo",    "Front-Desk Staff", "London",     "amara@paragon.com"),
        ("frontdesk4",    hsh("front123"),   "Sian Hughes",     "Front-Desk Staff", "Cardiff",    "sian@paragon.com"),
        ("finance1",      hsh("finance123"), "Robert Hughes",   "Finance Manager",  "Bristol",    "robert@paragon.com"),
        ("finance2",      hsh("finance123"), "Natasha Peters",  "Finance Manager",  "London",     "natasha@paragon.com"),
        ("maint1",        hsh("maint123"),   "Carlos Rivera",   "Maintenance Staff","Bristol",    "carlos@paragon.com"),
        ("maint2",        hsh("maint123"),   "Priya Singh",     "Maintenance Staff","London",     "priya@paragon.com"),
        ("maint3",        hsh("maint123"),   "Tom Bradley",     "Maintenance Staff","Manchester", "tom@paragon.com"),
        ("maint4",        hsh("maint123"),   "Kezia Mensah",    "Maintenance Staff","Cardiff",    "kezia@paragon.com"),
    ]
    cur.executemany(
        "INSERT INTO users(username,password,full_name,role,location,email) VALUES(?,?,?,?,?,?)",
        users
    )

    # ── Apartments ───────────────────────────────────────────
    # Format: (apt_number, location, type, rooms, monthly_rent, status, floor, description)
    apartments = [
        # Bristol
        ("APT-101", "Bristol", "Studio",    1,  850.0, "Occupied",   1, "Modern studio with open-plan living"),
        ("APT-102", "Bristol", "1-Bedroom", 1, 1050.0, "Occupied",   1, "Bright 1-bed with private balcony"),
        ("APT-103", "Bristol", "2-Bedroom", 2, 1400.0, "Vacant",     1, "Spacious 2-bed, freshly renovated"),
        ("APT-104", "Bristol", "Studio",    1,  820.0, "Maintenance",1, "Undergoing full refurbishment"),
        ("APT-201", "Bristol", "2-Bedroom", 2, 1350.0, "Occupied",   2, "South-facing 2-bed with river views"),
        ("APT-202", "Bristol", "3-Bedroom", 3, 1800.0, "Occupied",   2, "Large family unit with garden access"),
        ("APT-203", "Bristol", "1-Bedroom", 1, 1100.0, "Vacant",     2, "Corner unit, lots of natural light"),
        ("APT-301", "Bristol", "Penthouse", 4, 3200.0, "Vacant",     3, "Luxury penthouse, 360-degree views"),
        # London
        ("APT-L01", "London",  "Studio",    1, 1400.0, "Occupied",   1, "Bridge view studio, Zone 1"),
        ("APT-L02", "London",  "1-Bedroom", 1, 1750.0, "Occupied",   1, "Prime Shoreditch location"),
        ("APT-L03", "London",  "2-Bedroom", 2, 2400.0, "Vacant",     2, "Excellent transport links"),
        ("APT-L04", "London",  "3-Bedroom", 3, 3100.0, "Occupied",   3, "Luxury flat with concierge service"),
        ("APT-L05", "London",  "Studio",    1, 1350.0, "Occupied",   1, "Compact studio, near Canary Wharf"),
        # Manchester
        ("APT-M01", "Manchester", "2-Bedroom", 2, 1100.0, "Occupied", 1, "City centre, close to Arndale"),
        ("APT-M02", "Manchester", "1-Bedroom", 1,  900.0, "Vacant",   1, "Northern Quarter, character property"),
        ("APT-M03", "Manchester", "Studio",    1,  750.0, "Occupied", 1, "Compact modern studio"),
        ("APT-M04", "Manchester", "2-Bedroom", 2, 1050.0, "Vacant",  2, "Ancoats area, newly built"),
        # Cardiff
        ("APT-C01", "Cardiff", "1-Bedroom", 1,  850.0, "Occupied",   1, "Cardiff Bay waterfront"),
        ("APT-C02", "Cardiff", "2-Bedroom", 2, 1100.0, "Vacant",     1, "Quiet residential, parking included"),
        ("APT-C03", "Cardiff", "Studio",    1,  700.0, "Occupied",   1, "City centre, compact and efficient"),
        ("APT-C04", "Cardiff", "1-Bedroom", 1,  950.0, "Occupied",   2, "Roath area, close to university"),
    ]
    cur.executemany(
        "INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description) VALUES(?,?,?,?,?,?,?,?)",
        apartments
    )

    # Build lookup maps
    cur.execute("SELECT id, apt_number FROM apartments")
    apt_map = {row[1]: row[0] for row in cur.fetchall()}

    cur.execute("SELECT id, username FROM users")
    user_map = {row[1]: row[0] for row in cur.fetchall()}

    # ── Tenants ──────────────────────────────────────────────
    # Format: (ni, full_name, phone, email, occupation, reference,
    #          apt_requirements, apt_number, back_months, fwd_months, deposit, rent)
    tenants_raw = [
        ("NI-AA123456A", "Oliver Thompson", "07700111001", "oliver@email.com",   "Software Engineer",  "John Smith",    "1-Bedroom", "APT-102",  6, 12, 1050.0, 1050.0),
        ("NI-BB234567B", "Emma Williams",   "07700111002", "emma@email.com",     "Nurse",              "Dr. Jones",     "1-Bedroom", "APT-101",  3,  9,  850.0,  850.0),
        ("NI-CC345678C", "Noah Brown",      "07700111003", "noah@email.com",     "Teacher",            "Mary Green",    "2-Bedroom", "APT-201",  1, 11, 1350.0, 1350.0),
        ("NI-DD456789D", "Sophia Davis",    "07700111004", "sophia@email.com",   "Accountant",         "Peter Davis",   "3-Bedroom", "APT-202",  4,  8, 1800.0, 1800.0),
        ("NI-EE567890E", "Liam Wilson",     "07700111005", "liam@email.com",     "Architect",          "Jane Wilson",   "Studio",    "APT-L01",  2, 10, 1400.0, 1400.0),
        ("NI-FF678901F", "Isabella Moore",  "07700111006", "isab@email.com",     "Marketing Manager",  "Tom Moore",     "1-Bedroom", "APT-L02",  5,  7, 1750.0, 1750.0),
        ("NI-GG789012G", "Mason Taylor",    "07700111007", "mason@email.com",    "Chef",               "Cathy Taylor",  "2-Bedroom", "APT-M01",  6,  6, 1100.0, 1100.0),
        ("NI-HH890123H", "Ava Anderson",    "07700111008", "ava@email.com",      "Solicitor",          "Bob Anderson",  "1-Bedroom", "APT-C01",  3,  9,  850.0,  850.0),
        ("NI-II901234I", "Jack Robinson",   "07700111009", "jack@email.com",     "Doctor",             "NHS Trust",     "3-Bedroom", "APT-L04",  2, 10, 3100.0, 3100.0),
        ("NI-JJ012345J", "Zoe Martinez",    "07700111010", "zoe@email.com",      "Designer",           "Creative Co",   "Studio",    "APT-M03",  1, 11,  750.0,  750.0),
        ("NI-KK123456K", "Harry Evans",     "07700111011", "harry@email.com",    "Engineer",           "Rhys Evans",    "Studio",    "APT-C03",  4,  8,  700.0,  700.0),
        ("NI-LL234567L", "Sophie Clarke",   "07700111012", "sophie@email.com",   "Pharmacist",         "NHS Trust",     "2-Bedroom", "APT-L05",  1, 11, 1350.0, 1350.0),
        ("NI-MM345678M", "Ethan Johnson",   "07700111013", "ethan@email.com",    "Data Analyst",       "Tech Corp",     "1-Bedroom", "APT-C04",  2,  8,  950.0,  950.0),
    ]

    tenant_id_map = {}
    for ni, name, phone, email, occ, ref, req, apt_num, back, fwd, dep, rent in tenants_raw:
        ls, le = lease_range(back, fwd)
        aid = apt_map[apt_num]
        cur.execute("""
            INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,
                apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent,
                status,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'Active','',date('now'))
        """, (ni, name, phone, email, occ, ref, req, aid, ls, le, dep, rent))
        tenant_id_map[ni] = cur.lastrowid

    # ── Leases ───────────────────────────────────────────────
    for ni, name, phone, email, occ, ref, req, apt_num, back, fwd, dep, rent in tenants_raw:
        ls, le = lease_range(back, fwd)
        tid = tenant_id_map[ni]
        aid = apt_map[apt_num]
        cur.execute("""
            INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,
                monthly_rent,deposit,status)
            VALUES(?,?,?,?,?,?,'Active')
        """, (tid, aid, ls, le, rent, dep))

    # ── Payments (6 months history per tenant) ────────────────
    today = datetime.date.today()
    for ni, *_, rent in tenants_raw:
        tid = tenant_id_map[ni]
        for m in range(6, 0, -1):
            due_dt  = (today - datetime.timedelta(days=30 * m)).replace(day=1)
            due     = due_dt.isoformat()
            if m > 1:
                paid_date = due
                status    = "Paid"
                notified  = 0
            else:
                paid_date = None
                status    = "Overdue"
                notified  = 1
            cur.execute("""
                INSERT INTO payments(tenant_id,amount,due_date,paid_date,
                    status,type,late_notified)
                VALUES(?,?,?,?,?,?,?)
            """, (tid, rent, due, paid_date, status, "Rent", notified))

    # ── Maintenance Requests ──────────────────────────────────
    # Format: (tenant_ni, apt_num, title, description, priority, status,
    #          rep_offset, sched_offset, res_offset, assigned_username,
    #          cost, time_spent, comm_sent, notes)
    maintenance_raw = [
        ("NI-AA123456A","APT-102","Leaking Tap",        "Kitchen tap dripping continuously",           "High",    "Resolved",   -20,-18,-17,"maint1",120.0,3.0, 1,"Parts replaced, tap fully functional"),
        ("NI-BB234567B","APT-101","Broken Heater",       "Bedroom radiator not working",               "High",    "In Progress", -5,  2,None,"maint1",  0.0,0.0, 1,"Replacement part ordered, ETA 3 days"),
        ("NI-CC345678C","APT-201","Cracked Window",      "Bedroom window has a hairline crack",        "Medium",  "Open",        -2,None,None,"maint1",  0.0,0.0, 0,""),
        ("NI-DD456789D","APT-202","Lift Fault",          "Floor 2 lift not stopping correctly",        "Critical","Open",        -1,None,None,"maint1",  0.0,0.0, 0,""),
        ("NI-EE567890E","APT-L01","Pest Control",        "Cockroaches reported in kitchen",            "Medium",  "Resolved",   -30,-26,-25,"maint2",200.0,5.0, 1,"Professional extermination completed"),
        ("NI-FF678901F","APT-L02","Faulty Electrics",    "Intermittent power in living room",          "High",    "In Progress", -3,  1,None,"maint2",  0.0,0.0, 1,"Electrician booked for site visit"),
        ("NI-GG789012G","APT-M01","Damp Patch",          "Damp patch on bathroom ceiling",             "Medium",  "Assigned",    -7,  3,None,"maint3",  0.0,0.0, 1,"Damp specialist assigned"),
        ("NI-HH890123H","APT-C01","Blocked Drain",       "Shower drain slow to empty",                 "Low",     "Resolved",   -14,-12,-12,"maint4", 45.0,1.5, 1,"Drain rod cleared the blockage"),
        ("NI-II901234I","APT-L04","Intercom Fault",      "Front door intercom not responding",         "Medium",  "Scheduled",   -4,  5,None,"maint2",  0.0,0.0, 1,"Engineer visit scheduled"),
        ("NI-JJ012345J","APT-M03","Mould in Bathroom",   "Black mould on ceiling near shower",         "High",    "Open",        -3,None,None,"maint3",  0.0,0.0, 0,""),
        ("NI-KK123456K","APT-C03","Broken Door Lock",    "Front door lock stiff and difficult to open","High",    "Resolved",   -10, -8, -7,"maint4", 85.0,2.0, 1,"Lock replaced with new mechanism"),
        ("NI-LL234567L","APT-L05","No Hot Water",        "Boiler not producing hot water",             "High",    "In Progress", -2,  1,None,"maint2",  0.0,0.0, 1,"Boiler engineer booked"),
        ("NI-MM345678M","APT-C04","Noisy Pipes",         "Banging sounds from water pipes at night",   "Low",     "Open",        -5,None,None,"maint4",  0.0,0.0, 0,""),
        ("NI-AA123456A","APT-102","Broken Cupboard",     "Kitchen cupboard door hinge snapped",        "Low",     "Resolved",   -45,-43,-42,"maint1", 25.0,0.5, 1,"Hinge replaced"),
        ("NI-EE567890E","APT-L01","Thermostat Fault",    "Thermostat not reading temperature correctly","Medium", "Assigned",    -6,  2,None,"maint2",  0.0,0.0, 1,"Smart thermostat replacement ordered"),
    ]

    for row in maintenance_raw:
        (ni, apt_num, title, desc, priority, status,
         rep_off, sched_off, res_off,
         assigned_user, cost, time_spent, comm, notes) = row
        tid  = tenant_id_map[ni]
        aid  = apt_map[apt_num]
        uid  = user_map[assigned_user]
        rep_d   = d(rep_off)
        sched_d = d(sched_off) if sched_off is not None else None
        res_d   = d(res_off)   if res_off   is not None else None
        cur.execute("""
            INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,
                reported_date,scheduled_date,resolved_date,assigned_to,
                cost,time_spent,communication_sent,notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (tid, aid, title, desc, priority, status,
              rep_d, sched_d, res_d, uid,
              cost, time_spent, comm, notes))

    # ── Complaints ───────────────────────────────────────────
    # Format: (tenant_ni, title, description, status, created_offset, resolved_offset)
    complaints_raw = [
        ("NI-AA123456A","Noisy Neighbours",    "Upstairs neighbours extremely loud past midnight",        "Open",        -3, None),
        ("NI-CC345678C","Parking Issue",        "Another tenant using my allocated parking space",         "Open",        -2, None),
        ("NI-EE567890E","Water Pressure Low",   "Hot water pressure has been very low for over a week",    "Resolved",   -10,   -8),
        ("NI-GG789012G","Rubbish Collection",   "Communal bins not collected for two weeks",               "In Progress", -5, None),
        ("NI-II901234I","Intercom Broken",       "Front door intercom system not working for residents",    "Open",        -1, None),
        ("NI-DD456789D","Heating Insufficient", "Central heating inadequate during cold weather",           "In Progress", -6, None),
        ("NI-JJ012345J","Pest Sighting",         "Mice spotted in the communal hallway area",               "Open",        -2, None),
        ("NI-LL234567L","Neighbour Dispute",     "Dispute over shared utility bill calculations",            "Resolved",   -15,  -10),
        ("NI-MM345678M","Lift Out of Order",     "Lift has been out of order for 3 days",                   "Open",        -3, None),
        ("NI-BB234567B","Bin Room Access",       "Bin room keypad code not working",                        "Resolved",   -20,  -18),
        ("NI-KK123456K","Communal Light Fault",  "Communal hallway light flickering constantly",            "In Progress", -4, None),
        ("NI-HH890123H","Parking Space Blocked", "Unknown vehicle blocking designated parking bay",         "Resolved",    -8,   -6),
    ]

    for ni, title, desc, status, created_off, resolved_off in complaints_raw:
        tid     = tenant_id_map[ni]
        created = d(created_off)
        resolved= d(resolved_off) if resolved_off is not None else None
        cur.execute("""
            INSERT INTO complaints(tenant_id,title,description,status,created_at,resolved_at)
            VALUES(?,?,?,?,?,?)
        """, (tid, title, desc, status, created, resolved))

    # ── Audit Log (sample entries) ────────────────────────────
    audit_entries = [
        (user_map["admin_bristol"], "LOGIN",           "User",      "1",  None, None),
        (user_map["frontdesk1"],    "ADD_TENANT",      "Tenant",    "1",  None, "Oliver Thompson"),
        (user_map["frontdesk1"],    "ADD_TENANT",      "Tenant",    "2",  None, "Emma Williams"),
        (user_map["finance1"],      "MARK_PAID",       "Payment",   "1",  "Overdue", "Paid"),
        (user_map["maint1"],        "RESOLVE_ISSUE",   "Maintenance","1", "Open", "Resolved"),
        (user_map["admin_bristol"], "ADD_APARTMENT",   "Apartment", "1",  None, "APT-101"),
        (user_map["manager"],       "GENERATE_REPORT", "Report",    None, None, "Occupancy Report"),
        (user_map["finance1"],      "GENERATE_INVOICE","Payment",   "5",  None, "Rent Invoice"),
        (user_map["frontdesk1"],    "ADD_COMPLAINT",   "Complaint", "1",  None, "Noisy Neighbours"),
        (user_map["admin_london"],  "LOGIN",           "User",      "2",  None, None),
    ]
    cur.executemany("""
        INSERT INTO audit_log(user_id,action,entity_type,entity_id,old_value,new_value)
        VALUES(?,?,?,?,?,?)
    """, audit_entries)

    conn.commit()
    print("  All seed data inserted successfully.")


# ================================================================
# MAIN
# ================================================================
def build_database():
    print(f"\nBuilding PAMS SQLite database...")
    print(f"  Location: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")

    # Create schema
    print("  Creating schema...")
    conn.executescript(SCHEMA)
    print("  Schema created.")

    # Seed data
    print("  Seeding data...")
    seed(conn)

    # Verify
    print("\n  Table row counts:")
    tables = ["locations","users","apartments","tenants","leases",
              "payments","maintenance","complaints","audit_log"]
    conn.row_factory = sqlite3.Row
    for t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"    {t:<18} {n:>3} rows")

    conn.close()

    print(f"""
  ✓ pams.db created successfully!

  Login credentials:
    Role               Username          Password
    ─────────────────────────────────────────────
    Administrator      admin_bristol     admin123
    Administrator      admin_london      admin123
    Administrator      admin_manc        admin123
    Administrator      admin_cardiff     admin123
    Manager            manager           manager123
    Front-Desk Staff   frontdesk1        front123
    Front-Desk Staff   frontdesk2        front123
    Finance Manager    finance1          finance123
    Finance Manager    finance2          finance123
    Maintenance Staff  maint1            maint123
    Maintenance Staff  maint2            maint123

  Next step: python main.py
""")


if __name__ == "__main__":
    build_database()
