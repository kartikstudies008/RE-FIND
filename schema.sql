-- ==========================================================
-- ReFind AI – Intelligent Lost & Found Matching Platform
-- Database Schema for MySQL 8.0+
-- ==========================================================

CREATE DATABASE IF NOT EXISTS `refind_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `refind_db`;

-- Drop existing tables if re-initializing
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `reports`;
DROP TABLE IF EXISTS `matches`;
DROP TABLE IF EXISTS `items`;
DROP TABLE IF EXISTS `users`;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. Users Table
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(120) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `phone` VARCHAR(20) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('USER', 'ADMIN') NOT NULL DEFAULT 'USER',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_users_email` (`email`),
    INDEX `idx_users_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Items Table
CREATE TABLE `items` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `type` ENUM('lost', 'found') NOT NULL,
    `item_name` VARCHAR(150) NOT NULL,
    `category` VARCHAR(60) NOT NULL,
    `description` TEXT NOT NULL,
    `color` VARCHAR(60) NULL,
    `brand` VARCHAR(80) NULL,
    `location` VARCHAR(255) NOT NULL,
    `date` DATE NOT NULL,
    `time` TIME NULL,
    `image_path` VARCHAR(255) NULL,
    `status` ENUM('active', 'matched', 'resolved') NOT NULL DEFAULT 'active',
    `is_flagged` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_items_type` (`type`),
    INDEX `idx_items_category` (`category`),
    INDEX `idx_items_status` (`status`),
    INDEX `idx_items_date` (`date`),
    INDEX `idx_items_location` (`location`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Matches Table
CREATE TABLE `matches` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `lost_item_id` INT NOT NULL,
    `found_item_id` INT NOT NULL,
    `match_score` FLOAT NOT NULL,
    `category_score` FLOAT NOT NULL DEFAULT 0.0,
    `location_score` FLOAT NOT NULL DEFAULT 0.0,
    `date_score` FLOAT NOT NULL DEFAULT 0.0,
    `color_score` FLOAT NOT NULL DEFAULT 0.0,
    `brand_score` FLOAT NOT NULL DEFAULT 0.0,
    `description_score` FLOAT NOT NULL DEFAULT 0.0,
    `status` ENUM('suggested', 'accepted', 'rejected') NOT NULL DEFAULT 'suggested',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`lost_item_id`) REFERENCES `items`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`found_item_id`) REFERENCES `items`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `unique_pair` (`lost_item_id`, `found_item_id`),
    INDEX `idx_matches_score` (`match_score`),
    INDEX `idx_matches_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Reports Table
CREATE TABLE `reports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `item_id` INT NOT NULL,
    `reported_by` INT NOT NULL,
    `reason` TEXT NOT NULL,
    `status` ENUM('pending', 'reviewed') NOT NULL DEFAULT 'pending',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`item_id`) REFERENCES `items`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`reported_by`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_reports_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Notifications Table
CREATE TABLE `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `message` TEXT NOT NULL,
    `link` VARCHAR(255) NULL,
    `is_read` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_notif_user` (`user_id`, `is_read`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
