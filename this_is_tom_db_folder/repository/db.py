import sqlite3
import hashlib


DB_NAME = "pams.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")  # IMPORTANT
    return conn


# -------------------------
# PASSWORD HASHING
# -------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# -------------------------
# CREATE TABLES
# -------------------------
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # -------------------------
    # LOCATIONS TABLE
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL UNIQUE
    );
    """)

    # -------------------------
    # USERS TABLE
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN 
            ('front_desk', 'finance_manager', 'maintenance_staff', 'admin', 'manager')
        ),
        location_id INTEGER,
        FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL
    );
    """)

    # -------------------------
    # APARTMENTS TABLE
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS apartments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        rooms INTEGER NOT NULL,
        monthly_rent REAL NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('available', 'occupied', 'maintenance')),
        FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
    );
    """)

    # -------------------------
    # TENANTS TABLE
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ni_number TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        occupation TEXT,
        apartment_id INTEGER,
        lease_start DATE,
        lease_end DATE,
        monthly_rent REAL,
        FOREIGN KEY (apartment_id) REFERENCES apartments(id) ON DELETE SET NULL
    );
    """)

    # -------------------------
    # LEASES TABLE
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        apartment_id INTEGER NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        monthly_rent REAL NOT NULL,
        early_termination_fee REAL DEFAULT 0,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (apartment_id) REFERENCES apartments(id) ON DELETE CASCADE
    );
    """)

    # -------------------------
    # PAYMENTS TABLE
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        lease_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        due_date DATE NOT NULL,
        paid_date DATE,
        status TEXT NOT NULL CHECK(status IN ('pending', 'paid', 'late')),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (lease_id) REFERENCES leases(id) ON DELETE CASCADE
    );
    """)

    # -------------------------
    # MAINTENANCE REQUESTS TABLE
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        apartment_id INTEGER NOT NULL,
        tenant_id INTEGER,
        description TEXT NOT NULL,
        priority TEXT CHECK(priority IN ('low', 'medium', 'high')),
        status TEXT CHECK(status IN ('open', 'in_progress', 'resolved')),
        reported_date DATE,
        resolved_date DATE,
        cost REAL DEFAULT 0,
        time_taken TEXT,
        FOREIGN KEY (apartment_id) REFERENCES apartments(id) ON DELETE CASCADE,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL
    );
    """)

    conn.commit()
    conn.close()


# -------------------------
# SEED DEFAULT DATA
# -------------------------
def seed_locations():
    conn = get_connection()
    cursor = conn.cursor()

    locations = ["Bristol", "Cardiff", "London", "Manchester"]

    for city in locations:
        cursor.execute("""
        INSERT OR IGNORE INTO locations (city)
        VALUES (?)
        """, (city,))

    conn.commit()
    conn.close()


def seed_admin_user():
    conn = get_connection()
    cursor = conn.cursor()

    # Get Bristol location ID
    cursor.execute("SELECT id FROM locations WHERE city = ?", ("Bristol",))
    location = cursor.fetchone()

    if location:
        location_id = location[0]

        cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, role, location_id)
        VALUES (?, ?, ?, ?)
        """, (
            "admin",
            hash_password("admin123"),
            "admin",
            location_id
        ))

    conn.commit()
    conn.close()


# -------------------------
# INITIALIZE DATABASE
# -------------------------
if __name__ == "__main__":
    create_tables()
    seed_locations()
    seed_admin_user()
    print("Database initialized successfully.")
