-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1:3306
-- Generation Time: Nov 23, 2024 at 04:38 AM
-- Server version: 8.0.31
-- PHP Version: 8.2.0

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `vsms`
--

-- --------------------------------------------------------

--
-- Table structure for table `admin`
--

DROP TABLE IF EXISTS `admin`;
CREATE TABLE IF NOT EXISTS `admin` (
  `admin_id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` text,
  PRIMARY KEY (`admin_id`)
) ENGINE=MyISAM AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `admin`
--


-- --------------------------------------------------------

--
-- Table structure for table `customer`
--

DROP TABLE IF EXISTS `customer`;
CREATE TABLE IF NOT EXISTS `customer` (
  `customer_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `password` varchar(100) NOT NULL,
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`customer_id`)
) ENGINE=MyISAM AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `customer`
--

INSERT INTO `customer` (`customer_id`, `name`, `password`, `email`) VALUES
(1, 'agney', 'admin', 'agneyanand@hotmail.com'),
(2, 'cijo', 'admin', 'cijo@gmail.com');

-- --------------------------------------------------------

--
-- Table structure for table `invoice`
--

DROP TABLE IF EXISTS `invoice`;
CREATE TABLE IF NOT EXISTS `invoice` (
  `invoice_id` int NOT NULL AUTO_INCREMENT,
  `service_id` int NOT NULL,
  `invoice_date` timestamp NOT NULL,
  `payment_status` enum('PENDING','PAID') NOT NULL,
  `total_amount` int NOT NULL,
  `description` text NOT NULL,
  PRIMARY KEY (`invoice_id`)
) ENGINE=MyISAM AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `invoice`
--

INSERT INTO `invoice` (`invoice_id`, `service_id`, `invoice_date`, `payment_status`, `total_amount`, `description`) VALUES
(3, 2, '2024-09-20 16:20:21', 'PENDING', 3900, ''),
(4, 7, '2024-09-22 11:31:11', 'PENDING', 2350, ''),
(5, 8, '2024-09-23 16:09:57', 'PENDING', 1400, ''),
(6, 9, '2024-09-23 16:53:24', 'PENDING', 2000, ''),
(7, 13, '2024-09-28 17:13:24', 'PENDING', 3000, 'INVOICE CREATED'),
(8, 14, '2024-09-28 17:25:35', 'PENDING', 13000, 'invoice created'),
(9, 16, '2024-09-29 11:16:39', 'PENDING', 5100, 'new invoice'),
(10, 38, '2024-10-22 04:29:49', 'PENDING', 0, 'awdwd');

-- --------------------------------------------------------

--
-- Table structure for table `mechanic`
--

DROP TABLE IF EXISTS `mechanic`;
CREATE TABLE IF NOT EXISTS `mechanic` (
  `mechanic_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `username` varchar(100) NOT NULL,
  `password` text NOT NULL,
  `status` enum('available','busy') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `specialization` varchar(100) NOT NULL,
  PRIMARY KEY (`mechanic_id`)
) ENGINE=MyISAM AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `mechanic`
--

INSERT INTO `mechanic` (`mechanic_id`, `name`, `username`, `password`, `status`, `specialization`) VALUES
(6, 'sangeeth', 'sangi', 'scrypt:32768:8:1$ECw1OmqE7TG0QwfD$6b8e8accbbbf11b43c626bf688b4f71f7a7913c830526a11fd5510e5c60ef442b55420bebea303c3a2952f77dd2031d39aafe8380a6fbcaaf2287cc1aead2f95', 'busy', 'main vazha'),
(10, 'cijo', 'cijo', 'scrypt:32768:8:1$5nOpTAIUoTkLzaoE$d7474b0dcf74d86db8e3685a2b5ab6d91fd1e69a9e6e91b94ffc1038da922750be3d990ff3e7990125433ed38e4647e3caf8cac049ceecf54ec74b103a301e8a', 'busy', 'tyre works'),
(11, 'navaneeth', 'navi', 'scrypt:32768:8:1$IyBCy99cyv46ufzw$b352743ee42bf6c956f4dd26f859f042c5887f1c146d1b4ed221ad82fffcb95ab4be6f961cdea2fd7219f5d3091ea670da9c2852c11a74d799885cfde3508c8e', 'busy', 'paint works');

-- --------------------------------------------------------

--
-- Table structure for table `service_cost`
--

DROP TABLE IF EXISTS `service_cost`;
CREATE TABLE IF NOT EXISTS `service_cost` (
  `cost_id` int NOT NULL AUTO_INCREMENT,
  `service_id` int NOT NULL,
  `part_name` varchar(255) DEFAULT NULL,
  `part_cost` decimal(10,2) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `status` enum('pending','accepted','rejected') DEFAULT 'pending',
  PRIMARY KEY (`cost_id`),
  KEY `service_id` (`service_id`)
) ENGINE=MyISAM AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `service_cost`
--

INSERT INTO `service_cost` (`cost_id`, `service_id`, `part_name`, `part_cost`, `description`, `status`) VALUES
(1, 2, '250.00', '450.00', 'new part', 'pending'),
(2, 2, '100.00', '100.00', 'another part', 'pending'),
(3, 7, '100.00', '200.00', 'new part\r\n', 'rejected'),
(4, 8, '100.00', '300.00', 'new wheels', 'rejected'),
(5, 7, '250.00', '600.00', 'fender', 'rejected'),
(6, 7, '100.00', '100.00', 'extra paint', 'rejected'),
(7, 9, '0.00', '0.00', 'base invoice', 'rejected'),
(8, 9, '200.00', '800.00', 'New tyres', 'rejected'),
(14, 14, 'battery', '10000.00', 'change battery', 'accepted'),
(11, 12, 'lights', '3000.00', 'headlight\r\n', 'rejected'),
(13, 13, 'engine oil', '3000.00', 'oil change', 'accepted'),
(15, 14, 'headlights', '3000.00', 'change lights', 'accepted'),
(16, 16, 'tyres', '100.00', 'tyres', 'accepted'),
(17, 16, 'battery', '5000.00', 'repair', 'accepted'),
(18, 17, 'oil change', '3000.00', 'change oil', 'accepted'),
(19, 40, 'awdd', '2000.00', 'dfdf', 'accepted'),
(20, 40, 'fsef', '1000.00', 'dfesf', 'accepted');

-- --------------------------------------------------------

--
-- Table structure for table `service_request`
--

DROP TABLE IF EXISTS `service_request`;
CREATE TABLE IF NOT EXISTS `service_request` (
  `service_id` int NOT NULL AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `mechanic_id` int DEFAULT NULL,
  `vehicle_id` int NOT NULL,
  `status` enum('pending','accepted','in-progress','completed') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'pending',
  `created_on` timestamp NOT NULL,
  `updated_on` timestamp NOT NULL,
  `description` varchar(100) NOT NULL,
  `next_service_date` date DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `assignment_status` enum('assigned','unassigned') NOT NULL DEFAULT 'unassigned',
  PRIMARY KEY (`service_id`)
) ENGINE=MyISAM AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `service_request`
--

INSERT INTO `service_request` (`service_id`, `customer_id`, `mechanic_id`, `vehicle_id`, `status`, `created_on`, `updated_on`, `description`, `next_service_date`, `location`, `assignment_status`) VALUES
(9, 1, 10, 8, 'completed', '2024-09-29 13:38:03', '2024-09-29 13:38:03', 'tyre change', '2024-11-29', NULL, 'assigned'),
(38, 1, 10, 9, 'completed', '2024-09-29 14:52:16', '0000-00-00 00:00:00', 'awdadwddd', '0000-00-00', '10.0604796, 76.3210889', 'assigned'),
(8, 1, 6, 13, 'completed', '2024-09-29 13:38:09', '2024-09-29 13:38:09', 'engine works', '2024-11-21', NULL, 'assigned'),
(34, 1, 10, 13, 'completed', '2024-09-29 13:40:12', '2024-09-29 13:40:12', 'a4', '0000-00-00', NULL, 'assigned'),
(33, 1, 11, 5, 'pending', '2024-09-29 13:40:05', '2024-09-29 13:40:05', 'a3', NULL, NULL, 'assigned'),
(13, 1, 10, 13, 'completed', '2024-09-29 13:37:55', '2024-09-29 13:37:55', 'breakdown saaaar', '2025-02-05', '10.0604742, 76.3210893', 'assigned'),
(16, 2, 6, 14, 'completed', '2024-09-29 13:38:17', '2024-09-29 13:38:17', 'breakdownn', '2025-01-31', '10.0604818, 76.3210859', 'assigned'),
(39, 1, 10, 9, 'pending', '2024-09-29 14:54:55', '2024-09-29 14:54:55', 'zx', NULL, NULL, 'assigned'),
(31, 1, 6, 8, 'pending', '2024-09-29 13:39:48', '2024-09-29 13:39:48', 'a1', NULL, NULL, 'assigned'),
(37, 1, 10, 13, 'completed', '2024-09-29 14:51:41', '2024-09-29 14:51:41', 'awdd', '0000-00-00', NULL, 'assigned'),
(40, 1, 10, 9, 'completed', '2024-10-22 04:26:09', '0000-00-00 00:00:00', 'zxcds', '0000-00-00', '10.0673997, 76.326788', 'assigned');

-- --------------------------------------------------------

--
-- Table structure for table `vehicle`
--

DROP TABLE IF EXISTS `vehicle`;
CREATE TABLE IF NOT EXISTS `vehicle` (
  `vehicle_id` int NOT NULL AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `make` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  `engine_type` varchar(100) NOT NULL,
  `reg_no` varchar(100) NOT NULL,
  `created_on` timestamp NOT NULL,
  `vehicle_image` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`vehicle_id`)
) ENGINE=MyISAM AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `vehicle`
--

INSERT INTO `vehicle` (`vehicle_id`, `customer_id`, `make`, `model`, `engine_type`, `reg_no`, `created_on`, `vehicle_image`) VALUES
(8, 1, 'benz', 's class', 'petrol', 'kl 23 22', '2024-09-09 19:04:27', 'carousel-1.png'),
(9, 1, 'dodge', 'charger', 'diesel', 'ka 23 44', '2024-09-09 19:05:12', 'img1.png'),
(5, 1, 'bmw', 'x8', 'petrol', 'kl 231 99 ', '2024-09-09 18:56:48', 'carousel-2.png'),
(14, 2, 'Tesla', 'plaid', 'petrol', 'kl 23 52', '2024-09-28 17:23:07', 'tesla-model-s.png'),
(13, 1, 'mahindra', 'thar', 'diesel', 'kl 332 ad', '2024-09-19 17:01:19', 'carousel-bg-2.jpg'),
(15, 2, 'porsche', 'turbo', 'petrol', 'kl 23 aaa', '2024-09-29 11:29:21', 'carousel-bg-1.jpg');
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
