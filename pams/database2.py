# ============================================================
# PAMS - database.py
# In-memory static data layer (no SQLite)
# ============================================================
from __future__ import annotations

import copy
import datetime
import hashlib
from typing import Optional


# Application-level salt kept for compatibility with existing credentials.
_SALT = b"PAMS_Paragon_Secure_2025"


def _hash(pw: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), _SALT, 100_000).hex()


def _today() -> str:
    return datetime.date.today().isoformat()


def _days_from_today(days: int) -> str:
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()


def _seed_state() -> dict:
    users = [
        {
            "id": 1,
            "username": "admin_bristol",
            "password": _hash("admin123"),
            "full_name": "Alice Morrison",
            "role": "Administrator",
            "location": "Bristol",
            "email": "",
            "active": 1,
            "created_at": _today(),
        },
        {
            "id": 2,
            "username": "admin_london",
            "password": _hash("admin123"),
            "full_name": "David Okafor",
            "role": "Administrator",
            "location": "London",
            "email": "",
            "active": 1,
            "created_at": _today(),
        },
        {
            "id": 3,
            "username": "manager",
            "password": _hash("manager123"),
            "full_name": "Sarah Whitfield",
            "role": "Manager",
            "location": "Bristol",
            "email": "",
            "active": 1,
            "created_at": _today(),
        },
        {
            "id": 4,
            "username": "frontdesk1",
            "password": _hash("front123"),
            "full_name": "James Patel",
            "role": "Front-Desk Staff",
            "location": "Bristol",
            "email": "",
            "active": 1,
            "created_at": _today(),
        },
        {
            "id": 5,
            "username": "frontdesk2",
            "password": _hash("front123"),
            "full_name": "Lily Chen",
            "role": "Front-Desk Staff",
            "location": "Manchester",
            "email": "",
            "active": 1,
            "created_at": _today(),
        },
        {
            "id": 6,
            "username": "finance1",
            "password": _hash("finance123"),
            "full_name": "Robert Hughes",
            "role": "Finance Manager",
            "location": "Bristol",
            "email": "",
            "active": 1,
            "created_at": _today(),
        },
        {
            "id": 7,
            "username": "maint1",
            "password": _hash("maint123"),
            "full_name": "Carlos Rivera",
            "role": "Maintenance Staff",
            "location": "Bristol",
            "email": "",
            "active": 1,
            "created_at": _today(),
        },
        {
            "id": 8,
            "username": "maint2",
            "password": _hash("maint123"),
            "full_name": "Priya Singh",
            "role": "Maintenance Staff",
            "location": "London",
            "email": "",
            "active": 1,
            "created_at": _today(),
        },
    ]

    apartments = [
        {"id": 1, "apt_number": "APT-101", "location": "Bristol", "type": "Studio", "rooms": 1, "monthly_rent": 850.0, "status": "Occupied", "floor": 1, "description": "Modern studio"},
        {"id": 2, "apt_number": "APT-102", "location": "Bristol", "type": "1-Bedroom", "rooms": 1, "monthly_rent": 1050.0, "status": "Occupied", "floor": 1, "description": "Balcony"},
        {"id": 3, "apt_number": "APT-103", "location": "Bristol", "type": "2-Bedroom", "rooms": 2, "monthly_rent": 1400.0, "status": "Vacant", "floor": 1, "description": "Spacious"},
        {"id": 4, "apt_number": "APT-201", "location": "Bristol", "type": "2-Bedroom", "rooms": 2, "monthly_rent": 1350.0, "status": "Occupied", "floor": 2, "description": "South facing"},
        {"id": 5, "apt_number": "APT-202", "location": "Bristol", "type": "3-Bedroom", "rooms": 3, "monthly_rent": 1800.0, "status": "Occupied", "floor": 2, "description": "Family unit"},
        {"id": 6, "apt_number": "APT-301", "location": "Bristol", "type": "Penthouse", "rooms": 4, "monthly_rent": 3200.0, "status": "Vacant", "floor": 3, "description": "Luxury"},
        {"id": 7, "apt_number": "APT-L01", "location": "London", "type": "Studio", "rooms": 1, "monthly_rent": 1400.0, "status": "Occupied", "floor": 1, "description": "Bridge view"},
        {"id": 8, "apt_number": "APT-L02", "location": "London", "type": "1-Bedroom", "rooms": 1, "monthly_rent": 1750.0, "status": "Occupied", "floor": 1, "description": "Prime area"},
        {"id": 9, "apt_number": "APT-L03", "location": "London", "type": "2-Bedroom", "rooms": 2, "monthly_rent": 2400.0, "status": "Vacant", "floor": 2, "description": "Transport links"},
        {"id": 10, "apt_number": "APT-M01", "location": "Manchester", "type": "2-Bedroom", "rooms": 2, "monthly_rent": 1100.0, "status": "Occupied", "floor": 1, "description": "City centre"},
        {"id": 11, "apt_number": "APT-M02", "location": "Manchester", "type": "1-Bedroom", "rooms": 1, "monthly_rent": 900.0, "status": "Vacant", "floor": 1, "description": "Northern Quarter"},
        {"id": 12, "apt_number": "APT-C01", "location": "Cardiff", "type": "1-Bedroom", "rooms": 1, "monthly_rent": 850.0, "status": "Occupied", "floor": 1, "description": "Bay area"},
        {"id": 13, "apt_number": "APT-C02", "location": "Cardiff", "type": "2-Bedroom", "rooms": 2, "monthly_rent": 1100.0, "status": "Vacant", "floor": 1, "description": "Quiet area"},
    ]

    def _lease_range(back_months: int, fwd_months: int) -> tuple[str, str]:
        s = datetime.date.today() - datetime.timedelta(days=30 * back_months)
        e = datetime.date.today() + datetime.timedelta(days=30 * fwd_months)
        return s.isoformat(), e.isoformat()

    lease = [_lease_range(6, 12), _lease_range(3, 9), _lease_range(1, 11), _lease_range(4, 8),
             _lease_range(2, 10), _lease_range(5, 7), _lease_range(6, 6), _lease_range(3, 9)]

    tenants = [
        {"id": 1, "ni_number": "NI-AA123456A", "full_name": "Oliver Thompson", "phone": "07700111001", "email": "oliver@email.com", "occupation": "Software Engineer", "reference": "John Smith", "apartment_requirements": "1-Bedroom", "apt_id": 1, "lease_start": lease[0][0], "lease_end": lease[0][1], "deposit": 1050.0, "monthly_rent": 1050.0, "status": "Active", "notes": "", "early_leave_notice_date": None, "created_at": _today()},
        {"id": 2, "ni_number": "NI-BB234567B", "full_name": "Emma Williams", "phone": "07700111002", "email": "emma@email.com", "occupation": "Nurse", "reference": "Dr. Jones", "apartment_requirements": "1-Bedroom", "apt_id": 2, "lease_start": lease[1][0], "lease_end": lease[1][1], "deposit": 1050.0, "monthly_rent": 1050.0, "status": "Active", "notes": "", "early_leave_notice_date": None, "created_at": _today()},
        {"id": 3, "ni_number": "NI-CC345678C", "full_name": "Noah Brown", "phone": "07700111003", "email": "noah@email.com", "occupation": "Teacher", "reference": "Mary Green", "apartment_requirements": "2-Bedroom", "apt_id": 4, "lease_start": lease[2][0], "lease_end": lease[2][1], "deposit": 1350.0, "monthly_rent": 1350.0, "status": "Active", "notes": "", "early_leave_notice_date": None, "created_at": _today()},
        {"id": 4, "ni_number": "NI-DD456789D", "full_name": "Sophia Davis", "phone": "07700111004", "email": "sophia@email.com", "occupation": "Accountant", "reference": "Peter Davis", "apartment_requirements": "3-Bedroom", "apt_id": 5, "lease_start": lease[3][0], "lease_end": lease[3][1], "deposit": 1800.0, "monthly_rent": 1800.0, "status": "Active", "notes": "", "early_leave_notice_date": None, "created_at": _today()},
        {"id": 5, "ni_number": "NI-EE567890E", "full_name": "Liam Wilson", "phone": "07700111005", "email": "liam@email.com", "occupation": "Architect", "reference": "Jane Wilson", "apartment_requirements": "Studio", "apt_id": 7, "lease_start": lease[4][0], "lease_end": lease[4][1], "deposit": 1750.0, "monthly_rent": 1750.0, "status": "Active", "notes": "", "early_leave_notice_date": None, "created_at": _today()},
        {"id": 6, "ni_number": "NI-FF678901F", "full_name": "Isabella Moore", "phone": "07700111006", "email": "isab@email.com", "occupation": "Marketing Mgr", "reference": "Tom Moore", "apartment_requirements": "1-Bedroom", "apt_id": 8, "lease_start": lease[5][0], "lease_end": lease[5][1], "deposit": 1750.0, "monthly_rent": 1750.0, "status": "Active", "notes": "", "early_leave_notice_date": None, "created_at": _today()},
        {"id": 7, "ni_number": "NI-GG789012G", "full_name": "Mason Taylor", "phone": "07700111007", "email": "mason@email.com", "occupation": "Chef", "reference": "Cathy Taylor", "apartment_requirements": "2-Bedroom", "apt_id": 10, "lease_start": lease[6][0], "lease_end": lease[6][1], "deposit": 1100.0, "monthly_rent": 1100.0, "status": "Active", "notes": "", "early_leave_notice_date": None, "created_at": _today()},
        {"id": 8, "ni_number": "NI-HH890123H", "full_name": "Ava Anderson", "phone": "07700111008", "email": "ava@email.com", "occupation": "Solicitor", "reference": "Bob Anderson", "apartment_requirements": "1-Bedroom", "apt_id": 12, "lease_start": lease[7][0], "lease_end": lease[7][1], "deposit": 850.0, "monthly_rent": 850.0, "status": "Active", "notes": "", "early_leave_notice_date": None, "created_at": _today()},
    ]

    payments: list[dict] = []
    pid = 1
    for t in tenants:
        rent = t["monthly_rent"]
        for m in (3, 2, 1):
            due = (datetime.date.today() - datetime.timedelta(days=30 * m)).replace(day=1).isoformat()
            paid = due if m > 1 else None
            status = "Paid" if paid else "Overdue"
            payments.append({
                "id": pid,
                "tenant_id": t["id"],
                "amount": rent,
                "due_date": due,
                "paid_date": paid,
                "status": status,
                "type": "Rent",
                "late_notified": 0,
                "notes": "",
            })
            pid += 1

    maintenance = [
        {"id": 1, "tenant_id": 1, "apt_id": 1, "title": "Leaking Tap", "description": "Kitchen tap dripping continuously", "priority": "High", "status": "Resolved", "reported_date": _days_from_today(-20), "scheduled_date": _days_from_today(-18), "resolved_date": _days_from_today(-17), "assigned_to": 7, "cost": 120.0, "time_spent": 3.0, "communication_sent": 1, "notes": ""},
        {"id": 2, "tenant_id": 2, "apt_id": 2, "title": "Broken Heater", "description": "Radiator not working", "priority": "High", "status": "In Progress", "reported_date": _days_from_today(-5), "scheduled_date": _days_from_today(2), "resolved_date": None, "assigned_to": 7, "cost": 0.0, "time_spent": 0.0, "communication_sent": 1, "notes": ""},
        {"id": 3, "tenant_id": 3, "apt_id": 4, "title": "Cracked Window", "description": "Bedroom window cracked", "priority": "Medium", "status": "Open", "reported_date": _days_from_today(-2), "scheduled_date": None, "resolved_date": None, "assigned_to": 7, "cost": 0.0, "time_spent": 0.0, "communication_sent": 0, "notes": ""},
        {"id": 4, "tenant_id": 4, "apt_id": 5, "title": "Lift Fault", "description": "Lift on floor 2 not stopping", "priority": "High", "status": "Open", "reported_date": _days_from_today(-1), "scheduled_date": None, "resolved_date": None, "assigned_to": 7, "cost": 0.0, "time_spent": 0.0, "communication_sent": 0, "notes": ""},
        {"id": 5, "tenant_id": 5, "apt_id": 7, "title": "Pest Control", "description": "Cockroaches reported in kitchen", "priority": "Medium", "status": "Resolved", "reported_date": _days_from_today(-30), "scheduled_date": _days_from_today(-26), "resolved_date": _days_from_today(-25), "assigned_to": 8, "cost": 200.0, "time_spent": 5.0, "communication_sent": 1, "notes": ""},
        {"id": 6, "tenant_id": 6, "apt_id": 8, "title": "Faulty Electrics", "description": "Intermittent power in living room", "priority": "High", "status": "In Progress", "reported_date": _days_from_today(-3), "scheduled_date": _days_from_today(1), "resolved_date": None, "assigned_to": 7, "cost": 0.0, "time_spent": 0.0, "communication_sent": 1, "notes": ""},
    ]

    complaints = [
        {"id": 1, "tenant_id": 1, "title": "Noisy Neighbours", "description": "Upstairs neighbours loud past midnight", "status": "Open", "created_at": _days_from_today(-3), "resolved_at": None},
        {"id": 2, "tenant_id": 3, "title": "Parking Issue", "description": "Another tenant in my parking space", "status": "Open", "created_at": _days_from_today(-2), "resolved_at": None},
        {"id": 3, "tenant_id": 5, "title": "Water Pressure Low", "description": "Water pressure low for a week", "status": "Resolved", "created_at": _days_from_today(-10), "resolved_at": _days_from_today(-8)},
    ]

    locations = [
        {"id": 1, "name": "Bristol", "created_at": _today()},
        {"id": 2, "name": "London", "created_at": _today()},
        {"id": 3, "name": "Manchester", "created_at": _today()},
        {"id": 4, "name": "Cardiff", "created_at": _today()},
    ]

    return {
        "users": users,
        "apartments": apartments,
        "tenants": tenants,
        "payments": payments,
        "maintenance": maintenance,
        "complaints": complaints,
        "locations": locations,
    }


_STATE = _seed_state()


def _next_id(table: str) -> int:
    items = _STATE[table]
    return (max((x["id"] for x in items), default=0) + 1) if items else 1


def _find(table: str, item_id: int) -> dict | None:
    for row in _STATE[table]:
        if row["id"] == item_id:
            return row
    return None


def _tenant_with_join(t: dict) -> dict:
    row = copy.deepcopy(t)
    apt = _find("apartments", t.get("apt_id") or -1)
    row["apt_number"] = apt["apt_number"] if apt else None
    row["location"] = apt["location"] if apt else None
    return row


def _payment_with_join(p: dict) -> dict:
    row = copy.deepcopy(p)
    tenant = _find("tenants", p["tenant_id"])
    apt = _find("apartments", tenant.get("apt_id") if tenant else -1)
    row["full_name"] = tenant["full_name"] if tenant else None
    row["location"] = apt["location"] if apt else None
    row["apt_number"] = apt["apt_number"] if apt else None
    return row


def _maintenance_with_join(m: dict) -> dict:
    row = copy.deepcopy(m)
    tenant = _find("tenants", m.get("tenant_id") or -1)
    apt = _find("apartments", m.get("apt_id") or -1)
    staff = _find("users", m.get("assigned_to") or -1)
    row["full_name"] = tenant["full_name"] if tenant else None
    row["location"] = apt["location"] if apt else None
    row["apt_number"] = apt["apt_number"] if apt else None
    row["staff_name"] = staff["full_name"] if staff else None
    return row


def _complaint_with_join(c: dict) -> dict:
    row = copy.deepcopy(c)
    tenant = _find("tenants", c.get("tenant_id") or -1)
    apt = _find("apartments", tenant.get("apt_id") if tenant else -1)
    row["full_name"] = tenant["full_name"] if tenant else None
    row["location"] = apt["location"] if apt else None
    row["apt_number"] = apt["apt_number"] if apt else None
    return row


# ----------------------------------------------------------
# Init/Auth
# ----------------------------------------------------------
def init_db():
    """Compatibility no-op for in-memory static mode."""
    return None


def login(username: str, password: str) -> Optional[dict]:
    pw = _hash(password)
    for u in _STATE["users"]:
        if u["username"] == username and u["password"] == pw and u.get("active", 1):
            return copy.deepcopy(u)
    return None


# ----------------------------------------------------------
# Users
# ----------------------------------------------------------
def get_all_users(location=None):
    users = [copy.deepcopy(u) for u in _STATE["users"]]
    if location and location != "All":
        users = [u for u in users if u["location"] == location]
    return sorted(users, key=lambda x: (x.get("role", ""), x.get("full_name", "")))


def add_user(username, password, full_name, role, location, email=""):
    _STATE["users"].append({
        "id": _next_id("users"),
        "username": username,
        "password": _hash(password),
        "full_name": full_name,
        "role": role,
        "location": location,
        "email": email,
        "active": 1,
        "created_at": _today(),
    })


def update_user(uid, full_name, role, location, email, active):
    u = _find("users", uid)
    if not u:
        return
    u["full_name"] = full_name
    u["role"] = role
    u["location"] = location
    u["email"] = email
    u["active"] = int(bool(active))


def updateUserPassword(uid: int, password: str):
    u = _find("users", uid)
    if not u:
        return
    u["password"] = _hash(password)


def delete_user(uid):
    u = _find("users", uid)
    if u:
        u["active"] = 0


# ----------------------------------------------------------
# Apartments
# ----------------------------------------------------------
def get_all_apartments(location=None):
    rows = [copy.deepcopy(a) for a in _STATE["apartments"]]
    if location and location != "All":
        rows = [a for a in rows if a["location"] == location]
    return sorted(rows, key=lambda x: (x.get("location", ""), x.get("apt_number", "")))


def add_apartment(apt_number, location, apt_type, rooms, monthly_rent, floor=1, desc=""):
    _STATE["apartments"].append({
        "id": _next_id("apartments"),
        "apt_number": apt_number,
        "location": location,
        "type": apt_type,
        "rooms": int(rooms),
        "monthly_rent": float(monthly_rent),
        "status": "Vacant",
        "floor": int(floor),
        "description": desc,
    })


def update_apartment(apt_id, apt_number, location, apt_type, rooms, monthly_rent, status, floor, desc):
    a = _find("apartments", apt_id)
    if not a:
        return
    a["apt_number"] = apt_number
    a["location"] = location
    a["type"] = apt_type
    a["rooms"] = int(rooms)
    a["monthly_rent"] = float(monthly_rent)
    a["status"] = status
    a["floor"] = int(floor)
    a["description"] = desc


def delete_apartment(apt_id):
    _STATE["apartments"] = [a for a in _STATE["apartments"] if a["id"] != apt_id]



def get_vacant_apartments():
    out = []
    for a in _STATE["apartments"]:
        if a.get("status") == "Vacant":
            out.append((a["id"], f"{a['apt_number']} ({a['location']})"))
    return out


# ----------------------------------------------------------
# Tenants
# ----------------------------------------------------------
def get_all_tenants(location=None):
    rows = [_tenant_with_join(t) for t in _STATE["tenants"]]
    if location and location != "All":
        rows = [t for t in rows if t.get("location") == location]
    return sorted(rows, key=lambda x: x.get("full_name", ""))


def add_tenant(ni, name, phone, email, occupation, reference,
               apartment_requirements, apt_id, lease_start, lease_end,
               deposit, monthly_rent):
    _STATE["tenants"].append({
        "id": _next_id("tenants"),
        "ni_number": ni,
        "full_name": name,
        "phone": phone,
        "email": email,
        "occupation": occupation,
        "reference": reference,
        "apartment_requirements": apartment_requirements,
        "apt_id": apt_id,
        "lease_start": lease_start,
        "lease_end": lease_end,
        "deposit": float(deposit),
        "monthly_rent": float(monthly_rent),
        "status": "Active",
        "notes": "",
        "early_leave_notice_date": None,
        "created_at": _today(),
    })
    if apt_id:
        a = _find("apartments", int(apt_id))
        if a:
            a["status"] = "Occupied"


def update_tenant(tid, ni, name, phone, email, occupation,
                  reference, apartment_requirements, lease_start,
                  lease_end, deposit, monthly_rent, status, notes):
    t = _find("tenants", tid)
    if not t:
        return
    t["ni_number"] = ni
    t["full_name"] = name
    t["phone"] = phone
    t["email"] = email
    t["occupation"] = occupation
    t["reference"] = reference
    t["apartment_requirements"] = apartment_requirements
    t["lease_start"] = lease_start
    t["lease_end"] = lease_end
    t["deposit"] = float(deposit)
    t["monthly_rent"] = float(monthly_rent)
    t["status"] = status
    t["notes"] = notes


def delete_tenant(tid):
    t = _find("tenants", tid)
    if t and t.get("apt_id"):
        a = _find("apartments", t["apt_id"])
        if a:
            a["status"] = "Vacant"
    _STATE["tenants"] = [x for x in _STATE["tenants"] if x["id"] != tid]


def get_tenant_by_id(tid):
    t = _find("tenants", tid)
    return copy.deepcopy(t) if t else None


# ----------------------------------------------------------
# Payments
# ----------------------------------------------------------
def get_all_payments(location=None):
    rows = [_payment_with_join(p) for p in _STATE["payments"]]
    if location and location != "All":
        rows = [p for p in rows if p.get("location") == location]
    return sorted(rows, key=lambda x: x.get("due_date", ""), reverse=True)


def generateInvoice(tenant_id, amount, due_date, payment_type="Rent", notes=""):
    _STATE["payments"].append({
        "id": _next_id("payments"),
        "tenant_id": int(tenant_id),
        "amount": float(amount),
        "due_date": due_date,
        "paid_date": None,
        "status": "Pending",
        "type": payment_type,
        "late_notified": 0,
        "notes": notes,
    })


def markAsPaid(payment_id):
    p = _find("payments", payment_id)
    if not p:
        return
    p["paid_date"] = _today()
    p["status"] = "Paid"


# ----------------------------------------------------------
# Maintenance
# ----------------------------------------------------------
def get_all_maintenance(location=None):
    rows = [_maintenance_with_join(m) for m in _STATE["maintenance"]]
    if location and location != "All":
        rows = [m for m in rows if m.get("location") == location]
    return sorted(rows, key=lambda x: x.get("reported_date", ""), reverse=True)


def add_maintenance(tenant_id, apt_id, title, description,
                    priority="Medium", assigned_to=None, scheduled_date=None):
    _STATE["maintenance"].append({
        "id": _next_id("maintenance"),
        "tenant_id": int(tenant_id) if tenant_id else None,
        "apt_id": int(apt_id) if apt_id else None,
        "title": title,
        "description": description,
        "priority": priority,
        "status": "Open",
        "reported_date": _today(),
        "scheduled_date": scheduled_date,
        "resolved_date": None,
        "assigned_to": int(assigned_to) if assigned_to else None,
        "cost": 0.0,
        "time_spent": 0.0,
        "communication_sent": 0,
        "notes": "",
    })


def resolveIssue(mid, cost, time_spent, notes=""):
    m = _find("maintenance", mid)
    if not m:
        return
    m["status"] = "Resolved"
    m["resolved_date"] = _today()
    m["cost"] = float(cost)
    m["time_spent"] = float(time_spent)
    m["notes"] = notes


def update_maintenance_status(mid, status):
    m = _find("maintenance", mid)
    if m:
        m["status"] = status


# ----------------------------------------------------------
# Reports
# ----------------------------------------------------------
def getOccupancyByCity():
    by_loc: dict[str, dict] = {}
    for a in _STATE["apartments"]:
        loc = a["location"]
        if loc not in by_loc:
            by_loc[loc] = {"location": loc, "total": 0, "occupied": 0}
        by_loc[loc]["total"] += 1
        if a.get("status") == "Occupied":
            by_loc[loc]["occupied"] += 1
    return [by_loc[k] for k in sorted(by_loc.keys())]


def compareCollectedVsPending(location=None):
    rows = get_all_payments(location)
    collected = sum(float(p.get("amount") or 0) for p in rows if p.get("status") == "Paid")
    pending = sum(float(p.get("amount") or 0) for p in rows if p.get("status") != "Paid")
    return {"collected": round(collected, 2), "pending": round(pending, 2)}


def trackCostsByLocation(location=None):
    rows = get_all_maintenance(location)
    by_status: dict[str, dict] = {}
    for m in rows:
        st = m.get("status", "Unknown")
        if st not in by_status:
            by_status[st] = {"status": st, "total_cost": 0.0, "count": 0}
        by_status[st]["total_cost"] += float(m.get("cost") or 0)
        by_status[st]["count"] += 1
    out = []
    for st in sorted(by_status.keys()):
        r = by_status[st]
        r["total_cost"] = round(r["total_cost"], 2)
        out.append(r)
    return out


def dashboard_stats(user: dict) -> dict:
    loc = user.get("location")
    if user.get("role") == "Manager":
        loc = None

    apartments = get_all_apartments(loc)
    tenants = get_all_tenants(loc)
    maintenance = get_all_maintenance(loc)
    payments = get_all_payments(loc)

    return {
        "total_apts": len(apartments),
        "occupied_apts": sum(1 for a in apartments if a.get("status") == "Occupied"),
        "total_tenants": len(tenants),
        "active_maint": sum(1 for m in maintenance if m.get("status") != "Resolved"),
        "pending_rent": round(sum(float(p.get("amount") or 0) for p in payments if p.get("status") == "Overdue"), 2),
        "collected_rent": round(sum(float(p.get("amount") or 0) for p in payments if p.get("status") == "Paid"), 2),
    }


# ----------------------------------------------------------
# Locations
# ----------------------------------------------------------
def get_all_locations():
    return sorted([x["name"] for x in _STATE["locations"]])


def expandBusiness(name: str):
    name = (name or "").strip()
    if not name:
        return
    existing = {l["name"].lower() for l in _STATE["locations"]}
    if name.lower() not in existing:
        _STATE["locations"].append({"id": _next_id("locations"), "name": name, "created_at": _today()})


# ----------------------------------------------------------
# Complaints
# ----------------------------------------------------------
def get_all_complaints(location=None):
    rows = [_complaint_with_join(c) for c in _STATE["complaints"]]
    if location and location != "All":
        rows = [c for c in rows if c.get("location") == location]
    return sorted(rows, key=lambda x: x.get("created_at", ""), reverse=True)


def add_complaint(tenant_id, title, description):
    _STATE["complaints"].append({
        "id": _next_id("complaints"),
        "tenant_id": int(tenant_id),
        "title": title,
        "description": description,
        "status": "Open",
        "created_at": _today(),
        "resolved_at": None,
    })


def updateStatus(cid, status):
    c = _find("complaints", cid)
    if not c:
        return
    c["status"] = status
    c["resolved_at"] = _today() if status == "Resolved" else None


# ----------------------------------------------------------
# Early leave
# ----------------------------------------------------------
def calculatePenalty(monthly_rent: float) -> float:
    return round((monthly_rent or 0) * 0.05, 2)


def terminateEarly(tid):
    tenant = _find("tenants", tid)
    if not tenant:
        return None, "Tenant not found."
    if tenant.get("status") != "Active":
        return None, "Tenant is not currently active."

    monthly_rent = float(tenant.get("monthly_rent") or 0)
    penalty = calculatePenalty(monthly_rent)
    notice_date = _today()
    leave_date = _days_from_today(30)

    tenant["status"] = "Leaving"
    tenant["early_leave_notice_date"] = notice_date
    tenant["lease_end"] = leave_date
    tenant["notes"] = (
        f"Early leave requested {notice_date}. Leave date: {leave_date}. "
        f"Penalty: GBP {penalty:.2f} (5% of GBP {monthly_rent:.2f})"
    )

    generateInvoice(
        tenant_id=tid,
        amount=penalty,
        due_date=notice_date,
        payment_type="Early Leave Penalty",
        notes=f"5% early termination penalty on GBP {monthly_rent:.2f}/month",
    )
    return penalty, leave_date


# ----------------------------------------------------------
# Late notifications
# ----------------------------------------------------------
def get_late_payments(location=None):
    today = _today()
    rows = get_all_payments(location)
    return [
        p for p in rows
        if p.get("status") in ("Pending", "Overdue") and (p.get("due_date") or "") < today
    ]


def mark_late_notifications_sent(payment_ids: list):
    payment_id_set = {int(x) for x in payment_ids}
    for p in _STATE["payments"]:
        if p["id"] in payment_id_set:
            p["status"] = "Overdue"
            p["late_notified"] = 1


# ----------------------------------------------------------
# Maintenance helpers
# ----------------------------------------------------------
def get_maintenance_staff(location=None):
    users = get_all_users(location)
    return [
        (u["id"], u["full_name"])
        for u in users
        if u.get("role") == "Maintenance Staff" and u.get("active")
    ]


def update_maintenance_schedule(mid, scheduled_date, notes=""):
    m = _find("maintenance", mid)
    if not m:
        return
    m["scheduled_date"] = scheduled_date
    m["communication_sent"] = 1
    m["notes"] = notes


# ----------------------------------------------------------
# Tenant payment history
# ----------------------------------------------------------
def get_tenant_payments(tenant_id):
    rows = [copy.deepcopy(p) for p in _STATE["payments"] if p.get("tenant_id") == tenant_id]
    return sorted(rows, key=lambda x: x.get("due_date", ""), reverse=True)


# ----------------------------------------------------------
# Expiring leases
# ----------------------------------------------------------
def get_expiring_leases(days=30, location=None):
    today = datetime.date.today()
    future = today + datetime.timedelta(days=int(days))
    rows = get_all_tenants(location)
    out = []
    for t in rows:
        try:
            lease_end = datetime.date.fromisoformat(t.get("lease_end") or "")
        except ValueError:
            continue
        if today <= lease_end <= future and t.get("status") == "Active":
            out.append(t)
    return sorted(out, key=lambda x: x.get("lease_end", ""))


def processPayment(payment_id: int) -> bool:
    p = _find("payments", payment_id)
    if not p or p.get("status") == "Paid":
        return False
    markAsPaid(payment_id)
    return True


def generateReceipt(payment_id: int) -> dict:
    p = _find("payments", payment_id)
    return copy.deepcopy(p) if p else {}


def generateReport(location=None, start_date=None, end_date=None):
    return {
        "occupancy": getOccupancyByCity(),
        "financial": compareCollectedVsPending(location),
        "maintenance": trackCostsByLocation(location),
        "period": {"start": start_date, "end": end_date},
    }


# Backward-compatible aliases
authenticate = login
add_payment = generateInvoice
mark_payment_paid = markAsPaid
resolve_maintenance = resolveIssue
occupancy_by_location = getOccupancyByCity
financial_summary = compareCollectedVsPending
maintenance_cost_summary = trackCostsByLocation
add_location = expandBusiness
update_complaint_status = updateStatus
process_early_leave = terminateEarly
update_user_password = updateUserPassword
