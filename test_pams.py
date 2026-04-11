# =============================================================
# test_pams.py
# Automated Test Suite — Paragon Apartment Management System
#
# Tests: 16-20 (Automated validation tests as per test plan)
# Framework: Python unittest (built-in, no extra packages needed)
#
# Run with:   python -m pytest test_pams.py -v
#        OR:  python test_pams.py
# =============================================================

import os
import sys
import tempfile
import threading
import unittest

# --------------- Path setup ---------------
# Ensures imports work whether you run from the project root or an IDE
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


# ==============================================================
# Helper: spin up an isolated in-memory test database
# We patch pams.database._DB_PATH BEFORE the module creates any
# real connections so no test data ever touches pams.db.
# ==============================================================
def _bootstrap_test_db():
    """
    Creates a temporary SQLite file, patches database._DB_PATH to
    point at it, and initialises the schema (tables only, no seed data).
    Returns the path of the temp file for teardown.
    """
    import pams.database as db_mod

    # 1. Create a fresh temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    tmp_path = tmp.name

    # 2. Redirect the module to the temp file
    db_mod._DB_PATH = tmp_path

    # 3. Drop the live connection so the next call reconnects to tmp_path
    db_mod._local.conn = None

    # 4. Build the schema (tables/indexes only — skip seed data)
    db_mod._create_schema()

    return tmp_path


# ==============================================================
# Test class
# ==============================================================
class TestAutomatedValidation(unittest.TestCase):
    """
    Automated validation tests — TC16 through TC20.
    Each test targets pams/database.py functions directly,
    bypassing the GUI entirely.
    """

    # ---- one-time setup: build isolated test database ----
    @classmethod
    def setUpClass(cls):
        cls._tmp_path = _bootstrap_test_db()
        import pams.database as db_mod
        cls.db = db_mod

        # Locations table must have an entry before apartments can be inserted
        cls.db.add_location("Bristol")

        # Pre-insert one apartment so TC16 can assign a tenant to it
        cls.db.add_apartment(
            apt_number="UNIT-TEST-01",
            location="Bristol",
            apt_type="1-Bed",
            rooms=1,
            monthly_rent=800.0,
        )
        apts = cls.db.get_vacant_apartments()
        # Find our test apartment
        cls.test_apt_id = next(
            (a[0] for a in apts if "UNIT-TEST-01" in a[1]), None
        )

    # ---- one-time teardown: delete temp database ----
    @classmethod
    def tearDownClass(cls):
        try:
            conn = cls.db._db.get_connection()
            conn.close()
            cls.db._local.conn = None
        except Exception:
            pass
        try:
            os.unlink(cls._tmp_path)
        except Exception:
            pass

    # ---- per-test teardown: wipe tenants so NI duplicates can't occur ----
    def tearDown(self):
        conn = self.db._db.get_connection()
        conn.execute("DELETE FROM leases")
        conn.execute("DELETE FROM tenants")
        conn.commit()

    # ----------------------------------------------------------
    # TC16 — Valid tenant data is accepted and saved
    # ----------------------------------------------------------
    def test_16_valid_tenant_data_saves_correctly(self):
        """
        TC16 | Automated | Validate tenant data
        Input : fully valid tenant fields
        Expected: function returns an integer tenant ID and record exists in DB
        """
        tenant_id = self.db.add_tenant(
            ni="AB123456C",
            name="Alice Brown",
            phone="07700900001",
            email="alice@example.com",
            occupation="Nurse",
            reference="City Hospital",
            apartment_requirements="1-Bed",
            apt_id=self.test_apt_id,
            lease_start="2025-06-01",
            lease_end="2026-06-01",
            deposit=800.0,
            monthly_rent=800.0,
        )

        # Should return a valid integer primary key
        self.assertIsNotNone(tenant_id, "add_tenant() returned None for valid data")
        self.assertIsInstance(tenant_id, int, "add_tenant() should return an int tenant ID")
        self.assertGreater(tenant_id, 0, "Tenant ID should be a positive integer")

        # Confirm the record actually exists in the database
        saved = self.db.get_tenant_by_id(tenant_id)
        self.assertIsNotNone(saved, "Tenant was not found in the database after insert")
        self.assertEqual(saved["ni_number"], "AB123456C")
        self.assertEqual(saved["full_name"], "Alice Brown")

    # ----------------------------------------------------------
    # TC17 — Empty NI number is rejected
    # ----------------------------------------------------------
    def test_17_reject_missing_ni_number(self):
        """
        TC17 | Automated | Reject missing NI number
        Input : ni_number = "" (empty string)
        Expected: function raises ValueError or returns False
        """
        # Option A — the database function raises ValueError
        # Option B — it returns False / None without inserting
        # We test for EITHER behaviour; the important thing is that
        # an empty NI is never silently stored.
        try:
            result = self.db.add_tenant(
                ni="",           # ← deliberately empty
                name="Bob Smith",
                phone="07700900002",
                email="bob@example.com",
                occupation="Driver",
                reference="Transport Co",
                apartment_requirements="Studio",
                apt_id=self.test_apt_id,
                lease_start="2025-06-01",
                lease_end="2026-06-01",
                deposit=500.0,
                monthly_rent=600.0,
            )
            # If no exception was raised, result must be False/None (not a valid ID)
            self.assertFalse(
                result,
                "add_tenant() with empty NI should raise ValueError or return "
                "False/None, but returned a truthy value.",
            )
        except ValueError:
            pass  # correct behaviour — test passes

    # ----------------------------------------------------------
    # TC18 — Negative rent is rejected
    # ----------------------------------------------------------
    def test_18_reject_negative_rent(self):
        """
        TC18 | Automated | Reject negative rent
        Input : monthly_rent = -500
        Expected: function raises ValueError or returns False
        """
        try:
            result = self.db.add_tenant(
                ni="CD234567D",
                name="Carol Davis",
                phone="07700900003",
                email="carol@example.com",
                occupation="Teacher",
                reference="Academy School",
                apartment_requirements="2-Bed",
                apt_id=self.test_apt_id,
                lease_start="2025-06-01",
                lease_end="2026-06-01",
                deposit=1000.0,
                monthly_rent=-500,  # ← deliberately negative
            )
            self.assertFalse(
                result,
                "add_tenant() with negative rent should raise ValueError or return "
                "False/None, but returned a truthy value.",
            )
        except ValueError:
            pass  # correct behaviour — test passes

    # ----------------------------------------------------------
    # TC19 — Non-numeric payment amount is rejected
    # ----------------------------------------------------------
    def test_19_reject_invalid_payment_amount(self):
        """
        TC19 | Automated | Reject invalid payment amount
        Input : amount = "abc"
        Expected: function raises ValueError (float("abc") fails)
        """
        # generateInvoice calls float(amount), so "abc" triggers ValueError
        # before any database write occurs.
        with self.assertRaises((ValueError, TypeError)):
            self.db.generateInvoice(
                tenant_id=1,
                amount="abc",  # ← invalid non-numeric string
                due_date="2025-07-01",
            )

    # ----------------------------------------------------------
    # TC20 — Lease end date before start date is rejected
    # ----------------------------------------------------------
    def test_20_reject_lease_end_before_start(self):
        """
        TC20 | Automated | Reject invalid lease dates
        Input : lease_end = "2024-01-01", lease_start = "2026-01-01"
                (end is earlier than start — logically impossible)
        Expected: function raises ValueError or returns False
        """
        try:
            result = self.db.add_tenant(
                ni="EF345678E",
                name="Eve Foster",
                phone="07700900004",
                email="eve@example.com",
                occupation="Chef",
                reference="Grand Restaurant",
                apartment_requirements="1-Bed",
                apt_id=self.test_apt_id,
                lease_start="2026-01-01",
                lease_end="2024-01-01",  # ← end is BEFORE start
                deposit=600.0,
                monthly_rent=750.0,
            )
            self.assertFalse(
                result,
                "add_tenant() with end date before start date should raise "
                "ValueError or return False/None, but returned a truthy value.",
            )
        except ValueError:
            pass  # correct behaviour — test passes


# ==============================================================
# Run directly
# ==============================================================
if __name__ == "__main__":
    unittest.main(verbosity=2)
