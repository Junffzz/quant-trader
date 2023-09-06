SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

CREATE TABLE IF NOT EXISTS `balance`(
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `broker_name` VARCHAR(60) NOT NULL,
    `broker_environment` VARCHAR(20) NOT NULL,
    `broker_account_id` int(11) NOT NULL,
    `broker_account` VARCHAR(20) NOT NULL,
    `strategy_account_id` int(11) NOT NULL,
    `strategy_account` VARCHAR(20) NOT NULL,
    `strategy_version` VARCHAR(20) NOT NULL,
    `strategy_version_desc` VARCHAR(300),
    `strategy_status` VARCHAR(15),
    `trade_market` VARCHAR(20) NOT NULL,
    `cash` float NOT NULL,
    `cash_by_currency` VARCHAR(50),
    `available_cash` float NOT NULL,
    `max_power_short` float,
    `net_cash_power` float,
    `power` float,
    `maintenance_margin` float,
    `unrealized_pnl` float,
    `realized_pnl` float,
    `update_time` datetime NOT NULL DEFAULT current_timestamp(),
    `remark` VARCHAR(300),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `position`(
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `balance_id` int(10) NOT NULL,
    `security_name` VARCHAR(60) NOT NULL,
    `security_code` VARCHAR(20) NOT NULL,
    `direction` VARCHAR(20) NOT NULL,
    `holding_price` float NOT NULL,
    `quantity` int(10) NOT NULL,
    `update_time` datetime NOT NULL DEFAULT current_timestamp(),
    `remark` VARCHAR(300),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `trading_order` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `broker_order_id` VARCHAR(50) NOT NULL,
    `balance_id` int(10) NOT NULL,
    `security_name` VARCHAR(60) NOT NULL,
    `security_code` VARCHAR(20) NOT NULL,
    `price` float NOT NULL,
    `quantity` int(10) NOT NULL,
    `direction` VARCHAR(20) NOT NULL,
    `offset` VARCHAR(20) NOT NULL,
    `order_type` VARCHAR(20) NOT NULL,
    `filled_avg_price` float NOT NULL,
    `filled_quantity` int(10) NOT NULL,
    `status` VARCHAR(20) NOT NULL,
    `remark` VARCHAR(300),
    `create_time` datetime NOT NULL DEFAULT current_timestamp(),
    `update_time` datetime NOT NULL DEFAULT current_timestamp(),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


CREATE TABLE IF NOT EXISTS `trading_deal` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `broker_deal_id` VARCHAR(50) NOT NULL,
    `broker_order_id` VARCHAR(50) NOT NULL,
    `order_id` int(11) NOT NULL,
    `balance_id` int(10) NOT NULL,
    `security_name` VARCHAR(60) NOT NULL,
    `security_code` VARCHAR(20) NOT NULL,
    `direction` VARCHAR(20) NOT NULL,
    `offset` VARCHAR(20) NOT NULL,
    `order_type` VARCHAR(20) NOT NULL,
    `filled_avg_price` float NOT NULL,
    `filled_quantity` int(10) NOT NULL,
    `remark` VARCHAR(300),
    `update_time` datetime NOT NULL DEFAULT current_timestamp(),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


CREATE TABLE IF NOT EXISTS `orders` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `broker_order_id` VARCHAR(50) NOT NULL,
    `account_id` int(10) NOT NULL DEFAULT 0,
    `strategy_name` varchar(120) NOT NULL DEFAULT '',
    `security_name` VARCHAR(60) NOT NULL,
    `security_code` VARCHAR(20) NOT NULL,
    `price` float NOT NULL,
    `quantity` int(10) NOT NULL,
    `direction` VARCHAR(20) NOT NULL,
    `offset_type` VARCHAR(20) NOT NULL,
    `order_type` VARCHAR(20) NOT NULL,
    `filled_avg_price` float NOT NULL,
    `filled_quantity` int(10) NOT NULL,
    `status` VARCHAR(20) NOT NULL,
    `remark` VARCHAR(300),
    `create_time` datetime NOT NULL DEFAULT current_timestamp(),
    `update_time` datetime NOT NULL DEFAULT current_timestamp(),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
