BEGIN TRANSACTION;
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
INSERT INTO "apartments" VALUES(1,'APT-101','Bristol','Studio',1,850.0,'Occupied',1,'Modern studio with open-plan living');
INSERT INTO "apartments" VALUES(2,'APT-102','Bristol','1-Bedroom',1,1050.0,'Occupied',1,'Bright 1-bed with private balcony');
INSERT INTO "apartments" VALUES(3,'APT-103','Bristol','2-Bedroom',2,1400.0,'Occupied',1,'Spacious 2-bed, freshly renovated');
INSERT INTO "apartments" VALUES(4,'APT-104','Bristol','Studio',1,820.0,'Maintenance',1,'Undergoing full refurbishment');
INSERT INTO "apartments" VALUES(5,'APT-201','Bristol','2-Bedroom',2,1350.0,'Vacant',2,'South-facing 2-bed with river views');
INSERT INTO "apartments" VALUES(6,'APT-202','Bristol','3-Bedroom',3,1800.0,'Occupied',2,'Large family unit with garden access');
INSERT INTO "apartments" VALUES(7,'APT-203','Bristol','1-Bedroom',1,1100.0,'Vacant',2,'Corner unit, lots of natural light');
INSERT INTO "apartments" VALUES(8,'APT-301','Bristol','Penthouse',4,3200.0,'Vacant',3,'Luxury penthouse, 360-degree views');
INSERT INTO "apartments" VALUES(9,'APT-L01','London','Studio',1,1400.0,'Occupied',1,'Bridge view studio, Zone 1');
INSERT INTO "apartments" VALUES(10,'APT-L02','London','1-Bedroom',1,1750.0,'Occupied',1,'Prime Shoreditch location');
INSERT INTO "apartments" VALUES(11,'APT-L03','London','2-Bedroom',2,2400.0,'Occupied',2,'Excellent transport links');
INSERT INTO "apartments" VALUES(12,'APT-L04','London','3-Bedroom',3,3100.0,'Occupied',3,'Luxury flat with concierge service');
INSERT INTO "apartments" VALUES(13,'APT-L05','London','Studio',1,1350.0,'Occupied',1,'Compact studio, near Canary Wharf');
INSERT INTO "apartments" VALUES(14,'APT-M01','Manchester','2-Bedroom',2,1100.0,'Occupied',1,'City centre, close to Arndale');
INSERT INTO "apartments" VALUES(15,'APT-M02','Manchester','1-Bedroom',1,900.0,'Occupied',1,'Northern Quarter, character property');
INSERT INTO "apartments" VALUES(16,'APT-M03','Manchester','Studio',1,750.0,'Occupied',1,'Compact modern studio');
INSERT INTO "apartments" VALUES(17,'APT-M04','Manchester','2-Bedroom',2,1050.0,'Occupied',2,'Ancoats area, newly built');
INSERT INTO "apartments" VALUES(18,'APT-C01','Cardiff','1-Bedroom',1,850.0,'Occupied',1,'Cardiff Bay waterfront');
INSERT INTO "apartments" VALUES(19,'APT-C02','Cardiff','2-Bedroom',2,1100.0,'Occupied',1,'Quiet residential, parking included');
INSERT INTO "apartments" VALUES(20,'APT-C03','Cardiff','Studio',1,700.0,'Occupied',1,'City centre, compact and efficient');
INSERT INTO "apartments" VALUES(21,'APT-C04','Cardiff','1-Bedroom',1,950.0,'Occupied',2,'Roath area, close to university');
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
INSERT INTO "audit_log" VALUES(1,1,'LOGIN','User','1',NULL,NULL,'2026-04-04 20:20:06');
INSERT INTO "audit_log" VALUES(2,6,'ADD_TENANT','Tenant','1',NULL,'Oliver Thompson','2026-04-04 20:20:06');
INSERT INTO "audit_log" VALUES(3,6,'ADD_TENANT','Tenant','2',NULL,'Emma Williams','2026-04-04 20:20:06');
INSERT INTO "audit_log" VALUES(4,10,'MARK_PAID','Payment','1','Overdue','Paid','2026-04-04 20:20:06');
INSERT INTO "audit_log" VALUES(5,12,'RESOLVE_ISSUE','Maintenance','1','Open','Resolved','2026-04-04 20:20:06');
INSERT INTO "audit_log" VALUES(6,1,'ADD_APARTMENT','Apartment','1',NULL,'APT-101','2026-04-04 20:20:06');
INSERT INTO "audit_log" VALUES(7,5,'GENERATE_REPORT','Report',NULL,NULL,'Occupancy Report','2026-04-04 20:20:06');
INSERT INTO "audit_log" VALUES(8,10,'GENERATE_INVOICE','Payment','5',NULL,'Rent Invoice','2026-04-04 20:20:06');
INSERT INTO "audit_log" VALUES(9,6,'ADD_COMPLAINT','Complaint','1',NULL,'Noisy Neighbours','2026-04-04 20:20:06');
INSERT INTO "audit_log" VALUES(10,2,'LOGIN','User','2',NULL,NULL,'2026-04-04 20:20:06');
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
INSERT INTO "complaints" VALUES(1,1,'Noisy Neighbours','Upstairs neighbours extremely loud past midnight','Open','2026-04-01',NULL);
INSERT INTO "complaints" VALUES(2,3,'Parking Issue','Another tenant using my allocated parking space','Open','2026-04-02',NULL);
INSERT INTO "complaints" VALUES(3,5,'Water Pressure Low','Hot water pressure has been very low for over a week','Resolved','2026-03-25','2026-03-27');
INSERT INTO "complaints" VALUES(4,7,'Rubbish Collection','Communal bins not collected for two weeks','In Progress','2026-03-30',NULL);
INSERT INTO "complaints" VALUES(5,9,'Intercom Broken','Front door intercom system not working for residents','Open','2026-04-03',NULL);
INSERT INTO "complaints" VALUES(6,4,'Heating Insufficient','Central heating inadequate during cold weather','In Progress','2026-03-29',NULL);
INSERT INTO "complaints" VALUES(7,10,'Pest Sighting','Mice spotted in the communal hallway area','Open','2026-04-02',NULL);
INSERT INTO "complaints" VALUES(8,12,'Neighbour Dispute','Dispute over shared utility bill calculations','Resolved','2026-03-20','2026-03-25');
INSERT INTO "complaints" VALUES(9,13,'Lift Out of Order','Lift has been out of order for 3 days','Open','2026-04-01',NULL);
INSERT INTO "complaints" VALUES(10,2,'Bin Room Access','Bin room keypad code not working','Resolved','2026-03-15','2026-03-17');
INSERT INTO "complaints" VALUES(11,11,'Communal Light Fault','Communal hallway light flickering constantly','In Progress','2026-03-31',NULL);
INSERT INTO "complaints" VALUES(12,8,'Parking Space Blocked','Unknown vehicle blocking designated parking bay','Resolved','2026-03-27','2026-03-29');
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
INSERT INTO "leases" VALUES(1,1,2,'2025-10-06','2027-03-30',1050.0,1050.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(2,2,1,'2026-01-04','2026-12-30',850.0,850.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(3,3,5,'2026-03-05','2027-02-28',1350.0,1350.0,'Terminated','2026-04-06',67.5,'2026-04-04');
INSERT INTO "leases" VALUES(4,4,6,'2025-12-05','2026-11-30',1800.0,1800.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(5,5,9,'2026-02-03','2027-01-29',1400.0,1400.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(6,6,10,'2025-11-05','2026-10-31',1750.0,1750.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(7,7,14,'2025-10-06','2026-10-01',1100.0,1100.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(8,8,18,'2026-01-04','2026-12-30',850.0,850.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(9,9,12,'2026-02-03','2027-01-29',3100.0,3100.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(10,10,16,'2026-03-05','2027-02-28',750.0,750.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(11,11,20,'2025-12-05','2026-11-30',700.0,700.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(12,12,13,'2026-03-05','2027-02-28',1350.0,1350.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(13,13,21,'2026-02-03','2026-11-30',950.0,950.0,'Active',NULL,0.0,'2026-04-04');
INSERT INTO "leases" VALUES(16,16,11,'2026-04-12','2027-04-07',0.0,1000.0,'Active',NULL,0.0,'2026-04-12');
INSERT INTO "leases" VALUES(17,17,17,'2026-04-12','2027-04-07',500.0,1200.0,'Active',NULL,0.0,'2026-04-12');
INSERT INTO "leases" VALUES(18,18,15,'2026-04-12','2027-04-07',100.0,100.0,'Active',NULL,0.0,'2026-04-12');
INSERT INTO "leases" VALUES(19,19,19,'2026-04-12','2027-04-07',-500.0,-500.0,'Active',NULL,0.0,'2026-04-12');
INSERT INTO "leases" VALUES(21,21,3,'2026-14-15','2026-01-25',-7.0,-7.0,'Active',NULL,0.0,'2026-04-12');
CREATE TABLE locations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    created_at TEXT    NOT NULL DEFAULT (date('now'))
);
INSERT INTO "locations" VALUES(1,'Bristol','2026-04-04');
INSERT INTO "locations" VALUES(2,'Cardiff','2026-04-04');
INSERT INTO "locations" VALUES(3,'London','2026-04-04');
INSERT INTO "locations" VALUES(4,'Manchester','2026-04-04');
INSERT INTO "locations" VALUES(5,'Brixton','2026-04-06');
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
INSERT INTO "maintenance" VALUES(1,1,2,'Leaking Tap','Kitchen tap dripping continuously','High','Resolved','2026-03-15','2026-03-17','2026-03-18',12,120.0,3.0,1,'Parts replaced, tap fully functional');
INSERT INTO "maintenance" VALUES(2,2,1,'Broken Heater','Bedroom radiator not working','High','In Progress','2026-03-30','2026-04-06',NULL,12,0.0,0.0,1,'Replacement part ordered, ETA 3 days');
INSERT INTO "maintenance" VALUES(3,3,5,'Cracked Window','Bedroom window has a hairline crack','Medium','Open','2026-04-02','2026/04/23',NULL,12,0.0,0.0,1,'repair is iminent');
INSERT INTO "maintenance" VALUES(4,4,6,'Lift Fault','Floor 2 lift not stopping correctly','Critical','Open','2026-04-03',NULL,NULL,12,0.0,0.0,0,'');
INSERT INTO "maintenance" VALUES(5,5,9,'Pest Control','Cockroaches reported in kitchen','Medium','Resolved','2026-03-05','2026-03-09','2026-03-10',13,200.0,5.0,1,'Professional extermination completed');
INSERT INTO "maintenance" VALUES(6,6,10,'Faulty Electrics','Intermittent power in living room','High','Scheduled','2026-04-01','2026-04-05',NULL,13,0.0,0.0,1,'Electrician booked for site visit');
INSERT INTO "maintenance" VALUES(7,7,14,'Damp Patch','Damp patch on bathroom ceiling','Medium','Assigned','2026-03-28','2026-04-07',NULL,14,0.0,0.0,1,'Damp specialist assigned');
INSERT INTO "maintenance" VALUES(8,8,18,'Blocked Drain','Shower drain slow to empty','Low','Resolved','2026-03-21','2026-03-23','2026-03-23',15,45.0,1.5,1,'Drain rod cleared the blockage');
INSERT INTO "maintenance" VALUES(9,9,12,'Intercom Fault','Front door intercom not responding','Medium','Scheduled','2026-03-31','2026-04-09',NULL,13,0.0,0.0,1,'Engineer visit scheduled');
INSERT INTO "maintenance" VALUES(10,10,16,'Mould in Bathroom','Black mould on ceiling near shower','High','Open','2026-04-01',NULL,NULL,14,0.0,0.0,0,'');
INSERT INTO "maintenance" VALUES(11,11,20,'Broken Door Lock','Front door lock stiff and difficult to open','High','Resolved','2026-03-25','2026-03-27','2026-03-28',15,85.0,2.0,1,'Lock replaced with new mechanism');
INSERT INTO "maintenance" VALUES(12,12,13,'No Hot Water','Boiler not producing hot water','High','In Progress','2026-04-02','2026-04-05',NULL,13,0.0,0.0,1,'Boiler engineer booked');
INSERT INTO "maintenance" VALUES(13,13,21,'Noisy Pipes','Banging sounds from water pipes at night','Low','Open','2026-03-30',NULL,NULL,15,0.0,0.0,0,'');
INSERT INTO "maintenance" VALUES(14,1,2,'Broken Cupboard','Kitchen cupboard door hinge snapped','Low','Resolved','2026-02-18','2026-02-20','2026-02-21',12,25.0,0.5,1,'Hinge replaced');
INSERT INTO "maintenance" VALUES(15,5,9,'Thermostat Fault','Thermostat not reading temperature correctly','Medium','Assigned','2026-03-29','2026-04-06',NULL,13,0.0,0.0,1,'Smart thermostat replacement ordered');
INSERT INTO "maintenance" VALUES(16,1,1,'Toilet malfunctions','Running toilets and leaks at the base','Low','Assigned','2026-04-12',NULL,NULL,14,0.0,0.0,0,'');
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
INSERT INTO "payments" VALUES(1,1,NULL,1050.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(2,1,NULL,1050.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(3,1,NULL,1050.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(4,1,NULL,1050.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(5,1,NULL,1050.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(6,1,NULL,1050.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(7,2,NULL,850.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(8,2,NULL,850.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(9,2,NULL,850.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(10,2,NULL,850.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(11,2,NULL,850.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(12,2,NULL,850.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(13,3,NULL,1350.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(14,3,NULL,1350.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(15,3,NULL,1350.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(16,3,NULL,1350.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(17,3,NULL,1350.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(18,3,NULL,1350.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(19,4,NULL,1800.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(20,4,NULL,1800.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(21,4,NULL,1800.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(22,4,NULL,1800.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(23,4,NULL,1800.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(24,4,NULL,1800.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(25,5,NULL,1400.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(26,5,NULL,1400.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(27,5,NULL,1400.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(28,5,NULL,1400.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(29,5,NULL,1400.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(30,5,NULL,1400.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(31,6,NULL,1750.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(32,6,NULL,1750.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(33,6,NULL,1750.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(34,6,NULL,1750.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(35,6,NULL,1750.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(36,6,NULL,1750.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(37,7,NULL,1100.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(38,7,NULL,1100.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(39,7,NULL,1100.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(40,7,NULL,1100.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(41,7,NULL,1100.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(42,7,NULL,1100.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(43,8,NULL,850.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(44,8,NULL,850.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(45,8,NULL,850.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(46,8,NULL,850.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(47,8,NULL,850.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(48,8,NULL,850.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(49,9,NULL,3100.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(50,9,NULL,3100.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(51,9,NULL,3100.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(52,9,NULL,3100.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(53,9,NULL,3100.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(54,9,NULL,3100.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(55,10,NULL,750.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(56,10,NULL,750.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(57,10,NULL,750.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(58,10,NULL,750.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(59,10,NULL,750.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(60,10,NULL,750.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(61,11,NULL,700.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(62,11,NULL,700.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(63,11,NULL,700.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(64,11,NULL,700.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(65,11,NULL,700.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(66,11,NULL,700.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(67,12,NULL,1350.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(68,12,NULL,1350.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(69,12,NULL,1350.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(70,12,NULL,1350.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(71,12,NULL,1350.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(72,12,NULL,1350.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(73,13,NULL,950.0,'2025-10-01','2025-10-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(74,13,NULL,950.0,'2025-11-01','2025-11-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(75,13,NULL,950.0,'2025-12-01','2025-12-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(76,13,NULL,950.0,'2026-01-01','2026-01-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(77,13,NULL,950.0,'2026-02-01','2026-02-01','Paid','Rent',0,'');
INSERT INTO "payments" VALUES(78,13,NULL,950.0,'2026-03-01',NULL,'Overdue','Rent',1,'');
INSERT INTO "payments" VALUES(79,3,NULL,67.5,'2026-04-06',NULL,'Pending','Early Leave Penalty',0,'5% early termination penalty on £1350.00/month rent');
INSERT INTO "payments" VALUES(80,8,NULL,1200.0,'2026-04-12',NULL,'Pending','Rent',0,'');
INSERT INTO "payments" VALUES(81,11,NULL,1000.0,'2026-04-12',NULL,'Pending','Rent',0,'');
INSERT INTO "payments" VALUES(82,1,NULL,1200.0,'2026-04-12',NULL,'Pending','Rent',0,'');
INSERT INTO "payments" VALUES(83,8,NULL,100.0,'2026-04-20',NULL,'Pending','Rent',0,'');
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
INSERT INTO "tenants" VALUES(1,'NI-AA123456A','Oliver Thompson','07700111001','oliver@email.com','Software Engineer','John Smith','1-Bedroom',2,'2025-10-06','2027-03-30',1050.0,1050.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(2,'NI-BB234567B','Emma Williams','07700111002','emma@email.com','Nurse','Dr. Jones','1-Bedroom',1,'2026-01-04','2026-12-30',850.0,850.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(3,'NI-CC345678C','Noah Brown','07700111003','noah@email.com','Teacher','Mary Green','2-Bedroom',5,'2026-03-05','2026-04-19',1350.0,1350.0,'Leaving','Early leave requested 2026-04-06. Leave: 2026-05-06. Penalty: £67.50 (5% of £1350.00)','2026-04-06','2026-04-04');
INSERT INTO "tenants" VALUES(4,'NI-DD456789D','Sophia Davis','07700111004','sophia@email.com','Accountant','Peter Davis','3-Bedroom',6,'2025-12-05','2026-06-28',1800.0,1800.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(5,'NI-EE567890E','Liam Wilson','07700111005','liam@email.com','Architect','Jane Wilson','Studio',9,'2026-02-03','2027-01-29',1400.0,1400.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(6,'NI-FF678901F','Isabella Moore','07700111006','isab@email.com','Marketing Manager','Tom Moore','1-Bedroom',10,'2025-11-05','2026-10-31',1750.0,1750.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(7,'NI-GG789012G','Mason Taylor','07700111007','mason@email.com','Chef','Cathy Taylor','2-Bedroom',14,'2025-10-06','2026-05-04',1100.0,1100.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(8,'NI-HH890123H','Ava Anderson','07700111008','ava@email.com','Solicitor','Bob Anderson','1-Bedroom',18,'2026-01-04','2026-12-30',850.0,850.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(9,'NI-II901234I','Jack Robinson','07700111009','jack@email.com','Doctor','NHS Trust','3-Bedroom',12,'2026-02-03','2027-01-29',3100.0,3100.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(10,'NI-JJ012345J','Zoe Martinez','07700111010','zoe@email.com','Designer','Creative Co','Studio',16,'2026-03-05','2027-02-28',750.0,750.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(11,'NI-KK123456K','Harry Evans','07700111011','harry@email.com','Engineer','Rhys Evans','Studio',20,'2025-12-05','2026-06-03',700.0,700.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(12,'NI-LL234567L','Sophie Clarke','07700111012','sophie@email.com','Pharmacist','NHS Trust','2-Bedroom',13,'2026-03-05','2027-02-28',1350.0,1350.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(13,'NI-MM345678M','Ethan Johnson','07700111013','ethan@email.com','Data Analyst','Tech Corp','1-Bedroom',21,'2026-02-03','2026-11-30',950.0,950.0,'Active','',NULL,'2026-04-04');
INSERT INTO "tenants" VALUES(16,'AB2739373D','Jean Keegal','0773972418','jean0@gmail.com','Painter','077362934859','2-bedroom',11,'2026-04-12','2027-04-07',1000.0,0.0,'Active','',NULL,'2026-04-12');
INSERT INTO "tenants" VALUES(17,'AB18338949F','Jayden Doe','0773892748','jay@gmail.com','Racer','07783624793','2-bedroom',17,'2026-04-12','2027-04-07',1200.0,500.0,'Active','',NULL,'2026-04-12');
INSERT INTO "tenants" VALUES(18,'AB2737362882F','Jay Rayden','0776257826','jay@gmail.com','Racer','07782652735','2-bedroom',15,'2026-04-12','2027-04-07',100.0,100.0,'Active','',NULL,'2026-04-12');
INSERT INTO "tenants" VALUES(19,'AB6536337U','Kylie Roe','077826524729','roe@gamil.com','Racer','077927652728','2-bedroom',19,'2026-04-12','2027-04-07',-500.0,-500.0,'Active','',NULL,'2026-04-12');
INSERT INTO "tenants" VALUES(21,'AB123456I','Karen Doe','07782764218','karen@6gmail.com','Dancer','0778265183','2-bedroom',3,'2026-14-15','2026-01-25',-7.0,-7.0,'Active','',NULL,'2026-04-12');
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
INSERT INTO "users" VALUES(1,'admin_bristol','017daef6ac5d2602e9ed501a027e1e5d1f88657e37c0b4f6194f6c5cf5668a5b','Alice Morrison','Administrator','Bristol','alice@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(2,'admin_london','017daef6ac5d2602e9ed501a027e1e5d1f88657e37c0b4f6194f6c5cf5668a5b','David Okafor','Administrator','London','david@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(3,'admin_manc','017daef6ac5d2602e9ed501a027e1e5d1f88657e37c0b4f6194f6c5cf5668a5b','Fiona Walsh','Administrator','Manchester','fiona@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(4,'admin_cardiff','017daef6ac5d2602e9ed501a027e1e5d1f88657e37c0b4f6194f6c5cf5668a5b','Rhys Evans','Administrator','Cardiff','rhys@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(5,'manager','7e0e7e5b6cea4c4f4822dd6f5d39828b8f41f4f267116e2d02fa69f353dac9d3','Sarah Whitfield','Manager','Bristol','sarah@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(6,'frontdesk1','7b4cf7c10281a0aaac1411f483943146c8e9cee5729f6bf149261440502740d1','James Patel','Front-Desk Staff','Bristol','james@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(7,'frontdesk2','7b4cf7c10281a0aaac1411f483943146c8e9cee5729f6bf149261440502740d1','Lily Chen','Front-Desk Staff','Manchester','lily@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(8,'frontdesk3','7b4cf7c10281a0aaac1411f483943146c8e9cee5729f6bf149261440502740d1','Amara Diallo','Front-Desk Staff','London','amara@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(9,'frontdesk4','7b4cf7c10281a0aaac1411f483943146c8e9cee5729f6bf149261440502740d1','Sian Hughes','Front-Desk Staff','Cardiff','sian@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(10,'finance1','1c1b42ab802e26c8a9ce73afa19cfc4566db918050a24ce2aacd741e3c3a2f27','Robert Hughes','Finance Manager','Bristol','robert@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(11,'finance2','1c1b42ab802e26c8a9ce73afa19cfc4566db918050a24ce2aacd741e3c3a2f27','Natasha Peters','Finance Manager','London','natasha@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(12,'maint1','a04a6acdfb59372b3c76a4f2481c5f07a8425b3898c968151f64a2d234899d4b','Carlos Rivera','Maintenance Staff','Bristol','carlos@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(13,'maint2','a04a6acdfb59372b3c76a4f2481c5f07a8425b3898c968151f64a2d234899d4b','Priya Singh','Maintenance Staff','London','priya@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(14,'maint3','a04a6acdfb59372b3c76a4f2481c5f07a8425b3898c968151f64a2d234899d4b','Tom Bradley','Maintenance Staff','Manchester','tom@paragon.com',1,'2026-04-04');
INSERT INTO "users" VALUES(15,'maint4','a04a6acdfb59372b3c76a4f2481c5f07a8425b3898c968151f64a2d234899d4b','Kezia Mensah','Maintenance Staff','Cardiff','kezia@paragon.com',1,'2026-04-04');
CREATE INDEX idx_tenants_apt       ON tenants(apt_id);
CREATE INDEX idx_tenants_status    ON tenants(status);
CREATE INDEX idx_payments_tenant   ON payments(tenant_id);
CREATE INDEX idx_payments_status   ON payments(status);
CREATE INDEX idx_payments_due      ON payments(due_date);
CREATE INDEX idx_maint_apt         ON maintenance(apt_id);
CREATE INDEX idx_maint_status      ON maintenance(status);
CREATE INDEX idx_complaints_tenant ON complaints(tenant_id);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('locations',5);
INSERT INTO "sqlite_sequence" VALUES('users',15);
INSERT INTO "sqlite_sequence" VALUES('apartments',22);
INSERT INTO "sqlite_sequence" VALUES('tenants',21);
INSERT INTO "sqlite_sequence" VALUES('leases',21);
INSERT INTO "sqlite_sequence" VALUES('payments',83);
INSERT INTO "sqlite_sequence" VALUES('maintenance',16);
INSERT INTO "sqlite_sequence" VALUES('complaints',12);
INSERT INTO "sqlite_sequence" VALUES('audit_log',10);
COMMIT;