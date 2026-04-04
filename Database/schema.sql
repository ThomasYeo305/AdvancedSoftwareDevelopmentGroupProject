-- Active: 1739448589890@@127.0.0.1@3306@ASDGP_PAMS

CREATE DATABASE IF NOT EXISTS ASDGP_PAMS;
USE ASDGP_PAMS;

-- 1. LOCATIONS TABLE (Parent to many tables)
CREATE TABLE Locations (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(50) NOT NULL,
    address VARCHAR(255) NOT NULL,
    manager_id CHAR(36), -- Link to Users (will add constraint later)
    phone VARCHAR(15),
    operating_hours VARCHAR(100)
);

-- 2. USERS TABLE
CREATE TABLE Users (
    user_id CHAR(36) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    role ENUM('FRONTDESK', 'FINANCE', 'MAINTENANCE', 'ADMIN', 'MANAGER'),
    is_active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    location_id INT,
    CONSTRAINT fk_user_location FOREIGN KEY (location_id) REFERENCES Locations(location_id)
);

-- Now link Locations manager_id to Users
ALTER TABLE Locations ADD CONSTRAINT fk_location_manager FOREIGN KEY (manager_id) REFERENCES Users(user_id);

-- 3. APARTMENTS TABLE
CREATE TABLE Apartments (
    apartment_id INT AUTO_INCREMENT PRIMARY KEY,
    location_id INT NOT NULL,
    apartment_number VARCHAR(20) NOT NULL,
    building_name VARCHAR(100),
    apartment_type ENUM('STUDIO', '1BED', '2BED', '3BED', 'COMMERCIAL'),
    monthly_rent DECIMAL(10,2) NOT NULL,
    rooms INT,
    bathrooms DECIMAL(2,1),
    CONSTRAINT fk_apartment_location FOREIGN KEY (location_id) REFERENCES Locations(location_id)
);

-- 4. TENANTS TABLE
CREATE TABLE Tenants (
    tenant_id CHAR(36) PRIMARY KEY,
    ni_number VARCHAR(12) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    email VARCHAR(100) NOT NULL,
    occupation VARCHAR(100),
    references_text TEXT,
    apartment_id INT NULL,
    status ENUM('ACTIVE', 'INACTIVE', 'ARCHIVED'),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by CHAR(36),
    CONSTRAINT fk_tenant_apartment FOREIGN KEY (apartment_id) REFERENCES Apartments(apartment_id),
    CONSTRAINT fk_tenant_creator FOREIGN KEY (created_by) REFERENCES Users(user_id)
);

-- 5. LEASES TABLE
CREATE TABLE Leases (
    lease_id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    apartment_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    monthly_rent DECIMAL(10,2) NOT NULL,
    deposit DECIMAL(10,2) NOT NULL,
    status ENUM('ACTIVE', 'TERMINATED_EARLY', 'EXPIRED', 'ARCHIVED'),
    early_termination_date DATE NULL,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lease_tenant FOREIGN KEY (tenant_id) REFERENCES Tenants(tenant_id),
    CONSTRAINT fk_lease_apartment FOREIGN KEY (apartment_id) REFERENCES Apartments(apartment_id)
);

-- 6. INVOICES TABLE
CREATE TABLE Invoices (
    invoice_id CHAR(36) PRIMARY KEY,
    apartment_id INT,
    tenant_id CHAR(36),
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status ENUM('PENDING', 'PAID', 'OVERDUE', 'CANCELLED'),
    location_id INT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invoice_apt FOREIGN KEY (apartment_id) REFERENCES Apartments(apartment_id),
    CONSTRAINT fk_invoice_tenant FOREIGN KEY (tenant_id) REFERENCES Tenants(tenant_id),
    CONSTRAINT fk_invoice_location FOREIGN KEY (location_id) REFERENCES Locations(location_id)
);

-- 7. PAYMENTS TABLE
CREATE TABLE Payments (
    payment_id CHAR(36) PRIMARY KEY,
    invoice_id CHAR(36),
    tenant_id CHAR(36),
    amount DECIMAL(10,2) NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_invoice FOREIGN KEY (invoice_id) REFERENCES Invoices(invoice_id),
    CONSTRAINT fk_payment_tenant FOREIGN KEY (tenant_id) REFERENCES Tenants(tenant_id)
);

-- 8. MAINTENANCE WORKERS TABLE
CREATE TABLE MaintenanceWorkers (
    worker_id CHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    email VARCHAR(100),
    availability_status ENUM('AVAILABLE', 'BUSY', 'ON_LEAVE'),
    specialization VARCHAR(100),
    location_id INT,
    CONSTRAINT fk_worker_location FOREIGN KEY (location_id) REFERENCES Locations(location_id)
);

-- 9. MAINTENANCE REQUESTS TABLE
CREATE TABLE MaintenanceRequests (
    request_id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36),
    apartment_id INT,
    issue_description TEXT NOT NULL,
    priority_level ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'),
    status ENUM('REPORTED', 'ASSIGNED', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED'),
    reported_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_worker_id CHAR(36) NULL,
    scheduled_date DATE NULL,
    completed_date DATE NULL,
    resolution_notes TEXT NULL,
    cost DECIMAL(10,2) NULL,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_maint_tenant FOREIGN KEY (tenant_id) REFERENCES Tenants(tenant_id),
    CONSTRAINT fk_maint_apt FOREIGN KEY (apartment_id) REFERENCES Apartments(apartment_id),
    CONSTRAINT fk_maint_worker FOREIGN KEY (assigned_worker_id) REFERENCES MaintenanceWorkers(worker_id)
);

-- 10. AUDIT LOG TABLE (For Security/Non-functional requirements)
CREATE TABLE AuditLog (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    old_value TEXT NULL,
    new_value TEXT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(15),
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
);
