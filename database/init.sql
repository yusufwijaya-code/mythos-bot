-- ==========================================
-- Bot Trading Mythos - Database Schema
-- ==========================================

CREATE DATABASE IF NOT EXISTS bot_trading_mythos
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE bot_trading_mythos;

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    side ENUM('BUY', 'SELL') NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    total DECIMAL(20, 8) NOT NULL,
    fee DECIMAL(20, 8) DEFAULT 0,
    pnl DECIMAL(20, 8) DEFAULT NULL,
    pnl_pct DECIMAL(10, 4) DEFAULT NULL,
    mode ENUM('paper', 'live') NOT NULL DEFAULT 'paper',
    order_id VARCHAR(100) DEFAULT NULL,
    strategy VARCHAR(50) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pair (pair),
    INDEX idx_created_at (created_at),
    INDEX idx_mode (mode)
) ENGINE=InnoDB;

-- Signals table
CREATE TABLE IF NOT EXISTS signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    action ENUM('BUY', 'SELL', 'HOLD') NOT NULL,
    confidence DECIMAL(5, 2) DEFAULT NULL,
    indicators JSON DEFAULT NULL,
    executed TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pair_action (pair, action),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- Positions table
CREATE TABLE IF NOT EXISTS positions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    side ENUM('LONG', 'SHORT') NOT NULL DEFAULT 'LONG',
    entry_price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8) DEFAULT NULL,
    unrealized_pnl DECIMAL(20, 8) DEFAULT 0,
    stop_loss DECIMAL(20, 8) DEFAULT NULL,
    take_profit DECIMAL(20, 8) DEFAULT NULL,
    trailing_stop DECIMAL(20, 8) DEFAULT NULL,
    status ENUM('open', 'closed') NOT NULL DEFAULT 'open',
    mode ENUM('paper', 'live') NOT NULL DEFAULT 'paper',
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP NULL DEFAULT NULL,
    INDEX idx_pair_status (pair, status),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_type ENUM('daily', 'weekly') NOT NULL,
    report_date DATE NOT NULL,
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    net_profit DECIMAL(20, 8) DEFAULT 0,
    gross_profit DECIMAL(20, 8) DEFAULT 0,
    gross_loss DECIMAL(20, 8) DEFAULT 0,
    profit_factor DECIMAL(10, 4) DEFAULT 0,
    max_drawdown DECIMAL(10, 4) DEFAULT 0,
    mode ENUM('paper', 'live') NOT NULL DEFAULT 'paper',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_report (report_type, report_date, mode),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB;

-- Log entries table
CREATE TABLE IF NOT EXISTS log_entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level VARCHAR(10) NOT NULL DEFAULT 'INFO',
    module VARCHAR(50) DEFAULT NULL,
    message TEXT NOT NULL,
    details JSON DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_level (level),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- Bot settings table
CREATE TABLE IF NOT EXISTS bot_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(50) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Authorized users table (for Google OAuth access control)
CREATE TABLE IF NOT EXISTS authorized_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) DEFAULT NULL,
    role ENUM('admin', 'viewer') NOT NULL DEFAULT 'admin',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    last_login TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_active (is_active)
) ENGINE=InnoDB;

-- Insert default bot settings
INSERT INTO bot_settings (setting_key, setting_value) VALUES
    ('bot_active', 'false'),
    ('strategy_active', 'true'),
    ('trading_mode', 'paper')
ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);

-- Insert default authorized user
INSERT INTO authorized_users (email, name, role) VALUES
    ('yusufwijaya3@gmail.com', 'Yusuf Wijaya', 'admin')
ON DUPLICATE KEY UPDATE name = VALUES(name);
