-- ============================================================
-- MTH GATE - MariaDB / MySQL Database Schema (Production v1.2)
-- ============================================================

CREATE DATABASE IF NOT EXISTS `mth_gate` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `mth_gate`;

-- ------------------------------------------------------------
-- Table: users (เจ้าหน้าที่และผู้ได้รับสิทธิ์)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `name` VARCHAR(255) NOT NULL,
  `role` VARCHAR(255) DEFAULT 'เจ้าหน้าที่รักษาความปลอดภัย',
  `pin` VARCHAR(10) NOT NULL,
  `token` VARCHAR(128) NOT NULL UNIQUE,
  `status` VARCHAR(20) DEFAULT 'active',
  `device_id` VARCHAR(255) DEFAULT NULL,
  `max_devices` INT DEFAULT 1,
  `created_at` VARCHAR(50) DEFAULT NULL,
  `updated_at` VARCHAR(50) DEFAULT NULL,
  `last_used` VARCHAR(50) DEFAULT NULL,
  INDEX `idx_token` (`token`),
  INDEX `idx_pin` (`pin`),
  INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Table: user_devices (รายการอุปกรณ์ที่ลงทะเบียนใช้งานของแต่ละคน)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_devices` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` VARCHAR(64) NOT NULL,
  `device_id` VARCHAR(255) NOT NULL,
  `device_name` VARCHAR(255) DEFAULT 'อุปกรณ์มือถือ',
  `status` VARCHAR(20) DEFAULT 'active',
  `registered_at` VARCHAR(50) DEFAULT NULL,
  `last_used` VARCHAR(50) DEFAULT NULL,
  UNIQUE KEY `user_device_unique` (`user_id`, `device_id`),
  INDEX `idx_user_device_status` (`user_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Table: events (ประวัติการกดเปิดไม้กั้น & Log)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `events` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `time` VARCHAR(50) NOT NULL,
  `user_name` VARCHAR(255) NOT NULL,
  `action` VARCHAR(100) NOT NULL,
  `status` VARCHAR(50) NOT NULL,
  `detail` TEXT DEFAULT NULL,
  `user_id` VARCHAR(64) DEFAULT NULL,
  INDEX `idx_time` (`time`),
  INDEX `idx_user_name` (`user_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
