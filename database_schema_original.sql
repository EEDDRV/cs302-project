CREATE DATABASE IF NOT EXISTS PromptPlatoon
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE PromptPlatoon;

-- 1. Customer Table
CREATE TABLE Customer (
    CustomerID INT AUTO_INCREMENT PRIMARY KEY,
    OrganizationName VARCHAR(100) NOT NULL,
    Status VARCHAR(20) DEFAULT 'ACTIVE',
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. User Table
-- Use "Users" instead of "User" to avoid reserved-word issues in many DBs
CREATE TABLE Users (
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    UserName VARCHAR(50) NOT NULL UNIQUE,
    Email VARCHAR(100) NOT NULL UNIQUE,
    PasswordHash CHAR(60) NOT NULL,
    FirstName VARCHAR(50),
    LastName VARCHAR(50),
    IsActive BOOLEAN DEFAULT TRUE,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    CustomerID INT,
    CONSTRAINT fk_users_customer
        FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID)
        ON DELETE SET NULL
);

-- 3. Role Table
CREATE TABLE Role (
    RoleID INT AUTO_INCREMENT PRIMARY KEY,
    RoleName VARCHAR(50) NOT NULL UNIQUE,
    Description TEXT
);

-- 4. UserRole Junction Table
CREATE TABLE UserRole (
    UserID INT NOT NULL,
    RoleID INT NOT NULL,
    AssignedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (UserID, RoleID),
    CONSTRAINT fk_userrole_user
        FOREIGN KEY (UserID) REFERENCES Users(UserID)
        ON DELETE CASCADE,
    CONSTRAINT fk_userrole_role
        FOREIGN KEY (RoleID) REFERENCES Role(RoleID)
        ON DELETE CASCADE
);

-- 5. API_Key Table
CREATE TABLE API_Key (
    KeyID INT AUTO_INCREMENT PRIMARY KEY,
    BearerTokenHash VARCHAR(255) NOT NULL UNIQUE,
    KeyName VARCHAR(50) DEFAULT 'Primary Key',
    IsActive BOOLEAN DEFAULT TRUE,
    MonthlyQuota INT DEFAULT 1000,
    RateLimitPerMin INT DEFAULT 120,
    ExpiresAt DATETIME,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    CustomerID INT NOT NULL,
    CONSTRAINT fk_api_key_customer
        FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID)
        ON DELETE CASCADE
);

-- 6. CaptchaType Table
CREATE TABLE CaptchaType (
    TypeCode VARCHAR(50) PRIMARY KEY,
    TypeName VARCHAR(100) NOT NULL,
    InputFormat VARCHAR(30) NOT NULL DEFAULT 'IMAGE_BASE64',
    IsSupported BOOLEAN DEFAULT TRUE,
    Description TEXT
);

-- 7. AI_Model Table
CREATE TABLE AI_Model (
    Model_ID INT AUTO_INCREMENT PRIMARY KEY,
    ModelName VARCHAR(100) NOT NULL,
    Version VARCHAR(20) NOT NULL,
    Framework VARCHAR(50) DEFAULT 'PyTorch',
    ArtifactLocation VARCHAR(255) NOT NULL,
    IsActive BOOLEAN DEFAULT TRUE,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 8. SolverAdapter Table
CREATE TABLE SolverAdapter (
    SolverID INT AUTO_INCREMENT PRIMARY KEY,
    AdapterName VARCHAR(100) NOT NULL,
    ProvidesConfidence BOOLEAN DEFAULT TRUE,
    IsActive BOOLEAN DEFAULT TRUE,
    TypeCode VARCHAR(50) NOT NULL,
    Model_ID INT NOT NULL,
    CONSTRAINT fk_solveradapter_type
        FOREIGN KEY (TypeCode) REFERENCES CaptchaType(TypeCode)
        ON DELETE CASCADE,
    CONSTRAINT fk_solveradapter_model
        FOREIGN KEY (Model_ID) REFERENCES AI_Model(Model_ID)
        ON DELETE CASCADE
);

-- 9. SolvingRequest Table
CREATE TABLE SolvingRequest (
    RequestID BIGINT AUTO_INCREMENT PRIMARY KEY,
    CaptchaContentPayload LONGTEXT NOT NULL,
    PredictedSolution VARCHAR(255),
    Confidence DECIMAL(5,4),
    ProcessingTimeMs INT,
    Status VARCHAR(30) NOT NULL,
    ErrorMessage TEXT,
    RequestedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    CustomerID INT NOT NULL,
    KeyID INT NOT NULL,
    DeclaredTypeCode VARCHAR(50) NOT NULL,
    SolverID INT,
    CONSTRAINT fk_solvingrequest_customer
        FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID)
        ON DELETE CASCADE,
    CONSTRAINT fk_solvingrequest_key
        FOREIGN KEY (KeyID) REFERENCES API_Key(KeyID)
        ON DELETE CASCADE,
    CONSTRAINT fk_solvingrequest_type
        FOREIGN KEY (DeclaredTypeCode) REFERENCES CaptchaType(TypeCode)
        ON DELETE CASCADE,
    CONSTRAINT fk_solvingrequest_solver
        FOREIGN KEY (SolverID) REFERENCES SolverAdapter(SolverID)
        ON DELETE SET NULL
);

-- 10. UsageBatch Table
CREATE TABLE UsageBatch (
    BatchID INT AUTO_INCREMENT PRIMARY KEY,
    ChallengeCount INT DEFAULT 100,
    Status VARCHAR(30) DEFAULT 'COMPLETED',
    BatchStartedAt DATETIME NOT NULL,
    BatchCompletedAt DATETIME NOT NULL,
    TotalProcessingTimeMs BIGINT NOT NULL,
    CustomerID INT NOT NULL,
    CONSTRAINT fk_usagebatch_customer
        FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID)
        ON DELETE CASCADE
);

-- 11. SystemAuditLog Table
CREATE TABLE SystemAuditLog (
    LogID BIGINT AUTO_INCREMENT PRIMARY KEY,
    EventType VARCHAR(50) NOT NULL,
    Severity VARCHAR(20) DEFAULT 'INFO',
    Details TEXT NOT NULL,
    IPAddress VARCHAR(45),
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    CustomerID INT,
    UserID INT,
    CONSTRAINT fk_auditlog_customer
        FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID)
        ON DELETE SET NULL,
    CONSTRAINT fk_auditlog_user
        FOREIGN KEY (UserID) REFERENCES Users(UserID)
        ON DELETE SET NULL
);