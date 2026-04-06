<div align="center">

# Paragon Apartment Management System (PAMS)

[![Python](https://img.shields.io/badge/Python-3.10%20%E2%80%93%203.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-6.5%2B-41CD52?style=flat-square&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-Academic-lightgrey?style=flat-square)]()
[![Module](https://img.shields.io/badge/Module-UFCF8S--30--2-blue?style=flat-square)]()
[![Status](https://img.shields.io/badge/Status-Complete-success?style=flat-square)]()

> A fully-featured desktop application for managing multi-location apartment operations across Bristol, Cardiff, London, and Manchester — built with Python, PySide6, and SQLite.

</div>

---

## Table of Contents

- [Paragon Apartment Management System (PAMS)](#paragon-apartment-management-system-pams)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Features](#features)
    - [Account \& User Management](#account--user-management)
    - [Tenant Management](#tenant-management)
    - [Apartment Management](#apartment-management)
    - [Payment \& Billing](#payment--billing)
    - [Maintenance](#maintenance)
    - [Complaints](#complaints)
    - [Reporting](#reporting)
    - [Dashboard](#dashboard)
    - [Manager-Only](#manager-only)
    - [Non-Functional](#non-functional)
  - [Project Structure](#project-structure)
  - [Database Schema](#database-schema)
  - [Roles \& Access Control](#roles--access-control)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
  - [Default Login Credentials](#default-login-credentials)
  - [Non-Functional Requirements](#non-functional-requirements)
  - [Methodology](#methodology)
  - [Team Contributions](#team-contributions)

---

## Overview

**PAMS** (Paragon Apartment Management System) is a desktop management application developed as part of the Advanced Software Development module (UFCF8S-30-2). It addresses the real-world operational challenges faced by the Paragon apartment company — a multi-city property business relying on paper-based, error-prone, and unscalable processes.

The system consolidates all core property management workflows into a single, role-based desktop application:

- Centralised tenant and apartment records across all four UK cities
- Role-based access control (RBAC) with five distinct staff roles
- Invoice generation, late payment tracking, and financial reporting
- Maintenance request lifecycle management from report to resolution
- Complaint logging and resolution tracking
- Real-time occupancy and financial performance reporting
- Full audit logging for security and accountability

---

## Features

### Account & User Management
- Five role-based access levels enforced at every screen
- Administrators manage staff accounts within their assigned city
- Soft-delete for accounts (preserves audit trail, never hard-deletes)
- Secure password storage using PBKDF2-HMAC-SHA256 with 100,000 iterations
- Password update and role reassignment by administrators

### Tenant Management
- Register tenants with NI number, contact details, occupation, references, and apartment requirements
- NI number uniqueness enforced — prevents duplicate registrations
- Lease creation is automatic on tenant registration
- Track full payment history and complaint logs per tenant
- Early lease termination: 1-month notice period enforced, 5% monthly rent penalty automatically calculated and invoiced
- Tenant status lifecycle: Active → Leaving → Inactive → Archived

### Apartment Management
- Register apartments with location, type, rooms, floor, monthly rent, and description
- Status lifecycle: Vacant → Occupied → Maintenance
- Occupancy status updates automatically when tenants are assigned or removed
- Filter apartments by city

### Payment & Billing
- Generate invoices (Pending) for any tenant
- Mark payments as Paid with automatic date recording
- Receipt generation with full tenant and apartment details
- Late payment detection (past due date, status not Paid)
- Late notification flagging (`late_notified`) to prevent duplicate chasing
- Overdue rent totals surfaced on the dashboard in real time

### Maintenance
- Log maintenance requests with title, description, priority (Low / Medium / High / Critical)
- Assign to available maintenance staff filtered by location
- Schedule maintenance with date communication flag to tenant (`communication_sent`)
- Status lifecycle: Open → Assigned → Scheduled → In Progress → Resolved
- Record resolution date, repair cost, and time spent on resolution
- Cost tracking feeds directly into financial and performance reports

### Complaints
- Log tenant complaints with title and description
- Status tracking: Open → In Progress → Resolved
- Resolution timestamp auto-recorded on status change to Resolved

### Reporting
- Occupancy report: total vs. occupied apartments per city
- Financial summary: collected vs. pending rent (city-filtered or company-wide)
- Maintenance cost breakdown by status
- Full performance report per city combining all three above
- Expiring lease alerts for administrators (configurable warning window, default 30 days)

### Dashboard
- Role-aware KPI tiles: Total Apartments, Occupied, Tenants, Active Maintenance Jobs
- Live collected vs. pending rent figures
- Fully filtered to the logged-in user's city (Manager sees all)

### Manager-Only
- Company-wide performance view across all four cities
- Expand business to new cities directly from the UI

### Non-Functional
- Thread-safe SQLite with `threading.Lock()` and thread-local connections
- WAL journal mode for concurrent read performance
- Foreign key enforcement on every connection
- Full audit log with old/new value capture
- Python version guard (blocks 3.14+ at startup)
- Qt plugin path isolation to prevent environment conflicts

---

## Project Structure

```
ASD PROJECT/
├── main.py                          # Application entry point — boots Qt, initialises DB, launches login
├── requirements.txt                 # Python dependencies (PySide6 >= 6.5, < 6.11)
├── .gitignore                       # Excludes venv, pycache, .db files, IDE folders
├── pams/
│   ├── __init__.py
│   ├── database.py                  # All SQLite logic — schema, CRUD, business rules, reports
│   ├── theme.py                     # Design tokens, colour palette, QSS stylesheet
│   ├── widgets.py                   # Reusable UI components (cards, badges, KPI tiles, toasts)
│   ├── login_view.py                # Login screen with role-based redirect
│   ├── main_app.py                  # Root window — sidebar, navigation, session state
│   └── views/
│       ├── dashboard_view.py        # Role-aware KPI dashboard
│       ├── tenant_view.py           # Tenant register, search, edit, early leave
│       ├── apartment_view.py        # Apartment register, edit, status management
│       ├── payment_view.py          # Invoice generation, mark paid, late payment list
│       ├── maintenance_view.py      # Maintenance log, assign, schedule, resolve
│       ├── complaint_view.py        # Complaint log and resolution tracking
│       ├── report_view.py           # Occupancy, financial, maintenance, lease reports
│       └── user_view.py             # Staff account management (Admin only)
└── pams.db                          # SQLite database (auto-created and seeded on first run)
```

---

## Database Schema

The database comprises eight core tables plus an audit log, all with foreign key constraints enforced:

| Table | Purpose |
|---|---|
| `locations` | UK cities the company operates in |
| `users` | Staff accounts with RBAC role and city assignment |
| `apartments` | All apartment units with type, rent, and occupancy status |
| `tenants` | Tenant records including NI, contact, lease dates, and early leave fields |
| `leases` | Formal lease contracts with termination and penalty tracking |
| `payments` | Invoices and payment records with late notification flags |
| `maintenance` | Maintenance requests with priority, assignment, schedule, cost, and time |
| `complaints` | Tenant complaints with status and resolution timestamp |
| `audit_log` | Full action audit trail with old/new value capture per change |

Performance indexes are defined on all commonly filtered columns (tenant status, payment status/due date, maintenance status, complaint tenant).

---

## Roles & Access Control

| Role | Access Scope | Key Permissions |
|---|---|---|
| **Front-Desk Staff** | Own city | Register tenants, log maintenance requests, log complaints |
| **Finance Manager** | Own city | Manage invoices, mark payments, view late payments, financial reports |
| **Maintenance Staff** | Own city | View and update maintenance requests, resolve and log costs |
| **Administrator** | Own city | Full access to all modules within assigned city, manage user accounts |
| **Manager** | All cities | Company-wide reports, performance overview, expand to new cities |

---

## Getting Started

### Prerequisites

- Python 3.10, 3.11, 3.12, or 3.13 (Python 3.14+ is explicitly blocked)
- Windows, macOS, or Linux desktop environment

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/ThomasYeo305/AdvancedSoftwareDevelopmentGroupProject.git
cd AdvancedSoftwareDevelopmentGroupProject
```

**2. Create and activate a virtual environment**

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Run the application**

```bash
python main.py
```

The database (`pams.db`) is created and seeded with mock data automatically on first launch. No manual setup is required.

---

## Default Login Credentials

The database is pre-seeded with the following demo accounts for testing each role:

| Username | Password | Role | City |
|---|---|---|---|
| `admin_bristol` | `admin123` | Administrator | Bristol |
| `admin_london` | `admin123` | Administrator | London |
| `admin_manc` | `admin123` | Administrator | Manchester |
| `admin_cardiff` | `admin123` | Administrator | Cardiff |
| `manager` | `manager123` | Manager | All cities |
| `frontdesk1` | `front123` | Front-Desk Staff | Bristol |
| `frontdesk2` | `front123` | Front-Desk Staff | Manchester |
| `finance1` | `finance123` | Finance Manager | Bristol |
| `finance2` | `finance123` | Finance Manager | London |
| `maint1` | `maint123` | Maintenance Staff | Bristol |
| `maint2` | `maint123` | Maintenance Staff | London |

---

## Non-Functional Requirements

- **Security:** PBKDF2-HMAC-SHA256 password hashing, role-based access enforcement, audit log
- **Scalability:** Multi-city architecture, location-scoped queries, Manager-level global view
- **Efficiency:** WAL journal mode, thread-safe singleton DB connection, indexed queries
- **Usability:** Professional property-tech UI design, consistent navigation, toast notifications
- **Reliability:** Foreign key enforcement, soft-delete (no data loss), NI uniqueness validation

---

## Methodology

Agile development approach with iterative sprints. Each sprint focused on delivering one functional module end-to-end before moving to the next. Regular Git commits were used throughout to track progress and individual contributions across the team.

---

## Team Contributions

Evidence of individual contributions is maintained through Git commit history. Each team member's commits reflect their ownership of specific modules and features throughout the development sprints.

To view the full contribution history:

```bash
git log --oneline --all
```

Or visit the [GitHub repository](https://github.com/ThomasYeo305/AdvancedSoftwareDevelopmentGroupProject/commits/main).
