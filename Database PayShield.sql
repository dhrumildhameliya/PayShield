-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Nov 23, 2025 at 04:52 PM
-- Server version: 10.4.28-MariaDB
-- PHP Version: 8.1.17

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `payshield`
--

-- --------------------------------------------------------

--
-- Table structure for table `admin_users`
--

CREATE TABLE `admin_users` (
  `id` int(11) NOT NULL,
  `username` varchar(100) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `is_super` tinyint(1) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `admin_users`
--

INSERT INTO `admin_users` (`id`, `username`, `email`, `password_hash`, `is_super`, `created_at`) VALUES
(3, 'SuperAdmin', 'admin@payshield.com', '$2b$12$mqbYYWBcFkj0ZxfpuGcu0eidcX0EqFYNHJLRYY3zP8DOPWm4F5A9G', 1, '2025-11-21 08:02:29');

-- --------------------------------------------------------

--
-- Table structure for table `bank_accounts`
--

CREATE TABLE `bank_accounts` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `bank_name` varchar(50) NOT NULL,
  `account_number` varchar(20) DEFAULT NULL,
  `ifsc_code` varchar(15) DEFAULT NULL,
  `debit_card_number` varchar(20) DEFAULT NULL,
  `upi_id` varchar(50) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `wallet_created` tinyint(1) DEFAULT 0,
  `wallet_created_at` timestamp NULL DEFAULT NULL,
  `wallet_balance` decimal(10,2) DEFAULT 0.00,
  `mpin_hash` varchar(255) DEFAULT NULL,
  `mpin_set_at` timestamp NULL DEFAULT NULL,
  `daily_limit` decimal(10,2) DEFAULT 50000.00,
  `monthly_limit` decimal(10,2) DEFAULT 200000.00,
  `daily_spent` decimal(10,2) DEFAULT 0.00,
  `monthly_spent` decimal(10,2) DEFAULT 0.00,
  `last_reset` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `bank_accounts`
--

INSERT INTO `bank_accounts` (`id`, `user_id`, `bank_name`, `account_number`, `ifsc_code`, `debit_card_number`, `upi_id`, `created_at`, `wallet_created`, `wallet_created_at`, `wallet_balance`, `mpin_hash`, `mpin_set_at`, `daily_limit`, `monthly_limit`, `daily_spent`, `monthly_spent`, `last_reset`) VALUES
(1, 9, '', 'AC3318945445', 'PYSDJBDMAUB', '8158962793553331', 'user9@payshield', '2025-10-10 09:04:01', 1, '2025-11-03 07:02:13', 10000.00, NULL, NULL, 50000.00, 200000.00, 0.00, 0.00, NULL),
(26, 21, 'IDFC First Bank', '2222222222', 'SBIN0001234', '2222222222222222', 'user21@payshield', '2025-11-08 06:11:35', 1, '2025-11-08 00:43:02', 12261.00, 'scrypt:32768:8:1$T4803RbADOS7H4N6$c160ca7835c99d550990aca8495fe866b6de8e425902c3150df49ef2ca882aee9f893cc0418198c5e2849a72e0fc32ae26c264cffdf32878b451ccc3e25b2a8e', '2025-11-08 06:09:47', 50000.00, 200000.00, 0.00, 0.00, NULL),
(30, 24, 'State Bank of India', '1111111111', 'SBIN0001234', '1111111111111111', 'user24@payshield', '2025-11-16 12:56:56', 1, '2025-11-16 07:29:02', 973000.00, 'scrypt:32768:8:1$j7Tgfiw0CUggvH3Q$e088bcc20d21c6467b1a2c6589031331be7764b71faa8ce1b32380262e7c224332f4f77a075e802f2e6c38d7f81889c253951e508257d2fe8b5708e0796181d7', '2025-11-16 07:31:11', 50000.00, 200000.00, 28901.00, 0.00, '2025-11-21'),
(31, 15, 'IDFC First Bank', '333333333333', 'SBIN0004521', '3030303030303030', 'user15@payshield', '2025-11-23 08:25:46', 1, '2025-11-23 03:01:37', 7998.00, 'scrypt:32768:8:1$CLMZoDdIgaiAdS1e$cb7fb57370f422d743210b2a9562a88214ac49ce4a06e9e95141259da70b9cbff0f985b9e0b8c3a1c557c44193f59165e1c8f1493a14a1e13ba55cbd904e2d0f', '2025-11-23 03:03:07', 50000.00, 200000.00, 0.00, 0.00, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `otp_logs`
--

CREATE TABLE `otp_logs` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `otp_code` varchar(6) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `expires_at` datetime NOT NULL,
  `is_used` tinyint(1) DEFAULT 0,
  `action_type` enum('LOGIN','RISK_TX','BANK_VERIFY') DEFAULT 'LOGIN'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `otp_logs`
--

INSERT INTO `otp_logs` (`id`, `user_id`, `otp_code`, `created_at`, `expires_at`, `is_used`, `action_type`) VALUES
(1, 21, '537796', '2025-11-08 11:37:30', '2025-11-08 17:12:30', 1, 'LOGIN'),
(3, 24, '677757', '2025-11-16 12:37:04', '2025-11-16 18:12:04', 1, 'LOGIN'),
(4, 24, '636189', '2025-11-17 05:53:09', '2025-11-17 11:28:09', 1, 'LOGIN'),
(5, 24, '894313', '2025-11-17 06:05:25', '2025-11-17 11:40:25', 1, 'LOGIN'),
(6, 24, '926499', '2025-11-17 06:12:50', '2025-11-17 11:47:50', 1, 'LOGIN'),
(7, 24, '382181', '2025-11-21 05:17:10', '2025-11-21 10:52:10', 1, 'LOGIN'),
(8, 24, '515894', '2025-11-21 05:18:51', '2025-11-21 05:21:51', 1, 'RISK_TX'),
(9, 24, '387126', '2025-11-21 05:40:11', '2025-11-21 05:43:11', 0, 'RISK_TX'),
(10, 24, '662824', '2025-11-21 05:41:36', '2025-11-21 05:44:36', 1, 'RISK_TX'),
(11, 21, '561920', '2025-11-21 11:48:05', '2025-11-21 17:23:05', 1, 'LOGIN'),
(12, 15, '722738', '2025-11-22 12:56:50', '2025-11-22 18:31:50', 0, 'LOGIN'),
(13, 15, '459629', '2025-11-22 13:23:27', '2025-11-22 18:58:27', 1, 'LOGIN'),
(14, 15, '401054', '2025-11-23 08:14:25', '2025-11-23 13:49:25', 1, 'LOGIN');

-- --------------------------------------------------------

--
-- Table structure for table `risk_transactions`
--

CREATE TABLE `risk_transactions` (
  `id` int(11) NOT NULL,
  `from_user_id` int(11) NOT NULL,
  `to_user_id` int(11) NOT NULL,
  `to_upi` varchar(50) NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `note` text DEFAULT NULL,
  `status` enum('PENDING','EXPIRED','APPROVED','REJECTED') DEFAULT 'PENDING',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `risk_transactions`
--

INSERT INTO `risk_transactions` (`id`, `from_user_id`, `to_user_id`, `to_upi`, `amount`, `note`, `status`, `created_at`) VALUES
(1, 24, 15, 'user15@payshield', 300.00, '', 'APPROVED', '2025-11-21 05:18:51'),
(2, 24, 15, 'user15@payshield', 25000.00, '', 'PENDING', '2025-11-21 05:40:11'),
(3, 24, 15, 'user15@payshield', 25000.00, '', 'APPROVED', '2025-11-21 05:41:36');

-- --------------------------------------------------------

--
-- Table structure for table `security_logs`
--

CREATE TABLE `security_logs` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `event_type` varchar(50) NOT NULL,
  `ip_address` varchar(50) DEFAULT NULL,
  `device_info` text DEFAULT NULL,
  `risk_score` int(11) DEFAULT 0,
  `timestamp` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `security_logs`
--

INSERT INTO `security_logs` (`id`, `user_id`, `event_type`, `ip_address`, `device_info`, `risk_score`, `timestamp`) VALUES
(1, 24, 'FRAUD_CHECK_OTP_REQUIRED', '198.0.0.2', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, '2025-11-21 05:18:51'),
(2, 24, 'FRAUD_CHECK_ALLOW', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 0, '2025-11-21 05:22:21'),
(3, 24, 'FRAUD_CHECK_ALLOW', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 0, '2025-11-21 05:36:26'),
(4, 24, 'FRAUD_CHECK_OTP_REQUIRED', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 2, '2025-11-21 05:40:11'),
(5, 24, 'FRAUD_CHECK_OTP_REQUIRED', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 2, '2025-11-21 05:41:36'),
(6, 24, 'MPIN_FAIL', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 5, '2025-11-21 05:43:10'),
(7, 24, 'MPIN_FAIL', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 5, '2025-11-21 05:43:13'),
(8, 24, 'MPIN_FAIL', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 5, '2025-11-21 05:43:17'),
(9, 24, 'MPIN_FAIL', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 5, '2025-11-21 05:43:21'),
(10, 24, 'MPIN_FAIL', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 5, '2025-11-21 05:43:26'),
(11, 24, 'MPIN_FAIL', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 5, '2025-11-21 05:43:30'),
(12, 24, 'MPIN_FAIL', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 5, '2025-11-21 05:43:34'),
(13, 24, 'DAILY_LIMIT_EXCEEDED', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 8, '2025-11-21 05:43:38'),
(14, 24, 'DAILY_LIMIT_EXCEEDED', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 8, '2025-11-21 05:43:43'),
(15, 24, 'DAILY_LIMIT_EXCEEDED', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 8, '2025-11-21 05:43:51'),
(16, 24, 'DAILY_LIMIT_EXCEEDED', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 8, '2025-11-21 05:44:00'),
(17, 24, 'DAILY_LIMIT_EXCEEDED', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 8, '2025-11-21 05:44:08'),
(18, 24, 'MPIN_FAIL', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 5, '2025-11-21 05:44:12'),
(19, 24, 'DAILY_LIMIT_EXCEEDED', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 8, '2025-11-21 05:44:20'),
(20, 24, 'FRAUD_CHECK_ALLOW', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 0, '2025-11-21 05:47:30');

-- --------------------------------------------------------

--
-- Table structure for table `transactions`
--

CREATE TABLE `transactions` (
  `id` int(11) NOT NULL,
  `tx_id` varchar(32) NOT NULL,
  `from_user_id` int(11) DEFAULT NULL,
  `to_user_id` int(11) DEFAULT NULL,
  `to_upi` varchar(100) DEFAULT NULL,
  `amount` decimal(10,2) NOT NULL,
  `note` varchar(255) DEFAULT NULL,
  `status` enum('SUCCESS','FAILED') DEFAULT 'SUCCESS',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `transactions`
--

INSERT INTO `transactions` (`id`, `tx_id`, `from_user_id`, `to_user_id`, `to_upi`, `amount`, `note`, `status`, `created_at`) VALUES
(0, '426edcda429c4cf0bf78', 24, 15, 'user15@payshield', 3001.00, 'Rent', 'SUCCESS', '2025-11-16 13:32:51'),
(0, '9dba8f1a6053480c90e0', 24, 15, 'user15@payshield', 3001.00, 'Rent', 'SUCCESS', '2025-11-16 13:35:56'),
(0, 'aac9e32995f34224a8c7', 24, 15, 'user15@payshield', 3001.00, 'Rent', 'SUCCESS', '2025-11-17 06:13:40'),
(0, '0f8dcc2e78634cc78259', 21, 15, 'user15@payshield', 30000.00, '', 'SUCCESS', '2025-11-21 11:49:00'),
(0, 'a1030b6f455544d0ba25', 15, 24, 'user24@payshield', 30000.00, '', 'SUCCESS', '2025-11-22 13:29:57'),
(0, '596888f6cdfd44d884a3', 15, 24, 'user24@payshield', 1001.00, '', 'SUCCESS', '2025-11-23 08:44:24'),
(0, '4d6f02f8797a461bbc60', 15, 21, 'user21@payshield', 1001.00, 'AAVYAAA', 'SUCCESS', '2025-11-23 08:46:42');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(30) DEFAULT NULL,
  `email` varchar(255) NOT NULL,
  `mobileno` varchar(15) DEFAULT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `device_fingerprint` text DEFAULT NULL,
  `last_login_ip` varchar(50) DEFAULT NULL,
  `failed_attempts` int(11) DEFAULT 0,
  `last_mpin_update` timestamp NULL DEFAULT NULL,
  `is_blocked` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `username`, `email`, `mobileno`, `password`, `created_at`, `device_fingerprint`, `last_login_ip`, `failed_attempts`, `last_mpin_update`, `is_blocked`) VALUES
(9, 'yagnik sakhiya', 'yagniksakhiya777@gmail.com', '1231314256', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', '2025-10-09 10:51:08', NULL, NULL, 0, NULL, 0),
(15, 'DHRUMIL DHAMELIYA', 'dhrumildhameliya789@gmail.com', '8160040291', 'bcb15f821479b4d5772bd0ca866c00ad5f926e3580720659cc80d39c9d09802a', '2025-10-30 08:57:19', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', '127.0.0.1', 0, NULL, 1),
(21, 'sakhiya yagnik', 'sakhiyayagnik7@gmail.com', '9876543212', 'bcb15f821479b4d5772bd0ca866c00ad5f926e3580720659cc80d39c9d09802a', '2025-11-08 06:10:21', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', '127.0.0.1', 0, NULL, 1),
(24, 'Dhameliya Dhrumil', 'dhrumildhameliy@gmail.com', '8160040291', 'bcb15f821479b4d5772bd0ca866c00ad5f926e3580720659cc80d39c9d09802a', '2025-11-16 12:31:21', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', '127.0.0.1', 0, NULL, 0);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `admin_users`
--
ALTER TABLE `admin_users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indexes for table `bank_accounts`
--
ALTER TABLE `bank_accounts`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `account_number` (`account_number`),
  ADD UNIQUE KEY `debit_card_number` (`debit_card_number`),
  ADD UNIQUE KEY `upi_id` (`upi_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `otp_logs`
--
ALTER TABLE `otp_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `risk_transactions`
--
ALTER TABLE `risk_transactions`
  ADD PRIMARY KEY (`id`),
  ADD KEY `from_user_id` (`from_user_id`),
  ADD KEY `to_user_id` (`to_user_id`);

--
-- Indexes for table `security_logs`
--
ALTER TABLE `security_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `admin_users`
--
ALTER TABLE `admin_users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `bank_accounts`
--
ALTER TABLE `bank_accounts`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=32;

--
-- AUTO_INCREMENT for table `otp_logs`
--
ALTER TABLE `otp_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;

--
-- AUTO_INCREMENT for table `risk_transactions`
--
ALTER TABLE `risk_transactions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `security_logs`
--
ALTER TABLE `security_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=21;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=26;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `bank_accounts`
--
ALTER TABLE `bank_accounts`
  ADD CONSTRAINT `bank_accounts_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);

--
-- Constraints for table `otp_logs`
--
ALTER TABLE `otp_logs`
  ADD CONSTRAINT `otp_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `risk_transactions`
--
ALTER TABLE `risk_transactions`
  ADD CONSTRAINT `risk_transactions_ibfk_1` FOREIGN KEY (`from_user_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `risk_transactions_ibfk_2` FOREIGN KEY (`to_user_id`) REFERENCES `users` (`id`);

--
-- Constraints for table `security_logs`
--
ALTER TABLE `security_logs`
  ADD CONSTRAINT `security_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
