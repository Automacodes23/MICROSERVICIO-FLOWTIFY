-- Backup de tabla units
-- Fecha: 2025-11-05T10:00:53.248801

CREATE TABLE `units` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `floatify_unit_id` varchar(255) NOT NULL,
  `wialon_unit_id` varchar(255) DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `plates` varchar(20) DEFAULT NULL,
  `wialon_id` varchar(50) DEFAULT NULL,
  `plate` varchar(50) DEFAULT NULL,
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`metadata`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `floatify_unit_id` (`floatify_unit_id`),
  UNIQUE KEY `idx_units_wialon_id` (`wialon_id`),
  KEY `idx_floatify_unit` (`floatify_unit_id`),
  KEY `idx_wialon_unit` (`wialon_unit_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
