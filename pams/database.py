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
from __future__ import annotations   # allows using 'dict | None' type hints on older Python 3.10

import copy           # provides deep-copy utilities (available for callers if needed)
import datetime       # used to get today's date and calculate future/past dates for leases and payments
import hashlib        # provides the PBKDF2-HMAC function used to securely hash user passwords
import os             # used to build the absolute path to the database file relative to this module
import sqlite3        # the built-in SQLite library — provides Connection, Cursor, and Row objects
import threading      # provides thread-local storage so each thread gets its own database connection
from typing import Optional   # used for type hints like Optional[dict] (means "dict or None")

# ----------------------------------------------------------
# Configuration
# ----------------------------------------------------------
_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "pams.db")  # builds the absolute path: places pams.db one level up from this file, in the project root folder
_SALT = b"PAMS_Paragon_Secure_2025"   # fixed salt bytes mixed into every password hash to prevent rainbow-table attacks (never change after deployment)

# Thread-local storage for connections (thread-safety / scalability NFR3)
_local = threading.local()   # creates a thread-local object; each OS thread will get its own .conn attribute on this object

# ----------------------------------------------------------
# Singleton DatabaseManager (as per Class Diagram)
# ----------------------------------------------------------
class DatabaseManager:
    """
    Singleton class controlling all database access.
    Implements the Singleton pattern from the PAMS Class Diagram to ensure
    a single, centralised and controlled database connection point (NFR1, NFR2).
    """
    _instance: "DatabaseManager | None" = None  # class-level variable holding the one-and-only instance (None until first instantiation)
    _lock = threading.Lock()                     # thread lock that prevents two threads from simultaneously creating the singleton instance

    def __new__(cls):
        with cls._lock:                          # acquires the lock so only one thread enters the creation block at a time
            if cls._instance is None:            # checks if the singleton has not been created yet
                cls._instance = super().__new__(cls)  # creates the actual instance the first time this is called
        return cls._instance                     # returns the same instance every time, ensuring there is always just one DatabaseManager

    def get_connection(self) -> sqlite3.Connection:
        """Return a thread-local SQLite connection with foreign keys enabled."""
        if not hasattr(_local, "conn") or _local.conn is None:    # checks if this thread doesn't have an open connection yet
            _local.conn = sqlite3.connect(_DB_PATH, check_same_thread=False)  # opens a new SQLite connection to pams.db for this thread
            _local.conn.row_factory = sqlite3.Row          # makes query results accessible by column name (e.g. row["full_name"]) instead of just by index
            _local.conn.execute("PRAGMA foreign_keys = ON")  # enables foreign-key constraint enforcement so orphan rows are prevented
            _local.conn.execute("PRAGMA journal_mode = WAL")  # switches to Write-Ahead Logging for better concurrent read performance (NFR4)
        return _local.conn                                   # returns this thread's open connection ready for queries

    def executeQuery(self, query: str, params: tuple = ()) -> list:
        """Execute a SELECT query and return results as a list of dicts."""
        conn = self.get_connection()         # gets (or opens) this thread's database connection
        cur = conn.execute(query, params)    # runs the SELECT SQL with parameterised values to prevent SQL injection
        return [dict(row) for row in cur.fetchall()]  # fetches all result rows and converts each sqlite3.Row to a plain Python dict

    def executeUpdate(self, query: str, params: tuple = ()) -> bool:
        """Execute an INSERT/UPDATE/DELETE and commit. Returns success bool."""
        try:
            conn = self.get_connection()     # gets this thread's connection
            conn.execute(query, params)      # runs the INSERT/UPDATE/DELETE with parameterised values
            conn.commit()                    # saves the change to the database file permanently
            return True                      # signals success to the caller
        except sqlite3.Error as e:
            print(f"[DB ERROR] {e}\n  Query: {query}\n  Params: {params}")  # prints the error and the offending query so developers can debug it
            return False                     # signals failure to the caller so the UI can show an error message

    def executemany(self, query: str, param_list: list) -> bool:
        try:
            conn = self.get_connection()              # gets this thread's connection
            conn.executemany(query, param_list)       # inserts/updates all rows in param_list in a single efficient batch operation
            conn.commit()                             # commits the entire batch at once
            return True                               # signals that all rows were inserted/updated successfully
        except sqlite3.Error as e:
            print(f"[DB ERROR] {e}")                  # prints the error so developers can investigate
            return False                              # signals failure

    def lastrowid(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT and return the new row id."""
        conn = self.get_connection()    # gets this thread's connection
        cur = conn.execute(query, params)  # runs the INSERT and holds the cursor so we can read the new row's ID
        conn.commit()                   # commits the insert so the ID is persisted
        return cur.lastrowid            # returns the auto-incremented primary key of the newly inserted row


# Module-level singleton instance
_db = DatabaseManager()   # creates (or reuses) the single DatabaseManager instance that all functions in this module use


# ----------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------
def _hash(pw: str) -> str:
    # hashes the password using PBKDF2-HMAC-SHA256 with 100,000 iterations and the fixed salt; returns a hex string
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), _SALT, 100_000).hex()


def _today() -> str:
    return datetime.date.today().isoformat()   # returns today's date as a string like '2026-04-06'; used for due dates and audit timestamps


def _days_from_today(days: int) -> str:
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()  # returns a date that is `days` in the future (positive) or past (negative) as an ISO string


def _row(table_rows: list) -> dict | None:
    return table_rows[0] if table_rows else None   # safely returns the first row from a query result, or None if the result was empty


# ----------------------------------------------------------
# Schema Creation
# ----------------------------------------------------------
def _create_schema():
    """Create all database tables and indexes if they do not already exist."""
    conn = _db.get_connection()   # gets (or opens) the SQLite connection for this thread
    conn.executescript("""
    -- --------------------------------------------------------
    -- LOCATIONS table: stores each city that Paragon operates in
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS locations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- auto-incremented unique ID for each city
        name        TEXT    NOT NULL UNIQUE,            -- city name (e.g. 'Bristol') — must be unique
        created_at  TEXT    NOT NULL DEFAULT (date('now'))  -- date this city was added to the system
    );

    -- --------------------------------------------------------
    -- USERS table: stores staff accounts with role-based access (RBAC)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,   -- auto-incremented unique staff ID
        username    TEXT    NOT NULL UNIQUE,             -- login username — must be unique across all staff
        password    TEXT    NOT NULL,                    -- PBKDF2-HMAC-SHA256 hashed password (never stored in plaintext)
        full_name   TEXT    NOT NULL,                    -- staff member's full display name (e.g. 'Alice Morrison')
        role        TEXT    NOT NULL CHECK(role IN (
                        'Administrator','Manager','Front-Desk Staff',
                        'Finance Manager','Maintenance Staff')),  -- enforces the five allowed RBAC roles
        location    TEXT    NOT NULL,                    -- which city branch this staff member belongs to
        email       TEXT    NOT NULL DEFAULT '',         -- email address for notifications
        active      INTEGER NOT NULL DEFAULT 1,          -- 1 = account is active, 0 = soft-deleted/deactivated
        created_at  TEXT    NOT NULL DEFAULT (date('now'))  -- date this account was created
    );

    -- --------------------------------------------------------
    -- APARTMENTS table: stores all apartment units across all cities
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS apartments (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,  -- auto-incremented unique apartment ID
        apt_number   TEXT    NOT NULL UNIQUE,            -- unique apartment code like 'APT-101'
        location     TEXT    NOT NULL,                   -- which city this apartment is in
        type         TEXT    NOT NULL,                   -- apartment type: Studio / 1-Bedroom / 2-Bedroom etc.
        rooms        INTEGER NOT NULL DEFAULT 1,         -- total number of rooms in this apartment unit
        monthly_rent REAL    NOT NULL,                   -- monthly rent amount in pounds sterling
        status       TEXT    NOT NULL DEFAULT 'Vacant'
                        CHECK(status IN ('Vacant','Occupied','Maintenance')),  -- current availability status
        floor        INTEGER NOT NULL DEFAULT 1,         -- which floor the apartment is on in the building
        description  TEXT    NOT NULL DEFAULT '',        -- optional free-text description shown on apartment cards
        FOREIGN KEY (location) REFERENCES locations(name) ON UPDATE CASCADE  -- links to locations table; updates propagate if city renamed
    );

    -- --------------------------------------------------------
    -- TENANTS table: stores each registered tenant and their lease details
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS tenants (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,  -- auto-incremented unique tenant ID
        ni_number               TEXT    NOT NULL UNIQUE,            -- UK National Insurance number — uniquely identifies the person
        full_name               TEXT    NOT NULL,                   -- tenant's full legal name
        phone                   TEXT    NOT NULL DEFAULT '',        -- tenant's contact phone number
        email                   TEXT    NOT NULL DEFAULT '',        -- tenant's contact email address
        occupation              TEXT    NOT NULL DEFAULT '',        -- tenant's job/occupation (used for reference checks)
        reference               TEXT    NOT NULL DEFAULT '',        -- name of the references tenant provided
        apartment_requirements  TEXT    NOT NULL DEFAULT '',        -- tenant's stated apartment preferences
        apt_id                  INTEGER REFERENCES apartments(id) ON DELETE SET NULL,  -- linked apartment; set NULL if apartment deleted
        lease_start             TEXT,                               -- date the lease begins (ISO format YYYY-MM-DD)
        lease_end               TEXT,                               -- date the lease ends (ISO format YYYY-MM-DD)
        deposit                 REAL    NOT NULL DEFAULT 0,         -- security deposit amount paid by the tenant in pounds
        monthly_rent            REAL    NOT NULL DEFAULT 0,         -- agreed monthly rent amount in pounds
        status                  TEXT    NOT NULL DEFAULT 'Active'
                                    CHECK(status IN ('Active','Leaving','Inactive','Archived')),  -- current tenancy status
        notes                   TEXT    NOT NULL DEFAULT '',        -- free-text notes added by staff (e.g. maintenance history)
        early_leave_notice_date TEXT,                               -- date the tenant submitted Early Leave notice (if applicable)
        created_at              TEXT    NOT NULL DEFAULT (date('now'))  -- date this tenant was registered in the system
    );

    -- --------------------------------------------------------
    -- LEASES table: formal lease records (separate from inline tenant data)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS leases (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,  -- auto-incremented unique lease ID
        tenant_id            INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,   -- which tenant this lease belongs to
        apartment_id         INTEGER NOT NULL REFERENCES apartments(id) ON DELETE CASCADE, -- which apartment is leased
        start_date           TEXT    NOT NULL,   -- lease start date in ISO format
        end_date             TEXT    NOT NULL,   -- lease end date in ISO format
        monthly_rent         REAL    NOT NULL,   -- monthly rent agreed in this lease contract
        deposit              REAL    NOT NULL DEFAULT 0,   -- deposit amount recorded in this lease
        status               TEXT    NOT NULL DEFAULT 'Active'
                                 CHECK(status IN ('Active','Terminated','Expired','Archived')),  -- lifecycle status of this lease
        early_termination_date TEXT,   -- date this lease was terminated early (only set if terminated before end_date)
        penalty_amount       REAL    DEFAULT 0,  -- penalty charged for early termination (5% of monthly rent)
        created_at           TEXT    NOT NULL DEFAULT (date('now'))  -- date this lease record was created
    );

    -- --------------------------------------------------------
    -- PAYMENTS table: invoices and payment records for rent and other charges
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS payments (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,  -- auto-incremented unique payment/invoice ID
        tenant_id     INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,  -- which tenant this payment belongs to
        lease_id      INTEGER REFERENCES leases(id) ON DELETE SET NULL,           -- linked lease (optional); set NULL if lease deleted
        amount        REAL    NOT NULL,   -- amount due/paid in pounds sterling
        due_date      TEXT    NOT NULL,   -- date this invoice/payment is due (ISO format)
        paid_date     TEXT,               -- date the tenant actually paid; NULL means not yet paid
        status        TEXT    NOT NULL DEFAULT 'Pending'
                          CHECK(status IN ('Pending','Paid','Overdue')),  -- current payment status
        type          TEXT    NOT NULL DEFAULT 'Rent',   -- payment category: 'Rent', 'Deposit', 'Early Leave Penalty' etc.
        late_notified INTEGER NOT NULL DEFAULT 0,        -- 1 if the system already sent a late-payment notification email
        notes         TEXT    NOT NULL DEFAULT ''        -- optional staff notes about this payment
    );

    -- --------------------------------------------------------
    -- MAINTENANCE table: requests logged for apartment repairs/issues
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS maintenance (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,  -- auto-incremented unique maintenance request ID
        tenant_id          INTEGER REFERENCES tenants(id) ON DELETE SET NULL,    -- tenant who reported the issue
        apt_id             INTEGER REFERENCES apartments(id) ON DELETE CASCADE,  -- apartment the issue is in
        title              TEXT    NOT NULL,   -- short summary/title of the issue (e.g. 'Leaking Tap')
        description        TEXT    NOT NULL DEFAULT '',  -- detailed description of the fault provided by the tenant or staff
        priority           TEXT    NOT NULL DEFAULT 'Medium'
                               CHECK(priority IN ('Low','Medium','High','Critical')),  -- urgency level shown as coloured badge
        status             TEXT    NOT NULL DEFAULT 'Open'
                               CHECK(status IN ('Open','Assigned','Scheduled','In Progress','Resolved')),  -- current progress stage
        reported_date      TEXT    NOT NULL DEFAULT (date('now')),  -- date the issue was reported
        scheduled_date     TEXT,   -- date maintenance work is scheduled to begin (set by staff)
        resolved_date      TEXT,   -- date the issue was marked as fully resolved
        assigned_to        INTEGER REFERENCES users(id) ON DELETE SET NULL,  -- which maintenance staff member is assigned
        cost               REAL    NOT NULL DEFAULT 0,          -- total repair cost in pounds (filled in when resolved)
        time_spent         REAL    NOT NULL DEFAULT 0,          -- total hours spent on this repair
        communication_sent INTEGER NOT NULL DEFAULT 0,          -- 1 if a notification was sent to the tenant about scheduling
        notes              TEXT    NOT NULL DEFAULT ''          -- internal staff notes about the repair
    );

    -- --------------------------------------------------------
    -- COMPLAINTS table: formal complaints raised by tenants
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS complaints (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- auto-incremented unique complaint ID
        tenant_id   INTEGER REFERENCES tenants(id) ON DELETE CASCADE,  -- which tenant raised the complaint
        title       TEXT    NOT NULL,                   -- short summary of the complaint (e.g. 'Noisy Neighbours')
        description TEXT    NOT NULL DEFAULT '',        -- full complaint details written by the tenant or staff
        status      TEXT    NOT NULL DEFAULT 'Open'
                        CHECK(status IN ('Open','In Progress','Resolved')),  -- current resolution status shown as a badge
        created_at  TEXT    NOT NULL DEFAULT (date('now')),  -- date the complaint was submitted
        resolved_at TEXT    -- date the complaint was marked as resolved (NULL while still open)
    );

    -- --------------------------------------------------------
    -- AUDIT LOG table: immutable record of every data change for security (NFR1)
    -- --------------------------------------------------------
    CREATE TABLE IF NOT EXISTS audit_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- auto-incremented unique log entry ID
        user_id     INTEGER,     -- ID of the staff member who made the change (NULL for system actions)
        action      TEXT    NOT NULL,   -- description of what was done (e.g. 'ADD_TENANT', 'DELETE_USER')
        entity_type TEXT,    -- type of record that was changed (e.g. 'tenant', 'apartment')
        entity_id   TEXT,    -- ID of the specific record that was changed
        old_value   TEXT,    -- snapshot of the record before the change (JSON string)
        new_value   TEXT,    -- snapshot of the record after the change (JSON string)
        timestamp   TEXT    NOT NULL DEFAULT (datetime('now'))  -- exact date and time the change was made
    );

    -- --------------------------------------------------------
    -- PERFORMANCE INDEXES: speeds up the most common queries (NFR4)
    -- --------------------------------------------------------
    CREATE INDEX IF NOT EXISTS idx_tenants_apt    ON tenants(apt_id);       -- speeds up "which tenant is in apartment X?"
    CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);       -- speeds up filtering tenants by Active/Leaving etc.
    CREATE INDEX IF NOT EXISTS idx_payments_tenant ON payments(tenant_id);  -- speeds up "all payments for tenant X"
    CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);     -- speeds up filtering payments by Paid/Pending/Overdue
    CREATE INDEX IF NOT EXISTS idx_payments_due    ON payments(due_date);   -- speeds up looking up overdue invoices by date
    CREATE INDEX IF NOT EXISTS idx_maint_apt      ON maintenance(apt_id);   -- speeds up "all maintenance for apartment X"
    CREATE INDEX IF NOT EXISTS idx_maint_status   ON maintenance(status);   -- speeds up filtering maintenance by status
    CREATE INDEX IF NOT EXISTS idx_complaints_tenant ON complaints(tenant_id);  -- speeds up "all complaints for tenant X"
    """)
    conn.commit()   # saves all CREATE TABLE and CREATE INDEX statements to disk


# ----------------------------------------------------------
# Seed Data
# ----------------------------------------------------------
def _seed_data():
    """Populate the database with realistic mock data for demo/testing."""
    conn = _db.get_connection()   # gets the thread-local SQLite connection to run all inserts on

    # ── Locations ──────────────────────────────────────────
    locations = ["Bristol", "Cardiff", "London", "Manchester"]   # the four cities Paragon operates in
    conn.executemany(
        "INSERT OR IGNORE INTO locations(name) VALUES(?)",   # inserts each city name; OR IGNORE skips duplicates if re-run
        [(l,) for l in locations]    # wraps each city string in a single-element tuple as executemany requires
    )

    # ── Users  (RBAC roles) ────────────────────────────────
    users = [
        # Each tuple: (username, hashed_password, full_name, role, location, email)
        ("admin_bristol", _hash("admin123"), "Alice Morrison",   "Administrator",    "Bristol",    "alice@paragon.com"),    # Bristol admin — default login: admin_bristol / admin123
        ("admin_london",  _hash("admin123"), "David Okafor",     "Administrator",    "London",     "david@paragon.com"),    # London admin
        ("manager",       _hash("manager123"), "Sarah Whitfield","Manager",          "Bristol",    "sarah@paragon.com"),    # Manager — can see all locations, login: manager / manager123
        ("frontdesk1",    _hash("front123"),  "James Patel",     "Front-Desk Staff", "Bristol",    "james@paragon.com"),    # Bristol front-desk staff
        ("frontdesk2",    _hash("front123"),  "Lily Chen",       "Front-Desk Staff", "Manchester", "lily@paragon.com"),     # Manchester front-desk staff
        ("finance1",      _hash("finance123"),"Robert Hughes",   "Finance Manager",  "Bristol",    "robert@paragon.com"),   # Bristol finance manager
        ("maint1",        _hash("maint123"),  "Carlos Rivera",   "Maintenance Staff","Bristol",    "carlos@paragon.com"),   # Bristol maintenance worker (assigned to requests)
        ("maint2",        _hash("maint123"),  "Priya Singh",     "Maintenance Staff","London",     "priya@paragon.com"),    # London maintenance worker
        ("admin_manc",    _hash("admin123"),  "Fiona Walsh",     "Administrator",    "Manchester", "fiona@paragon.com"),    # Manchester admin
        ("admin_cardiff", _hash("admin123"),  "Rhys Evans",      "Administrator",    "Cardiff",    "rhys@paragon.com"),     # Cardiff admin
        ("finance2",      _hash("finance123"),"Natasha Peters",  "Finance Manager",  "London",     "natasha@paragon.com"),  # London finance manager
    ]
    conn.executemany("""
        INSERT OR IGNORE INTO users(username,password,full_name,role,location,email)
        VALUES(?,?,?,?,?,?)
    """, users)   # inserts all 11 demo staff accounts; OR IGNORE skips any already present

    # ── Apartments ────────────────────────────────────────
    apts = [
        # Each tuple: (apt_number, location, type, rooms, monthly_rent, status, floor, description)
        # Bristol
        ("APT-101","Bristol","Studio",    1,  850.0,"Occupied",1,"Modern studio with open-plan living"),     # ground-floor occupied studio in Bristol
        ("APT-102","Bristol","1-Bedroom", 1, 1050.0,"Occupied",1,"Bright 1-bed with private balcony"),       # ground-floor occupied 1-bed in Bristol
        ("APT-103","Bristol","2-Bedroom", 2, 1400.0,"Vacant",  1,"Spacious 2-bed, freshly renovated"),      # ground-floor vacant 2-bed in Bristol
        ("APT-201","Bristol","2-Bedroom", 2, 1350.0,"Occupied",2,"South-facing 2-bed, river views"),        # 2nd-floor occupied 2-bed with river view in Bristol
        ("APT-202","Bristol","3-Bedroom", 3, 1800.0,"Occupied",2,"Large family unit with garden access"),   # 2nd-floor large occupied 3-bed in Bristol
        ("APT-301","Bristol","Penthouse", 4, 3200.0,"Vacant",  3,"Luxury penthouse, 360-degree views"),     # 3rd-floor vacant luxury penthouse in Bristol
        ("APT-104","Bristol","Studio",    1,  820.0,"Maintenance",1,"Undergoing refurbishment"),            # ground-floor studio currently under maintenance in Bristol
        # London
        ("APT-L01","London","Studio",     1, 1400.0,"Occupied",1,"Bridge view studio, zone 1"),             # zone 1 London occupied studio with river/bridge views
        ("APT-L02","London","1-Bedroom",  1, 1750.0,"Occupied",1,"Prime Shoreditch location"),              # premium Shoreditch 1-bed in London
        ("APT-L03","London","2-Bedroom",  2, 2400.0,"Vacant",  2,"Excellent transport links"),             # vacant London 2-bed with good transport connections
        ("APT-L04","London","3-Bedroom",  3, 3100.0,"Occupied",3,"Luxury flat, concierge service"),        # high-end London 3-bed with concierge
        # Manchester
        ("APT-M01","Manchester","2-Bedroom",2,1100.0,"Occupied",1,"City centre, close to amenities"),      # city-centre Manchester 2-bed
        ("APT-M02","Manchester","1-Bedroom",1, 900.0,"Vacant",  1,"Northern Quarter, character property"), # vacant Northern Quarter 1-bed in Manchester
        ("APT-M03","Manchester","Studio",   1, 750.0,"Occupied",1,"Compact modern studio"),                # small modern Manchester studio
        # Cardiff
        ("APT-C01","Cardiff","1-Bedroom",  1, 850.0,"Occupied",1,"Cardiff Bay area, waterfront"),          # Cardiff Bay 1-bed near waterfront
        ("APT-C02","Cardiff","2-Bedroom",  2,1100.0,"Vacant",  1,"Quiet residential area, parking included"),  # Cardiff vacant 2-bed with parking
        ("APT-C03","Cardiff","Studio",     1, 700.0,"Occupied",1,"City centre, compact and efficient"),    # Cardiff city-centre studio
    ]
    conn.executemany("""
        INSERT OR IGNORE INTO apartments(apt_number,location,type,rooms,monthly_rent,status,floor,description)
        VALUES(?,?,?,?,?,?,?,?)
    """, apts)   # inserts all 18 demo apartments; OR IGNORE skips any already present
    conn.commit()   # saves locations, users, and apartments to disk

    # ── Helper: get IDs ────────────────────────────────────
    def apt_id(num): return _row(_db.executeQuery("SELECT id FROM apartments WHERE apt_number=?", (num,)))["id"]   # looks up an apartment's integer ID by its code (e.g. 'APT-102' → 3)

    def _lr(back, fwd):
        # calculates a lease date range: `back` months ago for start and `fwd` months ahead for end
        s = (datetime.date.today() - datetime.timedelta(days=30*back)).isoformat()   # lease start date = today minus `back` months
        e = (datetime.date.today() + datetime.timedelta(days=30*fwd)).isoformat()    # lease end date = today plus `fwd` months
        return s, e   # returns (start_date, end_date) as a pair of ISO strings

    # ── Tenants ───────────────────────────────────────────
    tenants_data = [
        # Each tuple: (ni_number, full_name, phone, email, occupation, reference, req, apt_code, back_months, fwd_months, deposit, rent)
        ("NI-AA123456A","Oliver Thompson","07700111001","oliver@email.com","Software Engineer","John Smith","1-Bedroom",    "APT-102",6,12,1050.0,1050.0),   # tenant in 1-bed APT-102 (Bristol), lease started 6mo ago ending in 12mo
        ("NI-BB234567B","Emma Williams",  "07700111002","emma@email.com",  "Nurse",           "Dr. Jones",  "1-Bedroom",    "APT-101",3, 9, 850.0, 850.0),   # tenant in studio APT-101 (Bristol)
        ("NI-CC345678C","Noah Brown",     "07700111003","noah@email.com",  "Teacher",         "Mary Green", "2-Bedroom",    "APT-201",1,11,1350.0,1350.0),   # tenant in 2-bed APT-201 (Bristol)
        ("NI-DD456789D","Sophia Davis",   "07700111004","sophia@email.com","Accountant",      "Peter Davis","3-Bedroom",    "APT-202",4, 3,1800.0,1800.0),   # tenant in 3-bed APT-202 (Bristol) — lease expiring in ~90 days for demo
        ("NI-EE567890E","Liam Wilson",    "07700111005","liam@email.com",  "Architect",       "Jane Wilson","Studio",       "APT-L01",2,10,1400.0,1400.0),   # tenant in London studio APT-L01
        ("NI-FF678901F","Isabella Moore", "07700111006","isab@email.com",  "Marketing Manager","Tom Moore", "1-Bedroom",    "APT-L02",5, 7,1750.0,1750.0),   # tenant in London 1-bed APT-L02
        ("NI-GG789012G","Mason Taylor",   "07700111007","mason@email.com", "Chef",            "Cathy Taylor","2-Bedroom",   "APT-M01",6, 1,1100.0,1100.0),   # tenant in Manchester 2-bed APT-M01 — lease expiring in ~30 days for demo
        ("NI-HH890123H","Ava Anderson",   "07700111008","ava@email.com",   "Solicitor",       "Bob Anderson","1-Bedroom",   "APT-C01",3, 9, 850.0, 850.0),   # tenant in Cardiff 1-bed APT-C01
        ("NI-II901234I","Jack Robinson",  "07700111009","jack@email.com",  "Doctor",          "NHS Trust",  "3-Bedroom",    "APT-L04",2,10,3100.0,3100.0),   # tenant in London luxury 3-bed APT-L04
        ("NI-JJ012345J","Zoe Martinez",   "07700111010","zoe@email.com",   "Designer",        "Creative Co","Studio",       "APT-M03",1,11, 750.0, 750.0),   # tenant in Manchester studio APT-M03
        ("NI-KK123456K","Harry Evans",    "07700111011","harry@email.com", "Engineer",        "Rhys Evans", "Studio",       "APT-C03",4, 2, 700.0, 700.0),   # tenant in Cardiff studio APT-C03 — lease expiring in ~60 days for demo
    ]
    for ni,name,phone,email,occ,ref,req,apt_num,back,fwd,dep,rent in tenants_data:   # unpacks each tenant tuple
        ls, le = _lr(back, fwd)   # calculates lease start and end dates for this tenant
        aid = apt_id(apt_num)     # looks up the integer apartment ID for this tenant's apartment
        conn.execute("""
            INSERT OR IGNORE INTO tenants
            (ni_number,full_name,phone,email,occupation,reference,
             apartment_requirements,apt_id,lease_start,lease_end,
             deposit,monthly_rent,status,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'Active','',date('now'))
        """, (ni,name,phone,email,occ,ref,req,aid,ls,le,dep,rent))   # inserts the tenant row; OR IGNORE skips duplicates

    conn.commit()   # saves all tenant inserts to disk

    # ── Leases (mirrors tenant data) ──────────────────────
    tenant_rows = _db.executeQuery("SELECT id,apt_id,lease_start,lease_end,monthly_rent,deposit FROM tenants")  # fetches every tenant to create a matching lease record
    for t in tenant_rows:   # loops through each tenant
        conn.execute("""
            INSERT OR IGNORE INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit,status)
            SELECT ?,?,?,?,?,?,'Active' WHERE NOT EXISTS(
                SELECT 1 FROM leases WHERE tenant_id=?)
        """, (t["id"],t["apt_id"],t["lease_start"],t["lease_end"],t["monthly_rent"],t["deposit"],t["id"]))  # inserts a lease only if one doesn't already exist for this tenant
    conn.commit()   # saves all lease inserts to disk

    # ── Payments (3 months history per tenant) ────────────
    today = datetime.date.today()   # today's date used to calculate historical due dates
    pid_rows = _db.executeQuery("SELECT id,monthly_rent FROM tenants")   # fetches all tenants so we can create payment history for each
    for t in pid_rows:   # loops through every tenant to create 3 months of payment records
        for m in (3, 2, 1):   # iterates: 3 months ago, 2 months ago, 1 month ago
            due = (today - datetime.timedelta(days=30*m)).replace(day=1).isoformat()   # sets due date to the 1st of the month `m` months ago
            paid = due if m > 1 else None    # marks months 3 and 2 as paid; month 1 is left unpaid (overdue) for demo realism
            status = "Paid" if paid else "Overdue"   # sets status to 'Paid' for older months and 'Overdue' for last month
            # Avoid duplicates
            existing = _db.executeQuery(
                "SELECT 1 FROM payments WHERE tenant_id=? AND due_date=? AND type='Rent'",
                (t["id"], due)
            )    # checks if a payment record already exists for this tenant + month to prevent duplicates on re-seed
            if not existing:   # only inserts if no duplicate found
                conn.execute("""
                    INSERT INTO payments(tenant_id,amount,due_date,paid_date,status,type,late_notified)
                    VALUES(?,?,?,?,?,'Rent',?)
                """, (t["id"],t["monthly_rent"],due,paid,status,1 if m==1 else 0))   # adds the rent payment; sets late_notified=1 for the overdue month
    conn.commit()   # saves all payment records to disk

    # ── Maintenance Requests ───────────────────────────────
    def tid(ni):   # looks up a tenant's integer ID by their NI number
        r = _row(_db.executeQuery("SELECT id FROM tenants WHERE ni_number=?", (ni,)))
        return r["id"] if r else None   # returns the ID or None if not found
    def aid(num):   # looks up an apartment's integer ID by its code letter (reuses same logic as above)
        r = _row(_db.executeQuery("SELECT id FROM apartments WHERE apt_number=?", (num,)))
        return r["id"] if r else None
    def uid(uname):   # looks up a staff user's integer ID by their username
        r = _row(_db.executeQuery("SELECT id FROM users WHERE username=?", (uname,)))
        return r["id"] if r else None

    maint_data = [
        # Each tuple: (tenant_id, apt_id, title, description, priority, status, reported, scheduled, resolved, assigned_user_id, cost, time_hours, comm_sent, notes)
        (tid("NI-AA123456A"),aid("APT-102"),"Leaking Tap",    "Kitchen tap dripping continuously",   "High",    "Resolved",   _days_from_today(-20),_days_from_today(-18),_days_from_today(-17),uid("maint1"),120.0,3.0,1,"Parts replaced"),    # resolved tap repair in APT-102 — cost £120, took 3 hours
        (tid("NI-BB234567B"),aid("APT-101"),"Broken Heater",  "Radiator not working",                "High",    "In Progress",_days_from_today(-5), _days_from_today(2), None,                  uid("maint1"),  0.0,0.0,1,"Ordered replacement part"),   # heating issue in APT-101 still in progress
        (tid("NI-CC345678C"),aid("APT-201"),"Cracked Window",  "Bedroom window cracked",             "Medium",  "Open",       _days_from_today(-2), None,               None,                  uid("maint1"),  0.0,0.0,0,""),    # newly reported cracked window in APT-201, not yet assigned
        (tid("NI-DD456789D"),aid("APT-202"),"Lift Fault",     "Lift on floor 2 not stopping",        "Critical","Open",       _days_from_today(-1), None,               None,                  uid("maint1"),  0.0,0.0,0,""),    # critical lift fault in APT-202 reported yesterday
        (tid("NI-EE567890E"),aid("APT-L01"),"Pest Control",   "Cockroaches reported in kitchen",     "Medium",  "Resolved",   _days_from_today(-30),_days_from_today(-26),_days_from_today(-25),uid("maint2"),200.0,5.0,1,"Professional extermination"),   # pest issue resolved in London APT-L01
        (tid("NI-FF678901F"),aid("APT-L02"),"Faulty Electrics","Intermittent power in living room",  "High",    "In Progress",_days_from_today(-3), _days_from_today(1), None,                  uid("maint2"),  0.0,0.0,1,"Electrician booked"),    # electrical fault in London APT-L02, electrician coming tomorrow
        (tid("NI-GG789012G"),aid("APT-M01"),"Damp Patch",     "Damp patch on bathroom ceiling",     "Medium",  "Assigned",   _days_from_today(-7), _days_from_today(3), None,                  uid("maint1"), 0.0,0.0,1,"Damp specialist assigned"),   # damp in Manchester APT-M01, specialist assigned
        (tid("NI-HH890123H"),aid("APT-C01"),"Blocked Drain",  "Shower drain slow to empty",          "Low",     "Resolved",   _days_from_today(-14),_days_from_today(-12),_days_from_today(-12),uid("maint1"),45.0,1.5,1,"Drain cleared"),    # drain cleared in Cardiff APT-C01 — cost £45, 1.5 hours
    ]
    for row in maint_data:   # loops through each maintenance request
        existing = _db.executeQuery("SELECT 1 FROM maintenance WHERE tenant_id=? AND title=?", (row[0], row[2]))   # checks for duplicates by tenant + title
        if not existing:   # only inserts if this request doesn't already exist
            conn.execute("""
                INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,status,
                    reported_date,scheduled_date,resolved_date,assigned_to,cost,time_spent,
                    communication_sent,notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, row)   # inserts the maintenance request with all 14 fields

    # ── Complaints ────────────────────────────────────────
    complaints_data = [
        # Each tuple: (tenant_id, title, description, status, created_at, resolved_at)
        (tid("NI-AA123456A"),"Noisy Neighbours",  "Upstairs neighbours very loud past midnight","Open",       _days_from_today(-3), None),    # new open complaint from Oliver (APT-102)
        (tid("NI-CC345678C"),"Parking Issue",     "Another tenant is using my parking space",   "Open",       _days_from_today(-2), None),    # new open complaint from Noah (APT-201)
        (tid("NI-EE567890E"),"Water Pressure Low","Water pressure has been low for a week",      "Resolved",   _days_from_today(-10),_days_from_today(-8)),   # resolved water pressure complaint — took 2 days to fix
        (tid("NI-GG789012G"),"Rubbish Collection","Bins not collected for two weeks",            "In Progress",_days_from_today(-5), None),   # complaint in progress about missed bin collections in Manchester
        (tid("NI-II901234I"),"Intercom Broken",   "Intercom system at front door not working",  "Open",       _days_from_today(-1), None),    # newly reported intercom fault from Jack (London APT-L04)
    ]
    for row in complaints_data:   # loops through each demo complaint
        existing = _db.executeQuery("SELECT 1 FROM complaints WHERE tenant_id=? AND title=?", (row[0], row[1]))   # checks for duplicates by tenant + title
        if not existing:   # only inserts if this complaint doesn't already exist
            conn.execute("""
                INSERT INTO complaints(tenant_id,title,description,status,created_at,resolved_at)
                VALUES(?,?,?,?,?,?)
            """, row)   # inserts the complaint with all 6 fields

    conn.commit()   # saves all maintenance requests and complaints to disk


# ----------------------------------------------------------
# Public Init (called by main.py at startup)
# ----------------------------------------------------------
def init_db():
    """
    Initialise the SQLite database: create schema and seed mock data.
    Idempotent — safe to call multiple times.
    """
    _create_schema()   # runs all CREATE TABLE and CREATE INDEX statements (skips existing ones)
    # Only seed if the database appears to be new/empty
    users = _db.executeQuery("SELECT COUNT(*) as c FROM users")   # counts how many user rows already exist
    if users and users[0]["c"] == 0:   # if the users table is empty, this is a fresh database that needs demo data
        _seed_data()   # populates all tables with the realistic demo locations, staff, apartments, tenants, payments, maintenance, and complaints


# ----------------------------------------------------------
# Authentication  (SD flows: verifyRoleAccess)
# ----------------------------------------------------------
def login(username: str, password: str) -> Optional[dict]:
    """Authenticate user. Returns user dict or None. (SD1–SD5 entry point)"""
    pw = _hash(password)   # hashes the entered password the same way it was stored — never compares plaintext
    rows = _db.executeQuery(
        "SELECT * FROM users WHERE username=? AND password=? AND active=1",
        (username, pw)
    )   # looks up a user whose username AND hashed password match AND whose account is active (not soft-deleted)
    if rows:   # if a matching active user was found
        u = dict(rows[0])   # converts the sqlite3.Row result to a plain Python dict so it can be easily passed around
        _db.executeUpdate(
            "UPDATE users SET created_at=created_at WHERE id=?", (u["id"],)
        )   # no-op update just to trigger any future audit hooks; keeps the connection fresh
        return u   # returns the full user record (id, username, role, location, etc.) to the login screen
    return None   # returns None if no matching user was found, signalling authentication failure

authenticate = login  # backward-compat alias — older code can call authenticate() instead of login()


# ----------------------------------------------------------
# Users  (Account / User Management FR)
# ----------------------------------------------------------
def get_all_users(location=None) -> list:
    if location and location != "All":   # if a specific city was requested (not "All")
        rows = _db.executeQuery(
            "SELECT * FROM users WHERE location=? ORDER BY role, full_name", (location,))  # returns only staff from that city, sorted by role then name
    else:
        rows = _db.executeQuery("SELECT * FROM users ORDER BY role, full_name")   # returns all staff from all cities, sorted by role then name
    return [dict(r) for r in rows]   # converts each sqlite3.Row to a plain dict for easy use in the UI


def add_user(username, password, full_name, role, location, email=""):
    return _db.executeUpdate("""
        INSERT INTO users(username,password,full_name,role,location,email)
        VALUES(?,?,?,?,?,?)
    """, (username, _hash(password), full_name, role, location, email or ""))   # inserts a new staff account; the password is hashed before storage


def update_user(uid, full_name, role, location, email, active):
    return _db.executeUpdate("""
        UPDATE users SET full_name=?,role=?,location=?,email=?,active=? WHERE id=?
    """, (full_name, role, location, email or "", int(bool(active)), uid))   # updates the staff member's profile details; converts the active flag to int (1=active, 0=inactive)


def updateUserPassword(uid: int, password: str):
    return _db.executeUpdate(
        "UPDATE users SET password=? WHERE id=?", (_hash(password), uid))   # replaces the stored hashed password with a new hash of the provided new password

update_user_password = updateUserPassword  # alias so other modules can call update_user_password() if preferred


def delete_user(uid):
    """Soft-delete: mark inactive (preserves audit trail)."""
    return _db.executeUpdate("UPDATE users SET active=0 WHERE id=?", (uid,))   # sets active=0 instead of physically deleting the row, preserving the audit history


# ----------------------------------------------------------
# Locations  (Multi-city scalability NFR3, FR7)
# ----------------------------------------------------------
def get_all_locations() -> list:
    rows = _db.executeQuery("SELECT name FROM locations ORDER BY name")   # fetches all city names sorted alphabetically
    return [r["name"] for r in rows]   # returns a plain list of city name strings (e.g. ['Bristol', 'Cardiff', 'London', 'Manchester'])


def expandBusiness(name: str):
    """SD5: Manager expands business to a new city."""
    name = (name or "").strip()   # trims whitespace from the city name; guards against None being passed in
    if not name:   # if the name is empty after stripping, do nothing
        return
    _db.executeUpdate("INSERT OR IGNORE INTO locations(name) VALUES(?)", (name,))   # adds the new city to the locations table; OR IGNORE prevents errors if the city already exists

add_location = expandBusiness  # alias so the views can call add_location() instead of expandBusiness()


# ----------------------------------------------------------
# Apartments  (Apartment Management FR2)
# ----------------------------------------------------------
def get_all_apartments(location=None) -> list:
    if location and location != "All":   # if a specific city filter was provided
        rows = _db.executeQuery("""
            SELECT * FROM apartments WHERE location=?
            ORDER BY location, apt_number
        """, (location,))   # returns only apartments in the requested city, sorted by city then apartment code
    else:
        rows = _db.executeQuery(
            "SELECT * FROM apartments ORDER BY location, apt_number")   # returns all apartments across all cities
    return [dict(r) for r in rows]   # converts each sqlite3.Row to a plain dict for the apartment view table


def add_apartment(apt_number, location, apt_type, rooms, monthly_rent, floor=1, desc=""):
    return _db.executeUpdate("""
        INSERT INTO apartments(apt_number,location,type,rooms,monthly_rent,floor,description)
        VALUES(?,?,?,?,?,?,?)
    """, (apt_number, location, apt_type, int(rooms), float(monthly_rent), int(floor), desc or ""))   # inserts a new apartment; casts rooms and floor to int and rent to float to ensure correct types


def update_apartment(apt_id, apt_number, location, apt_type, rooms, monthly_rent,
                     status, floor, desc):
    return _db.executeUpdate("""
        UPDATE apartments SET apt_number=?,location=?,type=?,rooms=?,monthly_rent=?,
            status=?,floor=?,description=?
        WHERE id=?
    """, (apt_number, location, apt_type, int(rooms), float(monthly_rent),
          status, int(floor), desc or "", apt_id))   # updates all editable fields of the apartment; id is used in the WHERE clause to target the correct row


def delete_apartment(apt_id):
    return _db.executeUpdate("DELETE FROM apartments WHERE id=?", (apt_id,))   # permanently deletes the apartment row; cascades to maintenance records linked to it


def get_vacant_apartments() -> list:
    rows = _db.executeQuery("""
        SELECT id, apt_number, location FROM apartments
        WHERE status='Vacant' ORDER BY location, apt_number
    """)   # fetches only apartments with Vacant status so new tenants can be assigned to them
    return [(r["id"], f"{r['apt_number']} ({r['location']})") for r in rows]   # returns a list of (id, display_label) tuples for populating the "Select Apartment" dropdown


# ----------------------------------------------------------
# Tenants  (Tenant Management FR1, SD2 Register New Tenant)
# ----------------------------------------------------------
def _tenant_with_join(row: dict) -> dict:
    """Enriches a single tenant dict with apt_number and location from the apartments table."""
    apt = None
    if row.get("apt_id"):   # only performs the join if the tenant has an assigned apartment
        apts = _db.executeQuery(
            "SELECT apt_number, location FROM apartments WHERE id=?", (row["apt_id"],))   # fetches the apartment code and city for the tenant's apartment
        apt = apts[0] if apts else None   # uses the first result or None if the apartment was not found
    row["apt_number"] = apt["apt_number"] if apt else None   # adds the apartment code (e.g. 'APT-102') to the tenant dict
    row["location"]   = apt["location"]   if apt else None   # adds the city name to the tenant dict for display in the tenant table
    return row   # returns the enriched tenant dict with apartment info included


def get_all_tenants(location=None) -> list:
    rows = _db.executeQuery("""
        SELECT t.*, a.apt_number, a.location
        FROM tenants t
        LEFT JOIN apartments a ON t.apt_id = a.id
        ORDER BY t.full_name
    """)   # fetches all tenants with their apartment codes and cities in a single JOIN query, sorted by name
    if location and location != "All":   # if a city filter was provided
        rows = [r for r in rows if r.get("location") == location]   # filters the results down to only tenants in that city
    return [dict(r) for r in rows]   # converts to plain dicts for the tenant view table


def get_tenant_by_id(tid) -> Optional[dict]:
    rows = _db.executeQuery("""
        SELECT t.*, a.apt_number, a.location
        FROM tenants t
        LEFT JOIN apartments a ON t.apt_id = a.id
        WHERE t.id=?
    """, (tid,))   # fetches a single tenant by their ID, including their apartment number and city
    return dict(rows[0]) if rows else None   # returns the tenant dict or None if no tenant with that ID was found


def add_tenant(ni, name, phone, email, occupation, reference,
               apartment_requirements, apt_id, lease_start, lease_end,
               deposit, monthly_rent):
    """
    SD2: Register New Tenant.
    Creates tenant record, updates apartment occupancy, creates lease.
    """
    # Validate NI uniqueness (SD2 checkExistingNiNumber)
    if _db.executeQuery("SELECT 1 FROM tenants WHERE ni_number=?", (ni,)):   # checks if this NI number is already registered in the system
        raise ValueError(f"NI number '{ni}' already exists in the system.")   # raises an error that the UI will catch and show to the user

    _db.executeUpdate("""
        INSERT INTO tenants(ni_number,full_name,phone,email,occupation,reference,
            apartment_requirements,apt_id,lease_start,lease_end,deposit,monthly_rent)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (ni, name, phone or "", email or "", occupation or "", reference or "",
          apartment_requirements or "", apt_id, lease_start, lease_end,
          float(deposit), float(monthly_rent)))   # inserts the new tenant record; empty strings replace None for optional text fields

    tenant_id = _db.executeQuery("SELECT last_insert_rowid() as id")[0]["id"]   # retrieves the auto-generated ID of the tenant just inserted

    # updateOccupancyStatus (SD2)
    if apt_id:   # only updates the apartment if one was assigned
        _db.executeUpdate("UPDATE apartments SET status='Occupied' WHERE id=?", (apt_id,))   # marks the apartment as Occupied now that a tenant has been assigned

    # createLease (SD2)
    _db.executeUpdate("""
        INSERT INTO leases(tenant_id,apartment_id,start_date,end_date,monthly_rent,deposit)
        VALUES(?,?,?,?,?,?)
    """, (tenant_id, apt_id, lease_start, lease_end, float(monthly_rent), float(deposit)))   # creates a formal lease record linking this tenant to their apartment

    return tenant_id   # returns the new tenant's ID so the caller can navigate to their profile


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
          float(deposit), float(monthly_rent), status, notes or "", tid))   # updates all editable tenant fields; casts deposit and rent to float; empty strings replace None for text fields


def delete_tenant(tid):
    """Remove tenant and free their apartment."""
    tenant = get_tenant_by_id(tid)   # fetches the tenant first so we know which apartment to free up
    if tenant and tenant.get("apt_id"):   # if the tenant has an apartment assigned
        _db.executeUpdate(
            "UPDATE apartments SET status='Vacant' WHERE id=?", (tenant["apt_id"],))   # marks the apartment as Vacant again when the tenant is removed
    return _db.executeUpdate("DELETE FROM tenants WHERE id=?", (tid,))   # permanently deletes the tenant row; cascades to their payments and lease records


# ----------------------------------------------------------
# Payments / Invoices  (Payment & Billing FR3, SD1)
# ----------------------------------------------------------
def _payment_with_join(row: dict) -> dict:
    """Enriches a single payment dict with tenant name, apt_number, and location."""
    tid = row.get("tenant_id")
    if tid:   # only joins if this payment has a linked tenant
        joins = _db.executeQuery("""
            SELECT t.full_name, a.apt_number, a.location
            FROM tenants t LEFT JOIN apartments a ON t.apt_id=a.id
            WHERE t.id=?
        """, (tid,))   # fetches the tenant name and their apartment details in one JOIN
        if joins:
            row["full_name"] = joins[0]["full_name"]    # adds the tenant's name (e.g. 'Oliver Thompson') to the payment dict
            row["location"]  = joins[0]["location"]     # adds the city (e.g. 'Bristol') to the payment dict for filtering
            row["apt_number"]= joins[0]["apt_number"]   # adds the apartment code (e.g. 'APT-102') to the payment dict
    return row   # returns the enriched payment dict


def get_all_payments(location=None) -> list:
    rows = _db.executeQuery("""
        SELECT p.*, t.full_name, a.apt_number, a.location
        FROM payments p
        JOIN tenants t ON p.tenant_id = t.id
        LEFT JOIN apartments a ON t.apt_id = a.id
        ORDER BY p.due_date DESC
    """)   # fetches all payments with matching tenant names and apartment info, newest first
    if location and location != "All":   # if a city filter was provided
        rows = [r for r in rows if r.get("location") == location]   # keeps only payments from tenants in that city
    return [dict(r) for r in rows]   # converts each result row to a plain dict for the payments view table


def get_tenant_payments(tenant_id) -> list:
    rows = _db.executeQuery("""
        SELECT * FROM payments WHERE tenant_id=? ORDER BY due_date DESC
    """, (tenant_id,))   # fetches all payment records for one specific tenant, newest first
    return [dict(r) for r in rows]   # returns the list of that tenant's invoices and payment history


def generateInvoice(tenant_id, amount, due_date, payment_type="Rent", notes=""):
    """SD1: Generate invoice for a tenant payment."""
    return _db.executeUpdate("""
        INSERT INTO payments(tenant_id,amount,due_date,status,type,notes)
        VALUES(?,?,?,'Pending',?,?)
    """, (int(tenant_id), float(amount), due_date, payment_type, notes or ""))   # creates a new 'Pending' payment record; amount cast to float, tenant_id to int

add_payment = generateInvoice  # alias so views can call add_payment() instead of generateInvoice()


def markAsPaid(payment_id):
    """SD1: markAsPaid() — set status to Paid and record date."""
    return _db.executeUpdate("""
        UPDATE payments SET status='Paid', paid_date=date('now') WHERE id=?
    """, (payment_id,))   # sets the payment status to 'Paid' and records today as the paid_date

mark_payment_paid = markAsPaid  # alias so views can call mark_payment_paid() if preferred


def processPayment(payment_id: int) -> bool:
    """SD1: processPayment() — validate and mark invoice as paid."""
    rows = _db.executeQuery("SELECT * FROM payments WHERE id=?", (payment_id,))   # fetches the payment record to check if it exists and is not already paid
    if not rows or rows[0]["status"] == "Paid":   # aborts if the payment doesn't exist or was already paid (prevents double-processing)
        return False
    markAsPaid(payment_id)   # marks the payment as Paid with today's date
    return True   # signals to the caller that the payment was processed successfully


def generateReceipt(payment_id: int) -> dict:
    """SD1: generateReceipt() — return payment record as receipt dict."""
    rows = _db.executeQuery("""
        SELECT p.*, t.full_name, a.apt_number
        FROM payments p
        JOIN tenants t ON p.tenant_id=t.id
        LEFT JOIN apartments a ON t.apt_id=a.id
        WHERE p.id=?
    """, (payment_id,))   # fetches the payment with its tenant name and apartment code for the receipt display
    return dict(rows[0]) if rows else {}   # returns the receipt data as a dict, or empty dict if not found


def get_late_payments(location=None) -> list:
    rows = _db.executeQuery("""
        SELECT p.*, t.full_name, a.apt_number, a.location
        FROM payments p
        JOIN tenants t ON p.tenant_id=t.id
        LEFT JOIN apartments a ON t.apt_id=a.id
        WHERE p.status IN ('Pending','Overdue') AND p.due_date < date('now')
        ORDER BY p.due_date
    """)   # fetches all pending/overdue payments whose due date has already passed, sorted oldest first
    if location and location != "All":   # if a city filter was applied
        rows = [r for r in rows if r.get("location") == location]   # keeps only overdue payments from tenants in that city
    return [dict(r) for r in rows]   # returns the list of late payments for the dashboard warning panel


def mark_late_notifications_sent(payment_ids: list):
    for pid in payment_ids:   # iterates through each late payment ID
        _db.executeUpdate(
            "UPDATE payments SET status='Overdue', late_notified=1 WHERE id=?", (pid,))   # sets status to 'Overdue' and marks late_notified=1 so the notification email is not sent again


# ----------------------------------------------------------
# Maintenance  (Maintenance FR4, SD3 Resolve Maintenance Issue)
# ----------------------------------------------------------
def _maintenance_with_join(row: dict) -> dict:
    """Enriches a maintenance dict with tenant name, apartment details, and assigned staff name."""
    if row.get("tenant_id"):   # only joins tenant if a tenant ID is present
        tjoin = _db.executeQuery(
            "SELECT full_name FROM tenants WHERE id=?", (row["tenant_id"],))   # looks up the tenant's full name
        row["full_name"] = tjoin[0]["full_name"] if tjoin else None   # adds the tenant's name to the maintenance dict
    if row.get("apt_id"):   # only joins apartment if an apartment ID is present
        ajoin = _db.executeQuery(
            "SELECT apt_number, location FROM apartments WHERE id=?", (row["apt_id"],))   # looks up the apartment code and city
        if ajoin:
            row["apt_number"] = ajoin[0]["apt_number"]   # adds the apartment code (e.g. 'APT-201')
            row["location"]   = ajoin[0]["location"]     # adds the city name
    if row.get("assigned_to"):   # only joins staff if a user is assigned to this request
        ujoin = _db.executeQuery(
            "SELECT full_name FROM users WHERE id=?", (row["assigned_to"],))   # looks up the maintenance worker's name
        row["staff_name"] = ujoin[0]["full_name"] if ujoin else None   # adds the assigned staff member's name (e.g. 'Carlos Rivera')
    return row   # returns the fully enriched maintenance dict


def get_all_maintenance(location=None) -> list:
    rows = _db.executeQuery("""
        SELECT m.*, t.full_name, a.apt_number, a.location,
               u.full_name AS staff_name
        FROM maintenance m
        LEFT JOIN tenants t ON m.tenant_id = t.id
        LEFT JOIN apartments a ON m.apt_id = a.id
        LEFT JOIN users u ON m.assigned_to = u.id
        ORDER BY m.reported_date DESC
    """)   # fetches all maintenance requests with tenant, apartment, and staff names in one JOIN, sorted newest first
    if location and location != "All":   # if a city filter was provided
        rows = [r for r in rows if r.get("location") == location]   # keeps only maintenance requests for apartments in that city
    return [dict(r) for r in rows]   # converts to plain dicts for the maintenance view table


def add_maintenance(tenant_id, apt_id, title, description,
                    priority="Medium", assigned_to=None, scheduled_date=None):
    return _db.executeUpdate("""
        INSERT INTO maintenance(tenant_id,apt_id,title,description,priority,
            assigned_to,scheduled_date,reported_date)
        VALUES(?,?,?,?,?,?,?,date('now'))
    """, (
        int(tenant_id) if tenant_id else None,   # casts to int if provided, None if no tenant linked
        int(apt_id) if apt_id else None,          # casts to int if provided, None if no apartment linked
        title, description or "", priority,
        int(assigned_to) if assigned_to else None,   # casts to int the ID of the assigned maintenance worker, or None if unassigned
        scheduled_date   # scheduled date string or None
    ))   # inserts the new maintenance request with today's date as the reported_date


def resolveIssue(mid, cost, time_spent, notes=""):
    """SD3: resolveIssue() — record resolution, cost, and time taken."""
    return _db.executeUpdate("""
        UPDATE maintenance
        SET status='Resolved', resolved_date=date('now'),
            cost=?, time_spent=?, notes=?
        WHERE id=?
    """, (float(cost), float(time_spent), notes or "", mid))   # marks the issue as Resolved, records today as the resolved date, and saves the repair cost, hours worked, and any notes

resolve_maintenance = resolveIssue  # alias so views can call resolve_maintenance() instead of resolveIssue()


def update_maintenance_status(mid, status):
    return _db.executeUpdate(
        "UPDATE maintenance SET status=? WHERE id=?", (status, mid))   # updates just the status field (e.g. from 'Open' to 'Assigned' or 'In Progress')


def update_maintenance_schedule(mid, scheduled_date, notes=""):
    return _db.executeUpdate("""
        UPDATE maintenance SET scheduled_date=?, communication_sent=1, notes=?
        WHERE id=?
    """, (scheduled_date, notes or "", mid))   # sets the scheduled start date, marks communication_sent=1 (notification sent to tenant), and saves notes


def get_maintenance_staff(location=None) -> list:
    if location and location != "All":   # if a city filter was provided
        rows = _db.executeQuery("""
            SELECT id, full_name FROM users
            WHERE role='Maintenance Staff' AND active=1 AND location=?
            ORDER BY full_name
        """, (location,))   # returns only active maintenance workers in the specified city
    else:
        rows = _db.executeQuery("""
            SELECT id, full_name FROM users
            WHERE role='Maintenance Staff' AND active=1
            ORDER BY full_name
        """)   # returns all active maintenance workers across all cities
    return [(r["id"], r["full_name"]) for r in rows]   # returns a list of (id, name) tuples for the "Assign To" dropdown in the maintenance form


# ----------------------------------------------------------
# Complaints
# ----------------------------------------------------------
def _complaint_with_join(row: dict) -> dict:
    """Enriches a single complaint dict with tenant name, apt_number, and city."""
    if row.get("tenant_id"):   # only performs the JOIN if a tenant is linked to this complaint
        joins = _db.executeQuery("""
            SELECT t.full_name, a.apt_number, a.location
            FROM tenants t LEFT JOIN apartments a ON t.apt_id=a.id
            WHERE t.id=?
        """, (row["tenant_id"],))   # fetches the tenant's name and their apartment details in one JOIN query
        if joins:
            row["full_name"] = joins[0]["full_name"]    # adds the tenant's name (e.g. 'Oliver Thompson') to the complaint dict
            row["location"]  = joins[0]["location"]     # adds the city name to the complaint dict
            row["apt_number"]= joins[0]["apt_number"]   # adds the apartment code (e.g. 'APT-102') to the complaint dict
    return row   # returns the enriched complaint dict with all display fields populated


def get_all_complaints(location=None) -> list:
    rows = _db.executeQuery("""
        SELECT c.*, t.full_name, a.apt_number, a.location
        FROM complaints c
        LEFT JOIN tenants t ON c.tenant_id = t.id
        LEFT JOIN apartments a ON t.apt_id = a.id
        ORDER BY c.created_at DESC
    """)   # fetches all complaints with the reporting tenant's name and their apartment, sorted newest first
    if location and location != "All":   # if a city filter was provided
        rows = [r for r in rows if r.get("location") == location]   # keeps only complaints from tenants in that city
    return [dict(r) for r in rows]   # converts each result row to a plain dict for the complaints view table


def add_complaint(tenant_id, title, description):
    return _db.executeUpdate("""
        INSERT INTO complaints(tenant_id,title,description,created_at)
        VALUES(?,?,?,date('now'))
    """, (int(tenant_id), title, description or ""))   # inserts a new Open complaint with today's date; description defaults to empty string


def updateStatus(cid, status):
    """Update complaint status; set resolved_at if resolving."""
    resolved_at = _today() if status == "Resolved" else None   # if the new status is 'Resolved', records today's date as the resolution date; otherwise leaves it NULL
    return _db.executeUpdate("""
        UPDATE complaints SET status=?, resolved_at=? WHERE id=?
    """, (status, resolved_at, cid))   # updates the complaint's status and resolved date in the database

update_complaint_status = updateStatus  # alias so views can call update_complaint_status() instead of updateStatus()


# ----------------------------------------------------------
# Early Lease Termination  (FR5, SD4)
# ----------------------------------------------------------
def calculatePenalty(monthly_rent: float) -> float:
    """SD4: calculateLatePenalty() — 5% of monthly rent as per business rules."""
    return round(float(monthly_rent or 0) * 0.05, 2)   # calculates 5% of the monthly rent as the early termination penalty, rounded to 2 decimal places (e.g. £1050 rent → £52.50 penalty)


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
    rows = _db.executeQuery("SELECT * FROM tenants WHERE id=?", (tid,))   # loads the tenant's record to check their status and get their rent amount
    if not rows:   # if no tenant with this ID was found
        return None, "Tenant not found."   # returns an error message that the UI can display
    tenant = rows[0]   # gets the tenant's data dict
    if tenant["status"] != "Active":   # only active tenants can submit early termination
        return None, "Tenant is not currently active."   # returns an error if the tenant is already Leaving, Inactive, or Archived

    monthly_rent = float(tenant["monthly_rent"] or 0)   # gets the monthly rent amount from the tenant record, defaulting to 0 if NULL
    penalty      = calculatePenalty(monthly_rent)   # calculates the 5% early termination penalty fee
    notice_date  = _today()       # records today as the date the notice was officially submitted
    leave_date   = _days_from_today(30)   # the tenant must leave in 30 days (1 month notice period) from today

    # Update tenant status
    _db.executeUpdate("""
        UPDATE tenants SET status='Leaving', early_leave_notice_date=?,
            lease_end=?, notes=?
        WHERE id=?
    """, (notice_date, leave_date,
          f"Early leave requested {notice_date}. Leave: {leave_date}. "
          f"Penalty: £{penalty:.2f} (5% of £{monthly_rent:.2f})",
          tid))   # changes the tenant's status to 'Leaving', records the notice date, updates their lease end to 30 days from now, and adds descriptive notes

    # updateOccupancyStatus apartment → Vacant (SD4)
    if tenant["apt_id"]:   # if the tenant has an apartment assigned
        _db.executeUpdate(
            "UPDATE apartments SET status='Vacant' WHERE id=?", (tenant["apt_id"],))   # marks the apartment as Vacant immediately upon early termination notice

    # Mark lease as Terminated (SD4)
    _db.executeUpdate("""
        UPDATE leases SET status='Terminated', early_termination_date=?, penalty_amount=?
        WHERE tenant_id=? AND status='Active'
    """, (notice_date, penalty, tid))   # updates the formal lease record to reflect the early termination with the notice date and penalty amount

    # generateInvoice for penalty (SD4)
    generateInvoice(
        tenant_id=tid,
        amount=penalty,
        due_date=notice_date,
        payment_type="Early Leave Penalty",
        notes=f"5% early termination penalty on £{monthly_rent:.2f}/month rent",
    )   # creates a new Pending payment invoice for the early termination penalty fee so it appears in the payments view

    return penalty, leave_date   # returns the calculated penalty amount and the tenant's official leave date to the caller

process_early_leave = terminateEarly  # alias so the UI can call process_early_leave() instead of terminateEarly()


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
    """)   # counts total apartments and occupied apartments grouped by city, sorted alphabetically
    return [dict(r) for r in rows]   # returns a list of dicts like {location: 'Bristol', total: 7, occupied: 5}

occupancy_by_location = getOccupancyByCity  # alias used by older report code


def compareCollectedVsPending(location=None) -> dict:
    """SD5: compareCollectedVsPending() — financial summary."""
    if location and location != "All":   # if a city filter was applied
        rows = _db.executeQuery("""
            SELECT p.status, p.amount
            FROM payments p
            JOIN tenants t ON p.tenant_id=t.id
            LEFT JOIN apartments a ON t.apt_id=a.id
            WHERE a.location=?
        """, (location,))   # fetches payment statuses and amounts only for tenants in the specified city
    else:
        rows = _db.executeQuery("SELECT status, amount FROM payments")   # fetches payment statuses and amounts for all cities

    collected = sum(float(r["amount"]) for r in rows if r["status"] == "Paid")      # sums the amount of all paid invoices in pounds
    pending   = sum(float(r["amount"]) for r in rows if r["status"] != "Paid")      # sums the amount of all unpaid (Pending/Overdue) invoices in pounds
    return {"collected": round(collected, 2), "pending": round(pending, 2)}   # returns a dict showing how much rent has been collected vs how much is still outstanding

financial_summary = compareCollectedVsPending  # alias used by some older report code


def trackCostsByLocation(location=None) -> list:
    """SD5: trackCostsByLocation() — maintenance cost report."""
    if location and location != "All":   # if a city was specified
        rows = _db.executeQuery("""
            SELECT m.status, m.cost
            FROM maintenance m
            LEFT JOIN apartments a ON m.apt_id=a.id
            WHERE a.location=?
        """, (location,))   # fetches maintenance status and cost for apartments in the specified city only
    else:
        rows = _db.executeQuery("SELECT status, cost FROM maintenance")   # fetches all maintenance status and cost records across all cities

    by_status: dict = {}   # dictionary to accumulate total costs grouped by maintenance status
    for r in rows:   # loops through each maintenance record
        st = r["status"] or "Unknown"   # uses 'Unknown' if status is NULL (shouldn't happen but guards against it)
        if st not in by_status:   # creates a new entry for this status if it hasn't been seen yet
            by_status[st] = {"status": st, "total_cost": 0.0, "count": 0}   # initialises totals for this status group
        by_status[st]["total_cost"] += float(r["cost"] or 0)   # adds this record's cost to the running total for this status
        by_status[st]["count"] += 1   # increments the count of records in this status group

    out = []   # list that will hold the final sorted output
    for st in sorted(by_status):   # iterates through statuses alphabetically
        e = by_status[st]
        e["total_cost"] = round(e["total_cost"], 2)   # rounds the total cost to 2 decimal places for display
        out.append(e)   # adds this status group's summary dict to the output list
    return out   # returns a list of dicts like [{status: 'Resolved', total_cost: 365.0, count: 3}, ...]

maintenance_cost_summary = trackCostsByLocation  # alias used by older code


def generateReport(location=None, start_date=None, end_date=None) -> dict:
    """SD5: generateReport() — composite full report."""
    return {
        "occupancy":   getOccupancyByCity(),       # list of per-city occupancy stats (total vs occupied apartments)
        "financial":   compareCollectedVsPending(location),   # dict showing collected vs pending rent for the requested location
        "maintenance": trackCostsByLocation(location),        # list of maintenance cost breakdowns by status
        "period":      {"start": start_date, "end": end_date},   # the date range this report covers (passed in; None means all-time)
    }


def getPerformanceByLocation() -> list:
    """SD5: getPerformanceByLocation() — performance metrics per city."""
    occupancy = getOccupancyByCity()   # gets the occupancy breakdown for all cities
    results = []   # list to accumulate per-city performance summaries
    for o in occupancy:   # loops through each city's occupancy data
        loc = o["location"]   # the current city name (e.g. 'Bristol')
        fin = compareCollectedVsPending(loc)   # gets collected vs pending rent figures for this city
        maint = trackCostsByLocation(loc)      # gets maintenance cost breakdown for this city
        total_maint_cost = sum(m["total_cost"] for m in maint)   # sums all maintenance costs across all statuses for this city
        rate = (o["occupied"] / o["total"] * 100) if o["total"] else 0   # calculates the occupancy rate as a percentage (e.g. 5/7 = 71.4%)
        results.append({
            "location":       loc,                           # city name
            "total_apts":     o["total"],                    # total number of apartments in this city
            "occupied":       o["occupied"],                 # number of currently occupied apartments
            "occupancy_rate": round(rate, 1),                # occupancy percentage (e.g. 71.4) shown on the performance chart
            "rent_collected": fin["collected"],              # total rent collected (paid) in this city in pounds
            "rent_pending":   fin["pending"],                # total rent still outstanding (Pending/Overdue) in this city
            "maint_cost":     round(total_maint_cost, 2),   # total maintenance spend in this city in pounds
        })
    return results   # returns a list of per-city performance dicts for the reports view


# ----------------------------------------------------------
# Dashboard Statistics
# ----------------------------------------------------------
def dashboard_stats(user: dict) -> dict:
    loc = user.get("location")   # gets the logged-in staff member's assigned city
    if user.get("role") == "Manager":
        loc = None  # Manager sees all locations — overrides their city to None so all-location queries are used

    apartments  = get_all_apartments(loc)    # fetches all apartments visible to this user (city-filtered or all)
    tenants     = get_all_tenants(loc)       # fetches all tenants visible to this user
    maintenance = get_all_maintenance(loc)   # fetches all maintenance requests visible to this user
    payments    = get_all_payments(loc)      # fetches all payment records visible to this user

    return {
        "total_apts":     len(apartments),   # total number of apartments this user can see (shown on the 'Total Apartments' KPI tile)
        "occupied_apts":  sum(1 for a in apartments if a.get("status") == "Occupied"),   # count of apartments currently occupied (shown on the 'Occupied' KPI tile)
        "total_tenants":  len(tenants),      # total number of tenants this user can see (shown on the 'Tenants' KPI tile)
        "active_maint":   sum(1 for m in maintenance if m.get("status") != "Resolved"),   # count of open/in-progress maintenance requests (shown on the 'Maintenance' warning KPI tile)
        "pending_rent":   round(sum(float(p.get("amount") or 0) for p in payments
                                   if p.get("status") in ("Overdue", "Pending")), 2),   # total outstanding rent owed in pounds (shown as the red 'Pending' figure on the finance KPI tile)
        "collected_rent": round(sum(float(p.get("amount") or 0) for p in payments
                                   if p.get("status") == "Paid"), 2),   # total rent already collected in pounds (shown as the green 'Collected' figure on the finance KPI tile)
    }


# ----------------------------------------------------------
# Expiring Leases  (Admin tracking FR)
# ----------------------------------------------------------
def get_expiring_leases(days=30, location=None) -> list:
    future = _days_from_today(int(days))   # calculates the end of the warning window (default: 30 days from today)
    today  = _today()   # today's date as the start of the warning window
    rows = _db.executeQuery("""
        SELECT t.*, a.apt_number, a.location
        FROM tenants t
        LEFT JOIN apartments a ON t.apt_id=a.id
        WHERE t.status IN ('Active', 'Leaving') AND t.lease_end BETWEEN ? AND ?
        ORDER BY t.lease_end
    """, (today, future))   # includes Leaving tenants too — early-leave tenants are the most urgent to show in lease tracking
    if location and location != "All":   # if a city filter was provided
        rows = [r for r in rows if r.get("location") == location]   # keeps only tenants in that city
    return [dict(r) for r in rows]   # returns the list of expiring leases for the admin dashboard warning panel


# ----------------------------------------------------------
# Audit Log  (Security NFR1)
# ----------------------------------------------------------
def log_audit(user_id, action, entity_type=None, entity_id=None,
              old_value=None, new_value=None):
    _db.executeUpdate("""
        INSERT INTO audit_log(user_id,action,entity_type,entity_id,old_value,new_value)
        VALUES(?,?,?,?,?,?)
    """, (user_id, action, entity_type, entity_id, old_value, new_value))   # writes a new audit log entry recording what was changed, by whom, and what the old and new values were


def get_audit_log(limit=200) -> list:
    rows = _db.executeQuery("""
        SELECT al.*, u.full_name FROM audit_log al
        LEFT JOIN users u ON al.user_id=u.id
        ORDER BY al.timestamp DESC LIMIT ?
    """, (limit,))   # fetches the most recent audit log entries (default: 200) with the staff member's name joined from the users table, newest first
    return [dict(r) for r in rows]   # converts each log entry to a plain dict for display in the audit log view
