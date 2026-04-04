# ============================================================
# PAMS — database.py
# Paragon Apartment Management System
# Comprehensive SQLite Database Layer
#
# Replaces the in-memory data store with full SQLite persistence.
# Implements the DatabaseManager Singleton pattern as per the
# Class Diagram and all Sequence Diagram workflows (SD1–SD5).
#
# All public function signatures are fully backward-compatible
# with the existing GUI views.
# ============================================================
from __future__ import annotations

import copy
import datetime
import hashlib
import os
import sqlite3
import threading
from typing import Optional

# ----------------------------------------------------------
# Configuration
# ----------------------------------------------------------
_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "pams.db")
_SALT = b"PAMS_Paragon_Secure_2025"

# Thread-local storage for connections (thread-safety / scalability NFR3)
_local = threading.local()

# ----------------------------------------------------------
# Singleton DatabaseManager (as per Class Diagram)
# ----------------------------------------------------------
class DatabaseManager:
    """
    Singleton class controlling all database access.
    Implements the Singleton pattern from the PAMS Class Diagram to ensure
    a single, centralised and controlled database connection point (NFR1, NFR2).
    """
    _instance: "DatabaseManager | None" = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def get_connection(self) -> sqlite3.Connection:
        """Return a thread-local SQLite connection with foreign keys enabled."""
        if not hasattr(_local, "conn") or _local.conn is None:
            _local.conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
            _local.conn.row_factory = sqlite3.Row
            _local.conn.execute("PRAGMA foreign_keys = ON")
            _local.conn.execute("PRAGMA journal_mode = WAL")  # Performance (NFR4)
        return _local.conn

    def executeQuery(self, query: str, params: tuple = ()) -> list:
        """Execute a SELECT query and return results as a list of dicts."""
        conn = self.get_connection()
        cur = conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

    def executeUpdate(self, query: str, params: tuple = ()) -> bool:
        """Execute an INSERT/UPDATE/DELETE and commit. Returns success bool."""
        try:
            conn = self.get_connection()
            conn.execute(query, params)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"[DB ERROR] {e}\n  Query: {query}\n  Params: {params}")
            return False

    def executemany(self, query: str, param_list: list) -> bool:
        try:
            conn = self.get_connection()
            conn.executemany(query, param_list)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"[DB ERROR] {e}")
            return False

    def lastrowid(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT and return the new row id."""
        conn = self.get_connection()
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid


# Module-level singleton instance
_db = DatabaseManager()


# ----------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------
def _hash(pw: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), _SALT, 100_000).hex()


def _today() -> str:
    return datetime.date.today().isoformat()


def _days_from_today(days: int) -> str:
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()


def _row(table_rows: list) -> dict | None:
    return table_rows[0] if table_rows else None


# ----------------------------------------------------------
# Schema Creation
# ----------------------------------------------------------
def _create_schema():
    conn = _db.get_connection()
    conn.executescript("""
    -- --------------------------------------------------------
    -- LOCATIONS (supports multi-city, FR7 / NFR3 Scalability)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS locations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL UNIQUE,
        created_at  TEXT    NOT NULL DEFAULT (date('now'))
    );

    -- --------------------------------------------------------
    -- USERS  (RBAC: NFR1 Security, User Management FR)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT    NOT NULL UNIQUE,
        password    TEXT    NOT NULL,
        full_name   TEXT    NOT NULL,
        role        TEXT    NOT NULL CHECK(role IN (
                        'Administrator','Manager','Front-Desk Staff',
                        'Finance Manager','Maintenance Staff')),
        location    TEXT    NOT NULL,
        email       TEXT    NOT NULL DEFAULT '',
        active      INTEGER NOT NULL DEFAULT 1,
        created_at  TEXT    NOT NULL DEFAULT (date('now'))
    );

    -- --------------------------------------------------------
    -- APARTMENTS  (Apartment Management FR)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS apartments (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        apt_number   TEXT    NOT NULL UNIQUE,
        location     TEXT    NOT NULL,
        type         TEXT    NOT NULL,
        rooms        INTEGER NOT NULL DEFAULT 1,
        monthly_rent REAL    NOT NULL,
        status       TEXT    NOT NULL DEFAULT 'Vacant'
                        CHECK(status IN ('Vacant','Occupied','Maintenance')),
        floor        INTEGER NOT NULL DEFAULT 1,
        description  TEXT    NOT NULL DEFAULT '',
        FOREIGN KEY (location) REFERENCES locations(name) ON UPDATE CASCADE
    );

    -- --------------------------------------------------------
    -- TENANTS  (Tenant Management FR1)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS tenants (
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

    -- --------------------------------------------------------
    -- LEASES  (Lease lifecycle: SD4 Early Termination)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS leases (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id            INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        apartment_id         INTEGER NOT NULL REFERENCES apartments(id) ON DELETE CASCADE,
        start_date           TEXT    NOT NULL,
        end_date             TEXT    NOT NULL,
        monthly_rent         REAL    NOT NULL,
        deposit              REAL    NOT NULL DEFAULT 0,
        status               TEXT    NOT NULL DEFAULT 'Active'
                                 CHECK(status IN ('Active','Terminated','Expired','Archived')),
        early_termination_date TEXT,
        penalty_amount       REAL    DEFAULT 0,
        created_at           TEXT    NOT NULL DEFAULT (date('now'))
    );

    -- --------------------------------------------------------
    -- PAYMENTS / INVOICES  (Payment & Billing FR3, SD1)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS payments (
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

    -- --------------------------------------------------------
    -- MAINTENANCE REQUESTS  (Maintenance FR4, SD3)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS maintenance (
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

    -- --------------------------------------------------------
    -- COMPLAINTS  (Complaint tracking FR)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS complaints (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id   INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
        title       TEXT    NOT NULL,
        description TEXT    NOT NULL DEFAULT '',
        status      TEXT    NOT NULL DEFAULT 'Open'
                        CHECK(status IN ('Open','In Progress','Resolved')),
        created_at  TEXT    NOT NULL DEFAULT (date('now')),
        resolved_at TEXT
    );

    -- --------------------------------------------------------
    -- AUDIT LOG  (Security NFR1 — tracks all mutations)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS audit_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        action      TEXT    NOT NULL,
        entity_type TEXT,
        entity_id   TEXT,
        old_value   TEXT,
        new_value   TEXT,
        timestamp   TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    -- --------------------------------------------------------
    -- PERFORMANCE INDEXES  (NFR4 Efficiency)
    -- --------------------------------------------------------
    CREATE INDEX IF NOT EXISTS idx_tenants_apt    ON tenants(apt_id);
    CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
    CREATE INDEX IF NOT EXISTS idx_payments_tenant ON payments(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
    CREATE INDEX IF NOT EXISTS idx_payments_due    ON payments(due_date);
    CREATE INDEX IF NOT EXISTS idx_maint_apt      ON maintenance(apt_id);
    CREATE INDEX IF NOT EXISTS idx_maint_status   ON maintenance(status);
    CREATE INDEX IF NOT EXISTS idx_complaints_tenant ON complaints(tenant_id);
    """)
    conn.commit()


# ----------------------------------------------------------
# Seed Data
# ----------------------------------------------------------
def _seed_data():
    """Populate the database with realistic mock data for demo/testing."""
    conn = _db.get_connection()

    # ── Locations ──────────────────────────────────────────
    locations = ["Bristol", "Cardiff", "London", "Manchester"]
    conn.executemany(
        "INSERT OR IGNORE INTO locations(name) VALUES(?)",
        [(l,) for l in locations]
    )

    # ── Users  (RBAC roles) ────────────────────────────────
    users = [
        ("admin_bristol", _hash("admin123"), "Alice Morrison",   "Administrator",    "Bristol",    "alice@paragon.com"),
        ("admin_london",  _hash("admin123"), "David Okafor",     "Administrator",    "London",     "david@paragon.com"),
        ("manager",       _hash("manager123"), "Sarah Whitfield","Manager",          "Bristol",    "sarah@paragon.com"),
        ("frontdesk1",    _hash("front123"),  "James Patel",     "Front-Desk Staff", "Bristol",    "james@paragon.com"),
        ("frontdesk2",    _hash("front123"),  "Lily Chen",       "Front-Desk Staff", "Manchester", "lily@paragon.com"),
        ("finance1",      _hash("finance123"),"Robert Hughes",   "Finance Manager",  "Bristol",    "robert@paragon.com"),
        ("maint1",        _hash("maint123"),  "Carlos Rivera",   "Maintenance Staff","Bristol",    "carlos@paragon.com"),
        ("maint2",        _hash("maint123"),  "Priya Singh",     "Maintenance Staff","London",     "priya@paragon.com"),
        ("admin_manc",    _hash("admin123"),  "Fiona Walsh",     "Administrator",    "Manchester", "fiona@paragon.com"),
        ("admin_cardiff", _hash("admin123"),  "Rhys Evans",      "Administrator",    "Cardiff",    "rhys@paragon.com"),
        ("finance2",      _hash("finance123"),"Natasha Peters",  "Finance Manager",  "London",     "natasha@paragon.com"),
    ]
    conn.executemany("""
        INSERT OR IGNORE INTO users(username,password,full_name,role,location,email)
        VALUES(?,?,?,?,?,?)
    """, users)

    # ── Apartments ────────────────────────────────────────
    apts = [
        # Bristol
        ("APT-101","Bristol","Studio",    1,  850.0,"Occupied",1,"Modern studio with open-plan living"),
        ("APT-102","Bristol","1-Bedroom", 1, 1050.0,"Occupied",1,"Bright 1-bed with private balcony"),
        ("APT-103","Bristol","2-Bedroom", 2, 1400.0,"Vacant",  1,"Spacious 2-bed, freshly renovated"),
        ("APT-201","Bristol","2-Bedroom", 2, 1350.0,"Occupied",2,"South-facing 2-bed, river views"),
        ("APT-202","Bristol","3-Bedroom", 3, 1800.0,"Occupied",2,"Large family unit with garden access"),
        ("APT-301","Bristol","Penthouse", 4, 3200.0,"Vacant",  3,"Luxury penthouse, 360-degree views"),
        ("APT-104","Bristol","Studio",    1,  820.0,"Maintenance",1,"Undergoing refurbishment"),
        # London
        ("APT-L01","London","Studio",     1, 1400.0,"Occupied",1,"Bridge view studio, zone 1"),
        ("APT-L02","London","1-Bedroom",  1, 1750.0,"Occupied",1,"Prime Shoreditch location"),
        ("APT-L03","London","2-Bedroom",  2, 2400.0,"Vacant",  2,"Excellent transport links"),
        ("APT-L04","London","3-Bedroom",  3, 3100.0,"Occupied",3,"Luxury flat, concierge service"),
        # Manchester
        ("APT-M01","Manchester","2-Bedroom",2,1100.0,"Occupied",1,"City centre, close to amenities"),
        ("APT-M02","Manchester","1-Bedroom",1, 900.0,"Vacant",  1,"Northern Quarter, character property"),
        ("APT-M03","Manchester","Studio",   1, 750.0,"Occupied",1,"Compact modern studio"),
        # Cardiff
        ("APT-C01","Cardiff","1-Bedroom",  1, 850.0,"Occupied",1,"Cardiff Bay area, waterfront"),
        ("APT-C02","Cardiff","2-Bedroom",  2,1100.0,"Vacant",  1,"Quiet residential area, parking included"),
        ("APT-C03","Cardiff","Studio",     1, 700.0,"Occupied",1,"City centre, compact and efficient"),
    ]
    conn.executemany("""
        INSERT OR IGNORE INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description)
        VALUES(?,?,?,?,?,?,?,?)
    """, apts)
    conn.commit()

    # ── Helper: get IDs ────────────────────────────────────
    def apt_id(num): return _row(_db.executeQuery("SELECT id FROM apartments WHERE apt_number=?", (num,)))["id"]

    def _lr(back, fwd):
        s = (datetime.date.today() - datetime.timedelta(days=30*back)).isoformat()
        e = (datetime.date.today() + datetime.timedelta(days=30*fwd)).isoformat()
        return s, e

    # ── Tenants ───────────────────────────────────────────
    tenants_data = [
        ("NI-AA123456A","Oliver Thompson","07700111001","oliver@email.com","Software Engineer","John Smith","1-Bedroom",    "APT-102",6,12,1050.0,1050.0),
        ("NI-BB234567B","Emma Williams",  "07700111002","emma@email.com",  "Nurse",           "Dr. Jones",  "1-Bedroom",    "APT-101",3, 9, 850.0, 850.0),
        ("NI-CC345678C","Noah Brown",     "07700111003","noah@email.com",  "Teacher",         "Mary Green", "2-Bedroom",    "APT-201",1,11,1350.0,1350.0),
        ("NI-DD456789D","Sophia Davis",   "07700111004","sophia@email.com","Accountant",      "Peter Davis","3-Bedroom",    "APT-202",4, 8,1800.0,1800.0),
        ("NI-EE567890E","Liam Wilson",    "07700111005","liam@email.com",  "Architect",       "Jane Wilson","Studio",       "APT-L01",2,10,1400.0,1400.0),
        ("NI-FF678901F","Isabella Moore", "07700111006","isab@email.com",  "Marketing Manager","Tom Moore", "1-Bedroom",    "APT-L02",5, 7,1750.0,1750.0),
        ("NI-GG789012G","Mason Taylor",   "07700111007","mason@email.com", "Chef",            "Cathy Taylor","2-Bedroom",   "APT-M01",6, 6,1100.0,1100.0),
        ("NI-HH890123H","Ava Anderson",   "07700111008","ava@email.com",   "Solicitor",       "Bob Anderson","1-Bedroom",   "APT-C01",3, 9, 850.0, 850.0),
        ("NI-II901234I","Jack Robinson",  "07700111009","jack@email.com",  "Doctor",          "NHS Trust",  "3-Bedroom",    "APT-L04",2,10,3100.0,3100.0),
        ("NI-JJ012345J","Zoe Martinez",   "07700111010","zoe@email.com",   "Designer",        "Creative Co","Studio",       "APT-M03",1,11, 750.0, 750.0),
        ("NI-KK123456K","Harry Evans",    "07700111011","harry@email.com", "Engineer",        "Rhys Evans", "Studio",       "APT-C03",4, 8, 700.0, 700.0),
    ]
    for ni,name,phone,email,occ,ref,req,apt_num,back,fwd,dep,rent in tenants_data:
        ls, le = _lr(back, fwd)
        aid = apt_id(apt_num)
        conn.execute("""
            INSERT OR IGNORE INTO tenants
            (ni_number,full_name,phone,email,occupation,reference,
             apartment_requirements,apt_id,lease_start,lease_end,
             deposit,monthly_rent,status,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'Active','',date('now'))
        """, (ni,name,phone,email,occ,ref,req,aid,ls,le,dep,rent))

    conn.commit()

    # ── Leases (mirrors tenant data) ──────────────────────
    tenant_rows = _db.executeQuery("SELECT id,apt_id,lease_start,lease_end,monthly_rent,deposit FROM tenants")
    for t in tenant_rows:
        conn.execute("""
            INSERT OR IGNORE INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status)
            SELECT ?,?,?,?,?,?,'Active' WHERE NOT EXISTS(
                SELECT 1 FROM leases WHERE tenant_id=?)
        """, (t["id"],t["apt_id"],t["lease_start"],t["lease_end"],t["monthly_rent"],t["deposit"],t["id"]))
    conn.commit()

    # ── Payments (3 months history per tenant) ────────────
    today = datetime.date.today()
    pid_rows = _db.executeQuery("SELECT id,monthly_rent FROM tenants")
    for t in pid_rows:
        for m in (3, 2, 1):
            due = (today - datetime.timedelta(days=30*m)).replace(day=1).isoformat()
            paid = due if m > 1 else None
            status = "Paid" if paid else "Overdue"
            # Avoid duplicates
            existing = _db.executeQuery(
                "SELECT 1 FROM payments WHERE tenant_id=? AND due_date=? AND type='Rent'",
                (t["id"], due)
            )
            if not existing:
                conn.execute("""
                    INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified)
                    VALUES(?,?,?,?,?,'Rent',?)
                """, (t["id"],t["monthly_rent"],due,paid,status,1 if m==1 else 0))
    conn.commit()

    # ── Maintenance Requests ───────────────────────────────
    def tid(ni):
        r = _row(_db.executeQuery("SELECT id FROM tenants WHERE ni_number=?", (ni,)))
        return r["id"] if r else None
    def aid(num):
        r = _row(_db.executeQuery("SELECT id FROM apartments WHERE apt_number=?", (num,)))
        return r["id"] if r else None
    def uid(uname):
        r = _row(_db.executeQuery("SELECT id FROM users WHERE username=?", (uname,)))
        return r["id"] if r else None

    maint_data = [
        (tid("NI-AA123456A"),aid("APT-102"),"Leaking Tap",    "Kitchen tap dripping continuously",   "High",    "Resolved",   _days_from_today(-20),_days_from_today(-18),_days_from_today(-17),uid("maint1"),120.0,3.0,1,"Parts replaced"),
        (tid("NI-BB234567B"),aid("APT-101"),"Broken Heater",  "Radiator not working",                "High",    "In Progress",_days_from_today(-5), _days_from_today(2), None,                  uid("maint1"),  0.0,0.0,1,"Ordered replacement part"),
        (tid("NI-CC345678C"),aid("APT-201"),"Cracked Window",  "Bedroom window cracked",             "Medium",  "Open",       _days_from_today(-2), None,               None,                  uid("maint1"),  0.0,0.0,0,""),
        (tid("NI-DD456789D"),aid("APT-202"),"Lift Fault",     "Lift on floor 2 not stopping",        "Critical","Open",       _days_from_today(-1), None,               None,                  uid("maint1"),  0.0,0.0,0,""),
        (tid("NI-EE567890E"),aid("APT-L01"),"Pest Control",   "Cockroaches reported in kitchen",     "Medium",  "Resolved",   _days_from_today(-30),_days_from_today(-26),_days_from_today(-25),uid("maint2"),200.0,5.0,1,"Professional extermination"),
        (tid("NI-FF678901F"),aid("APT-L02"),"Faulty Electrics","Intermittent power in living room",  "High",    "In Progress",_days_from_today(-3), _days_from_today(1), None,                  uid("maint2"),  0.0,0.0,1,"Electrician booked"),
        (tid("NI-GG789012G"),aid("APT-M01"),"Damp Patch",     "Damp patch on bathroom ceiling",     "Medium",  "Assigned",   _days_from_today(-7), _days_from_today(3), None,                  uid("maint1"), 0.0,0.0,1,"Damp specialist assigned"),
        (tid("NI-HH890123H"),aid("APT-C01"),"Blocked Drain",  "Shower drain slow to empty",          "Low",     "Resolved",   _days_from_today(-14),_days_from_today(-12),_days_from_today(-12),uid("maint1"),45.0,1.5,1,"Drain cleared"),
    ]
    for row in maint_data:
        existing = _db.executeQuery("SELECT 1 FROM maintenance WHERE tenant_id=? AND title=?", (row[0], row[2]))
        if not existing:
            conn.execute("""
                INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,
                    reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,
                    communication_sent,notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, row)

    # ── Complaints ────────────────────────────────────────
    complaints_data = [
        (tid("NI-AA123456A"),"Noisy Neighbours",  "Upstairs neighbours very loud past midnight","Open",       _days_from_today(-3), None),
        (tid("NI-CC345678C"),"Parking Issue",     "Another tenant is using my parking space",   "Open",       _days_from_today(-2), None),
        (tid("NI-EE567890E"),"Water Pressure Low","Water pressure has been low for a week",      "Resolved",   _days_from_today(-10),_days_from_today(-8)),
        (tid("NI-GG789012G"),"Rubbish Collection","Bins not collected for two weeks",            "In Progress",_days_from_today(-5), None),
        (tid("NI-II901234I"),"Intercom Broken",   "Intercom system at front door not working",  "Open",       _days_from_today(-1), None),
    ]
    for row in complaints_data:
        existing = _db.executeQuery("SELECT 1 FROM complaints WHERE tenant_id=? AND title=?", (row[0], row[1]))
        if not existing:
            conn.execute("""
                INSERT INTO complaints(tenant_id,title,description,status,created_at,resolved_at)
                VALUES(?,?,?,?,?,?)
            """, row)

    conn.commit()


# ----------------------------------------------------------
# Public Init (called by main.py at startup)
# ----------------------------------------------------------
def init_db():
    """
    Initialise the SQLite database: create schema and seed mock data.
    Idempotent — safe to call multiple times.
    """
    _create_schema()
    # Only seed if the database appears to be new/empty
    users = _db.executeQuery("SELECT COUNT(*) as c FROM users")
    if users and users[0]["c"] == 0:
        _seed_data()


# ----------------------------------------------------------
# Authentication  (SD flows: verifyRoleAccess)
# ----------------------------------------------------------
def login(username: str, password: str) -> Optional[dict]:
    """Authenticate user. Returns user dict or None. (SD1–SD5 entry point)"""
    pw = _hash(password)
    rows = _db.executeQuery(
        "SELECT * FROM users WHERE username=? AND password=? AND active=1",
        (username, pw)
    )
    if rows:
        u = dict(rows[0])
        _db.executeUpdate(
            "UPDATE users SET created_at=created_at WHERE id=?", (u["id"],)
        )
        return u
    return None

authenticate = login  # backward-compat alias


# ----------------------------------------------------------
# Users  (Account / User Management FR)
# ----------------------------------------------------------
def get_all_users(location=None) -> list:
    if location and location != "All":
        rows = _db.executeQuery(
            "SELECT * FROM users WHERE location=? ORDER BY role, full_name", (location,))
    else:
        rows = _db.executeQuery("SELECT * FROM users ORDER BY role, full_name")
    return [dict(r) for r in rows]


def add_user(username, password, full_name, role, location, email=""):
    return _db.executeUpdate("""
        INSERT INTO users(username,password,full_name,role,location,email)
        VALUES(?,?,?,?,?,?)
    """, (username, _hash(password), full_name, role, location, email or ""))


def update_user(uid, full_name, role, location, email, active):
    return _db.executeUpdate("""
        UPDATE users SET full_name=?,role=?,location=?,email=?,active=? WHERE id=?
    """, (full_name, role, location, email or "", int(bool(active)), uid))


def updateUserPassword(uid: int, password: str):
    return _db.executeUpdate(
        "UPDATE users SET password=? WHERE id=?", (_hash(password), uid))

update_user_password = updateUserPassword  # alias


def delete_user(uid):
    """Soft-delete: mark inactive (preserves audit trail)."""
    return _db.executeUpdate("UPDATE users SET active=0 WHERE id=?", (uid,))


# ----------------------------------------------------------
# Locations  (Multi-city scalability NFR3, FR7)
# ----------------------------------------------------------
def get_all_locations() -> list:
    rows = _db.executeQuery("SELECT name FROM locations ORDER BY name")
    return [r["name"] for r in rows]


def expandBusiness(name: str):
    """SD5: Manager expands business to a new city."""
    name = (name or "").strip()
    if not name:
        return
    _db.executeUpdate("INSERT OR IGNORE INTO locations(name) VALUES(?)", (name,))

add_location = expandBusiness  # alias


# ----------------------------------------------------------
# Apartments  (Apartment Management FR2)
# ----------------------------------------------------------
def get_all_apartments(location=None) -> list:
    if location and location != "All":
        rows = _db.executeQuery("""
            SELECT * FROM apartments WHERE location=?
            ORDER BY location, apt_number
        """, (location,))
    else:
        rows = _db.executeQuery(
            "SELECT * FROM apartments ORDER BY location, apt_number")
    return [dict(r) for r in rows]


def add_apartment(apt_number, location, apt_type, rooms, monthly_rent, floor=1, desc=""):
    return _db.executeUpdate("""
        INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,floor,description)
        VALUES(?,?,?,?,?,?,?)
    """, (apt_number, location, apt_type, int(rooms), float(monthly_rent), int(floor), desc or ""))


def update_apartment(apt_id, apt_number, location, apt_type, rooms, monthly_rent,
                     status, floor, desc):
    return _db.executeUpdate("""
        UPDATE apartments SET apt_number=?,location=?,type=?,rooms=?,monthly_rent=?,
            status=?,floor=?,description=?
        WHERE id=?
    """, (apt_number, location, apt_type, int(rooms), float(monthly_rent),
          status, int(floor), desc or "", apt_id))


def delete_apartment(apt_id):
    return _db.executeUpdate("DELETE FROM apartments WHERE id=?", (apt_id,))


def get_vacant_apartments() -> list:
    rows = _db.executeQuery("""
        SELECT id, apt_number, location FROM apartments
        WHERE status='Vacant' ORDER BY location, apt_number
    """)
    return [(r["id"], f"{r['apt_number']} ({r['location']})") for r in rows]


# ----------------------------------------------------------
# Tenants  (Tenant Management FR1, SD2 Register New Tenant)
# ----------------------------------------------------------
def _tenant_with_join(row: dict) -> dict:
    apt = None
    if row.get("apt_id"):
        apts = _db.executeQuery(
            "SELECT apt_number, location FROM apartments WHERE id=?", (row["apt_id"],))
        apt = apts[0] if apts else None
    row["apt_number"] = apt["apt_number"] if apt else None
    row["location"]   = apt["location"]   if apt else None
    return row


def get_all_tenants(location=None) -> list:
    rows = _db.executeQuery("""
        SELECT t.*, a.apt_number, a.location
        FROM tenants t
        LEFT JOIN apartments a ON t.apt_id = a.id
        ORDER BY t.full_name
    """)
    if location and location != "All":
        rows = [r for r in rows if r.get("location") == location]
    return [dict(r) for r in rows]


def get_tenant_by_id(tid) -> Optional[dict]:
    rows = _db.executeQuery("""
        SELECT t.*, a.apt_number, a.location
        FROM tenants t
        LEFT JOIN apartments a ON t.apt_id = a.id
        WHERE t.id=?
    """, (tid,))
    return dict(rows[0]) if rows else None


def add_tenant(ni, name, phone, email, occupation, reference,
               apartment_requirements, apt_id, lease_start, lease_end,
               deposit, monthly_rent):
    """
    SD2: Register New Tenant.
    Creates tenant record, updates apartment occupancy, creates lease.
    """
    # Validate NI uniqueness (SD2 checkExistingNiNumber)
    if _db.executeQuery("SELECT 1 FROM tenants WHERE ni_number=?", (ni,)):
        raise ValueError(f"NI number '{ni}' already exists in the system.")

    _db.executeUpdate("""
        INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,
            apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (ni, name, phone or "", email or "", occupation or "", reference or "",
          apartment_requirements or "", apt_id, lease_start, lease_end,
          float(deposit), float(monthly_rent)))

    tenant_id = _db.executeQuery("SELECT last_insert_rowid() as id")[0]["id"]

    # updateOccupancyStatus (SD2)
    if apt_id:
        _db.executeUpdate("UPDATE apartments SET status='Occupied' WHERE id=?", (apt_id,))

    # createLease (SD2)
    _db.executeUpdate("""
        INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit)
        VALUES(?,?,?,?,?,?)
    """, (tenant_id, apt_id, lease_start, lease_end, float(monthly_rent), float(deposit)))

    return tenant_id


def update_tenant(tid, ni, name, phone, email, occupation,
                  reference, apartment_requirements, lease_start,
                  lease_end, deposit, monthly_rent, status, notes):
    return _db.executeUpdate("""
        UPDATE tenants SET ni_number=?,full_name=?,phone=?,email=?,occupation=?,
            reference=?,apartment_requirements=?,lease_start=?,lease_end=?,
            deposit=?,monthly_rent=?,status=?,notes=?
        WHERE id=?
    """, (ni, name, phone or "", email or "", occupation or "", reference or "",
          apartment_requirements or "", lease_start, lease_end,
          float(deposit), float(monthly_rent), status, notes or "", tid))


def delete_tenant(tid):
    """Remove tenant and free their apartment."""
    tenant = get_tenant_by_id(tid)
    if tenant and tenant.get("apt_id"):
        _db.executeUpdate(
            "UPDATE apartments SET status='Vacant' WHERE id=?", (tenant["apt_id"],))
    return _db.executeUpdate("DELETE FROM tenants WHERE id=?", (tid,))


# ----------------------------------------------------------
# Payments / Invoices  (Payment & Billing FR3, SD1)
# ----------------------------------------------------------
def _payment_with_join(row: dict) -> dict:
    tid = row.get("tenant_id")
    if tid:
        joins = _db.executeQuery("""
            SELECT t.full_name, a.apt_number, a.location
            FROM tenants t LEFT JOIN apartments a ON t.apt_id=a.id
            WHERE t.id=?
        """, (tid,))
        if joins:
            row["full_name"] = joins[0]["full_name"]
            row["location"]  = joins[0]["location"]
            row["apt_number"]= joins[0]["apt_number"]
    return row


def get_all_payments(location=None) -> list:
    rows = _db.executeQuery("""
        SELECT p.*, t.full_name, a.apt_number, a.location
        FROM payments p
        JOIN tenants t ON p.tenant_id = t.id
        LEFT JOIN apartments a ON t.apt_id = a.id
        ORDER BY p.due_date DESC
    """)
    if location and location != "All":
        rows = [r for r in rows if r.get("location") == location]
    return [dict(r) for r in rows]


def get_tenant_payments(tenant_id) -> list:
    rows = _db.executeQuery("""
        SELECT * FROM payments WHERE tenant_id=? ORDER BY due_date DESC
    """, (tenant_id,))
    return [dict(r) for r in rows]


def generateInvoice(tenant_id, amount, due_date, payment_type="Rent", notes=""):
    """SD1: Generate invoice for a tenant payment."""
    return _db.executeUpdate("""
        INSERT INTO payments(tenant_id,amount,due_date,status,type,notes)
        VALUES(?,?,?,'Pending',?,?)
    """, (int(tenant_id), float(amount), due_date, payment_type, notes or ""))

add_payment = generateInvoice  # alias


def markAsPaid(payment_id):
    """SD1: markAsPaid() — set status to Paid and record date."""
    return _db.executeUpdate("""
        UPDATE payments SET status='Paid', paid_date=date('now') WHERE id=?
    """, (payment_id,))

mark_payment_paid = markAsPaid  # alias


def processPayment(payment_id: int) -> bool:
    """SD1: processPayment() — validate and mark invoice as paid."""
    rows = _db.executeQuery("SELECT * FROM payments WHERE id=?", (payment_id,))
    if not rows or rows[0]["status"] == "Paid":
        return False
    markAsPaid(payment_id)
    return True


def generateReceipt(payment_id: int) -> dict:
    """SD1: generateReceipt() — return payment record as receipt dict."""
    rows = _db.executeQuery("""
        SELECT p.*, t.full_name, a.apt_number
        FROM payments p
        JOIN tenants t ON p.tenant_id=t.id
        LEFT JOIN apartments a ON t.apt_id=a.id
        WHERE p.id=?
    """, (payment_id,))
    return dict(rows[0]) if rows else {}


def get_late_payments(location=None) -> list:
    rows = _db.executeQuery("""
        SELECT p.*, t.full_name, a.apt_number, a.location
        FROM payments p
        JOIN tenants t ON p.tenant_id=t.id
        LEFT JOIN apartments a ON t.apt_id=a.id
        WHERE p.status IN ('Pending','Overdue') AND p.due_date < date('now')
        ORDER BY p.due_date
    """)
    if location and location != "All":
        rows = [r for r in rows if r.get("location") == location]
    return [dict(r) for r in rows]


def mark_late_notifications_sent(payment_ids: list):
    for pid in payment_ids:
        _db.executeUpdate(
            "UPDATE payments SET status='Overdue', late_notified=1 WHERE id=?", (pid,))


# ----------------------------------------------------------
# Maintenance  (Maintenance FR4, SD3 Resolve Maintenance Issue)
# ----------------------------------------------------------
def _maintenance_with_join(row: dict) -> dict:
    if row.get("tenant_id"):
        tjoin = _db.executeQuery(
            "SELECT full_name FROM tenants WHERE id=?", (row["tenant_id"],))
        row["full_name"] = tjoin[0]["full_name"] if tjoin else None
    if row.get("apt_id"):
        ajoin = _db.executeQuery(
            "SELECT apt_number, location FROM apartments WHERE id=?", (row["apt_id"],))
        if ajoin:
            row["apt_number"] = ajoin[0]["apt_number"]
            row["location"]   = ajoin[0]["location"]
    if row.get("assigned_to"):
        ujoin = _db.executeQuery(
            "SELECT full_name FROM users WHERE id=?", (row["assigned_to"],))
        row["staff_name"] = ujoin[0]["full_name"] if ujoin else None
    return row


def get_all_maintenance(location=None) -> list:
    rows = _db.executeQuery("""
        SELECT m.*, t.full_name, a.apt_number, a.location,
               u.full_name AS staff_name
        FROM maintenance m
        LEFT JOIN tenants t ON m.tenant_id = t.id
        LEFT JOIN apartments a ON m.apt_id = a.id
        LEFT JOIN users u ON m.assigned_to = u.id
        ORDER BY m.reported_date DESC
    """)
    if location and location != "All":
        rows = [r for r in rows if r.get("location") == location]
    return [dict(r) for r in rows]


def add_maintenance(tenant_id, apt_id, title, description,
                    priority="Medium", assigned_to=None, scheduled_date=None):
    return _db.executeUpdate("""
        INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,
            assigned_to,scheduled_date,reported_date)
        VALUES(?,?,?,?,?,?,?,date('now'))
    """, (
        int(tenant_id) if tenant_id else None,
        int(apt_id) if apt_id else None,
        title, description or "", priority,
        int(assigned_to) if assigned_to else None,
        scheduled_date
    ))


def resolveIssue(mid, cost, time_spent, notes=""):
    """SD3: resolveIssue() — record resolution, cost, and time taken."""
    return _db.executeUpdate("""
        UPDATE maintenance
        SET status='Resolved', resolved_date=date('now'),
            cost=?, time_spent=?, notes=?
        WHERE id=?
    """, (float(cost), float(time_spent), notes or "", mid))

resolve_maintenance = resolveIssue  # alias


def update_maintenance_status(mid, status):
    return _db.executeUpdate(
        "UPDATE maintenance SET status=? WHERE id=?", (status, mid))


def update_maintenance_schedule(mid, scheduled_date, notes=""):
    return _db.executeUpdate("""
        UPDATE maintenance SET scheduled_date=?, communication_sent=1, notes=?
        WHERE id=?
    """, (scheduled_date, notes or "", mid))


def get_maintenance_staff(location=None) -> list:
    if location and location != "All":
        rows = _db.executeQuery("""
            SELECT id, full_name FROM users
            WHERE role='Maintenance Staff' AND active=1 AND location=?
            ORDER BY full_name
        """, (location,))
    else:
        rows = _db.executeQuery("""
            SELECT id, full_name FROM users
            WHERE role='Maintenance Staff' AND active=1
            ORDER BY full_name
        """)
    return [(r["id"], r["full_name"]) for r in rows]


# ----------------------------------------------------------
# Complaints
# ----------------------------------------------------------
def _complaint_with_join(row: dict) -> dict:
    if row.get("tenant_id"):
        joins = _db.executeQuery("""
            SELECT t.full_name, a.apt_number, a.location
            FROM tenants t LEFT JOIN apartments a ON t.apt_id=a.id
            WHERE t.id=?
        """, (row["tenant_id"],))
        if joins:
            row["full_name"] = joins[0]["full_name"]
            row["location"]  = joins[0]["location"]
            row["apt_number"]= joins[0]["apt_number"]
    return row


def get_all_complaints(location=None) -> list:
    rows = _db.executeQuery("""
        SELECT c.*, t.full_name, a.apt_number, a.location
        FROM complaints c
        LEFT JOIN tenants t ON c.tenant_id = t.id
        LEFT JOIN apartments a ON t.apt_id = a.id
        ORDER BY c.created_at DESC
    """)
    if location and location != "All":
        rows = [r for r in rows if r.get("location") == location]
    return [dict(r) for r in rows]


def add_complaint(tenant_id, title, description):
    return _db.executeUpdate("""
        INSERT INTO complaints(tenant_id,title,description,created_at)
        VALUES(?,?,?,date('now'))
    """, (int(tenant_id), title, description or ""))


def updateStatus(cid, status):
    """Update complaint status; set resolved_at if resolving."""
    resolved_at = _today() if status == "Resolved" else None
    return _db.executeUpdate("""
        UPDATE complaints SET status=?, resolved_at=? WHERE id=?
    """, (status, resolved_at, cid))

update_complaint_status = updateStatus  # alias


# ----------------------------------------------------------
# Early Lease Termination  (FR5, SD4)
# ----------------------------------------------------------
def calculatePenalty(monthly_rent: float) -> float:
    """SD4: calculateLatePenalty() — 5% of monthly rent as per business rules."""
    return round(float(monthly_rent or 0) * 0.05, 2)


def terminateEarly(tid):
    """
    SD4: Process Early Lease Termination.
    1. Load active lease
    2. calculatePenalty (5% monthly rent, 1 month notice)
    3. Update apartment to Vacant
    4. Mark lease as Terminated
    5. Generate penalty invoice
    Returns (penalty_amount, leave_date) or (None, error_msg)
    """
    rows = _db.executeQuery("SELECT * FROM tenants WHERE id=?", (tid,))
    if not rows:
        return None, "Tenant not found."
    tenant = rows[0]
    if tenant["status"] != "Active":
        return None, "Tenant is not currently active."

    monthly_rent = float(tenant["monthly_rent"] or 0)
    penalty      = calculatePenalty(monthly_rent)
    notice_date  = _today()
    leave_date   = _days_from_today(30)  # 1-month notice period

    # Update tenant status
    _db.executeUpdate("""
        UPDATE tenants SET status='Leaving', early_leave_notice_date=?,
            lease_end=?, notes=?
        WHERE id=?
    """, (notice_date, leave_date,
          f"Early leave requested {notice_date}. Leave: {leave_date}. "
          f"Penalty: £{penalty:.2f} (5% of £{monthly_rent:.2f})",
          tid))

    # updateOccupancyStatus apartment → Vacant (SD4)
    if tenant["apt_id"]:
        _db.executeUpdate(
            "UPDATE apartments SET status='Vacant' WHERE id=?", (tenant["apt_id"],))

    # Mark lease as Terminated (SD4)
    _db.executeUpdate("""
        UPDATE leases SET status='Terminated', early_termination_date=?, penalty_amount=?
        WHERE tenant_id=? AND status='Active'
    """, (notice_date, penalty, tid))

    # generateInvoice for penalty (SD4)
    generateInvoice(
        tenant_id=tid,
        amount=penalty,
        due_date=notice_date,
        payment_type="Early Leave Penalty",
        notes=f"5% early termination penalty on £{monthly_rent:.2f}/month rent",
    )

    return penalty, leave_date

process_early_leave = terminateEarly  # alias


# ----------------------------------------------------------
# Reports  (Reporting FR6, SD5)
# ----------------------------------------------------------
def getOccupancyByCity() -> list:
    """SD5: getOccupancyByCity() — occupancy report per location."""
    rows = _db.executeQuery("""
        SELECT location,
               COUNT(*) as total,
               SUM(CASE WHEN status='Occupied' THEN 1 ELSE 0 END) as occupied
        FROM apartments
        GROUP BY location
        ORDER BY location
    """)
    return [dict(r) for r in rows]

occupancy_by_location = getOccupancyByCity  # alias


def compareCollectedVsPending(location=None) -> dict:
    """SD5: compareCollectedVsPending() — financial summary."""
    if location and location != "All":
        rows = _db.executeQuery("""
            SELECT p.status, p.amount
            FROM payments p
            JOIN tenants t ON p.tenant_id=t.id
            LEFT JOIN apartments a ON t.apt_id=a.id
            WHERE a.location=?
        """, (location,))
    else:
        rows = _db.executeQuery("SELECT status, amount FROM payments")

    collected = sum(float(r["amount"]) for r in rows if r["status"] == "Paid")
    pending   = sum(float(r["amount"]) for r in rows if r["status"] != "Paid")
    return {"collected": round(collected, 2), "pending": round(pending, 2)}

financial_summary = compareCollectedVsPending  # alias


def trackCostsByLocation(location=None) -> list:
    """SD5: trackCostsByLocation() — maintenance cost report."""
    if location and location != "All":
        rows = _db.executeQuery("""
            SELECT m.status, m.cost
            FROM maintenance m
            LEFT JOIN apartments a ON m.apt_id=a.id
            WHERE a.location=?
        """, (location,))
    else:
        rows = _db.executeQuery("SELECT status, cost FROM maintenance")

    by_status: dict = {}
    for r in rows:
        st = r["status"] or "Unknown"
        if st not in by_status:
            by_status[st] = {"status": st, "total_cost": 0.0, "count": 0}
        by_status[st]["total_cost"] += float(r["cost"] or 0)
        by_status[st]["count"] += 1

    out = []
    for st in sorted(by_status):
        e = by_status[st]
        e["total_cost"] = round(e["total_cost"], 2)
        out.append(e)
    return out

maintenance_cost_summary = trackCostsByLocation  # alias


def generateReport(location=None, start_date=None, end_date=None) -> dict:
    """SD5: generateReport() — composite full report."""
    return {
        "occupancy":   getOccupancyByCity(),
        "financial":   compareCollectedVsPending(location),
        "maintenance": trackCostsByLocation(location),
        "period":      {"start": start_date, "end": end_date},
    }


def getPerformanceByLocation() -> list:
    """SD5: getPerformanceByLocation() — performance metrics per city."""
    occupancy = getOccupancyByCity()
    results = []
    for o in occupancy:
        loc = o["location"]
        fin = compareCollectedVsPending(loc)
        maint = trackCostsByLocation(loc)
        total_maint_cost = sum(m["total_cost"] for m in maint)
        rate = (o["occupied"] / o["total"] * 100) if o["total"] else 0
        results.append({
            "location":       loc,
            "total_apts":     o["total"],
            "occupied":       o["occupied"],
            "occupancy_rate": round(rate, 1),
            "rent_collected": fin["collected"],
            "rent_pending":   fin["pending"],
            "maint_cost":     round(total_maint_cost, 2),
        })
    return results


# ----------------------------------------------------------
# Dashboard Statistics
# ----------------------------------------------------------
def dashboard_stats(user: dict) -> dict:
    loc = user.get("location")
    if user.get("role") == "Manager":
        loc = None  # Manager sees all locations

    apartments  = get_all_apartments(loc)
    tenants     = get_all_tenants(loc)
    maintenance = get_all_maintenance(loc)
    payments    = get_all_payments(loc)

    return {
        "total_apts":     len(apartments),
        "occupied_apts":  sum(1 for a in apartments if a.get("status") == "Occupied"),
        "total_tenants":  len(tenants),
        "active_maint":   sum(1 for m in maintenance if m.get("status") != "Resolved"),
        "pending_rent":   round(sum(float(p.get("amount") or 0) for p in payments
                                   if p.get("status") in ("Overdue", "Pending")), 2),
        "collected_rent": round(sum(float(p.get("amount") or 0) for p in payments
                                   if p.get("status") == "Paid"), 2),
    }


# ----------------------------------------------------------
# Expiring Leases  (Admin tracking FR)
# ----------------------------------------------------------
def get_expiring_leases(days=30, location=None) -> list:
    future = _days_from_today(int(days))
    today  = _today()
    rows = _db.executeQuery("""
        SELECT t.*, a.apt_number, a.location
        FROM tenants t
        LEFT JOIN apartments a ON t.apt_id=a.id
        WHERE t.status='Active' AND t.lease_end BETWEEN ? AND ?
        ORDER BY t.lease_end
    """, (today, future))
    if location and location != "All":
        rows = [r for r in rows if r.get("location") == location]
    return [dict(r) for r in rows]


# ----------------------------------------------------------
# Audit Log  (Security NFR1)
# ----------------------------------------------------------
def log_audit(user_id, action, entity_type=None, entity_id=None,
              old_value=None, new_value=None):
    _db.executeUpdate("""
        INSERT INTO audit_log(user_id,action,entity_type,entity_id,old_value,new_value)
        VALUES(?,?,?,?,?,?)
    """, (user_id, action, entity_type, entity_id, old_value, new_value))


def get_audit_log(limit=200) -> list:
    rows = _db.executeQuery("""
        SELECT al.*, u.full_name FROM audit_log al
        LEFT JOIN users u ON al.user_id=u.id
        ORDER BY al.timestamp DESC LIMIT ?
    """, (limit,))
    return [dict(r) for r in rows]
