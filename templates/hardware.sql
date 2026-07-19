-- ============================================================
-- Hardware Database Schema + Seed Data
-- Generated: 2026-07-18
-- PostgreSQL Compatible
-- ============================================================

-- ============================================================
-- ENUMS
-- ============================================================

DO $$ BEGIN
    CREATE TYPE hardware_category AS ENUM (
        'CPU', 'GPU', 'Motherboard', 'RAM', 'SSD', 'PSU', 'Cooler', 'Case', 'Fan'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ============================================================
-- TABLE: cpus
-- ============================================================

CREATE TABLE IF NOT EXISTS cpus (
    id                  SERIAL PRIMARY KEY,
    name                TEXT        NOT NULL UNIQUE,
    cores               SMALLINT    NOT NULL,
    threads             SMALLINT    NOT NULL,
    base_clock_ghz      NUMERIC(4,2) NOT NULL,
    boost_clock_ghz     NUMERIC(4,2),
    tdp_watts           SMALLINT    NOT NULL,
    graphics_model      TEXT,
    graphics_cores      SMALLINT,
    cooler_included     TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  cpus IS 'Desktop CPU catalogue';
COMMENT ON COLUMN cpus.base_clock_ghz  IS 'Base frequency in GHz';
COMMENT ON COLUMN cpus.boost_clock_ghz IS 'Maximum boost frequency in GHz; NULL when not specified';
COMMENT ON COLUMN cpus.graphics_cores  IS 'Integrated GPU compute units / shader cores; NULL = discrete-only';

-- ============================================================
-- TABLE: gpus
-- ============================================================

CREATE TABLE IF NOT EXISTS gpus (
    id                      SERIAL PRIMARY KEY,
    name                    TEXT        NOT NULL UNIQUE,
    compute_units           SMALLINT    NOT NULL,
    ray_accelerators        SMALLINT,
    ai_accelerators         SMALLINT,
    game_clock_mhz          SMALLINT,
    infinity_cache_mb       SMALLINT,
    vram_gb                 SMALLINT    NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  gpus IS 'Desktop GPU catalogue (AMD Radeon)';
COMMENT ON COLUMN gpus.game_clock_mhz      IS 'Typical game clock in MHz; NULL when not published';
COMMENT ON COLUMN gpus.infinity_cache_mb   IS 'On-die Infinity Cache in MB';
COMMENT ON COLUMN gpus.ai_accelerators     IS 'AI Accelerator count (RDNA 4+); NULL for older architectures';

-- ============================================================
-- SEED: Ryzen 9000-series CPUs  (AM5 / Granite Ridge / Strix Halo)
-- ============================================================

INSERT INTO cpus (name, cores, threads, base_clock_ghz, boost_clock_ghz, tdp_watts, graphics_model, graphics_cores, cooler_included)
VALUES
    ('AMD Ryzen 9 9950X3D Dual Edition', 16, 32, 4.3, 5.6, 200, 'AMD Radeon Graphics', 2,    'Not Included'),
    ('AMD Ryzen 9 9950X3D',              16, 32, 4.3, 5.7, 170, 'AMD Radeon Graphics', 2,    'Not Included'),
    ('AMD Ryzen 9 9950X',               16, 32, 4.3, 5.7, 170, 'AMD Radeon Graphics', 2,    'Not Included'),
    ('AMD Ryzen 9 9900X3D',             12, 24, 4.4, 5.5, 120, 'AMD Radeon Graphics', 2,    'Not Included'),
    ('AMD Ryzen 9 9900X',               12, 24, 4.4, 5.6, 120, 'AMD Radeon Graphics', 2,    'Not Included'),
    ('AMD Ryzen 7 9850X3D',              8, 16, 4.7, 5.6, 120, 'AMD Radeon Graphics', 2,    'Not Included'),
    ('AMD Ryzen 7 9800X3D',              8, 16, 4.7, 5.2, 120, 'AMD Radeon Graphics', 2,    'Not Included'),
    ('AMD Ryzen 7 9700X',                8, 16, 3.8, 5.5,  65, 'AMD Radeon Graphics', 2,    'Not Included'),
    ('AMD Ryzen 7 9700F',                8, 16, 3.8, 5.5,  65, NULL,                  NULL, 'Not Included'),
    ('AMD Ryzen 5 9600X',                6, 12, 3.9, 5.4,  65, 'AMD Radeon Graphics', 2,    'Not Included'),
    ('AMD Ryzen 5 9600',                 6, 12, 3.8, 5.2,  65, 'AMD Radeon Graphics', 2,    'AMD Wraith Stealth'),
    ('AMD Ryzen 5 9500F',                6, 12, 3.8, 5.0,  65, NULL,                  NULL, 'AMD Wraith Stealth')
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- SEED: Ryzen 8000-series CPUs  (AM5 / Phoenix)
-- ============================================================

INSERT INTO cpus (name, cores, threads, base_clock_ghz, boost_clock_ghz, tdp_watts, graphics_model, graphics_cores, cooler_included)
VALUES
    ('AMD Ryzen 7 8700G', 8, 16, 4.2, 5.1, 65, 'AMD Radeon 780M', 12,   'Available'),
    ('AMD Ryzen 7 8700F', 8, 16, 4.1, 5.0, 65, NULL,              NULL, 'Available'),
    ('AMD Ryzen 5 8600G', 6, 12, 4.3, 5.0, 65, 'AMD Radeon 760M',  8,   'Available'),
    ('AMD Ryzen 5 8500G', 6, 12, 3.5, 5.0, 65, 'AMD Radeon 740M',  4,   'Not Available'),
    ('AMD Ryzen 5 8400F', 6, 12, 4.2, 4.7, 65, NULL,              NULL, 'Not Available'),
    ('AMD Ryzen 3 8300G', 4,  8, 3.4, 4.9, 65, 'AMD Radeon 740M',  4,   'Not Available')
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- SEED: Ryzen 5000-series CPUs  (AM4 / Zen 3)
-- ============================================================

INSERT INTO cpus (name, cores, threads, base_clock_ghz, boost_clock_ghz, tdp_watts, graphics_model, graphics_cores, cooler_included)
VALUES
    ('AMD Ryzen 9 5950X',   16, 32, 3.4, 4.9, 105, NULL,              NULL, 'Not Included'),
    ('AMD Ryzen 9 5900XT',  16, 32, 3.3, 4.8, 105, NULL,              NULL, 'Not Included'),
    ('AMD Ryzen 9 5900X',   12, 24, 3.7, 4.8, 105, NULL,              NULL, 'Not Included'),
    ('AMD Ryzen 7 5800X3D',  8, 16, 3.4, 4.5, 105, NULL,              NULL, 'Not Included'),
    ('AMD Ryzen 7 5800XT',   8, 16, 3.8, 4.8, 105, NULL,              NULL, NULL),
    ('AMD Ryzen 7 5800X',    8, 16, 3.8, 4.7, 105, NULL,              NULL, 'Not Included'),
    ('AMD Ryzen 7 5705GE',   8, 16, 3.2, 4.6,  35, 'AMD Radeon Graphics', 8, NULL),
    ('AMD Ryzen 7 5705G',    8, 16, 3.8, 4.6,  65, 'AMD Radeon Graphics', 8, NULL),
    ('AMD Ryzen 7 5700X3D',  8, 16, 3.0, 4.1, 105, NULL,              NULL, 'Not Included'),
    ('AMD Ryzen 7 5700X',    8, 16, 3.4, 4.6,  65, NULL,              NULL, 'Not Included'),
    ('AMD Ryzen 7 5700G',    8, 16, 3.8, 4.6,  65, 'AMD Radeon Graphics', 8, 'AMD Wraith Stealth'),
    ('AMD Ryzen 7 5700',     8, 16, 3.7, 4.6,  65, NULL,              NULL, 'AMD Wraith Stealth'),
    ('AMD Ryzen 5 5605GE',   6, 12, 3.4, 4.4,  35, 'AMD Radeon Graphics', 7, NULL),
    ('AMD Ryzen 5 5605G',    6, 12, 3.9, 4.4,  65, 'AMD Radeon Graphics', 7, NULL),
    ('AMD Ryzen 5 5600X3D',  6, 12, 3.3, 4.4, 105, NULL,              NULL, 'Not Included'),
    ('AMD Ryzen 5 5600X',    6, 12, 3.7, 4.6,  65, NULL,              NULL, 'AMD Wraith Stealth'),
    ('AMD Ryzen 5 5600XT',   6, 12, 3.7, 4.7,  65, NULL,              NULL, 'AMD Wraith Stealth'),
    ('AMD Ryzen 5 5600T',    6, 12, 3.5, 4.5,  65, NULL,              NULL, 'AMD Wraith Stealth'),
    ('AMD Ryzen 5 5600GT',   6, 12, 3.6, 4.6,  65, 'AMD Radeon Graphics', 7, 'AMD Wraith Stealth'),
    ('AMD Ryzen 5 5600G',    6, 12, 3.9, 4.4,  65, 'AMD Radeon Graphics', 7, 'AMD Wraith Stealth'),
    ('AMD Ryzen 5 5600F',    6, 12, 3.0, 4.0,  65, NULL,              NULL, NULL),
    ('AMD Ryzen 5 5600',     6, 12, 3.5, 4.4,  65, NULL,              NULL, 'AMD Wraith Stealth'),
    ('AMD Ryzen 5 5500X3D',  6, 12, 3.0, 4.0, 105, NULL,              NULL, 'Not Included'),
    ('AMD Ryzen 5 5500GT',   6, 12, 3.6, 4.4,  65, 'AMD Radeon Graphics', 7, 'AMD Wraith Stealth'),
    ('AMD Ryzen 5 5500',     6, 12, 3.6, 4.2,  65, NULL,              NULL, 'AMD Wraith Stealth'),
    ('AMD Ryzen 3 5305GE',   4,  8, 3.6, 4.2,  35, 'AMD Radeon Graphics', 6, NULL),
    ('AMD Ryzen 3 5305G',    4,  8, 4.0, 4.2,  65, 'AMD Radeon Graphics', 6, NULL)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- SEED: Ryzen 4000-series CPUs  (AM4 / Renoir / OEM)
-- ============================================================

INSERT INTO cpus (name, cores, threads, base_clock_ghz, boost_clock_ghz, tdp_watts, graphics_model, graphics_cores, cooler_included)
VALUES
    ('AMD Ryzen 7 4700GE', 8, 16, 3.1, 4.3, 35, 'AMD Radeon Graphics', 8, NULL),
    ('AMD Ryzen 7 4700G',  8, 16, 3.6, 4.4, 65, 'AMD Radeon Graphics', 8, NULL),
    ('AMD Ryzen 5 4600GE', 6, 12, 3.3, 4.2, 35, 'AMD Radeon Graphics', 7, NULL),
    ('AMD Ryzen 5 4600G',  6, 12, 3.7, 4.2, 65, 'AMD Radeon Graphics', 7, NULL),
    ('AMD Ryzen 3 4300GE', 4,  8, 3.5, 4.0, 35, 'AMD Radeon Graphics', 6, NULL)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- SEED: AMD Radeon RX 9000-series GPUs  (RDNA 4)
-- ============================================================

INSERT INTO gpus (name, compute_units, ray_accelerators, ai_accelerators, game_clock_mhz, infinity_cache_mb, vram_gb)
VALUES
    ('AMD Radeon RX 9070 XT',      64, 64, 128, 2400, 64, 16),
    ('AMD Radeon RX 9070',         56, 56, 112, 2070, 64, 16),
    ('AMD Radeon RX 9070 GRE',     48, 48,  96, 2220, 48, 12),
    ('AMD Radeon RX 9060 XT',      32, 32,  64, 2530, 32, 16),
    ('AMD Radeon RX 9060 XT 8GB',  32, 32,  64, 2530, 32,  8),
    ('AMD Radeon RX 9060 XT LP',   32, 32,  64, NULL, 32, 16),
    ('AMD Radeon RX 9060',         28, 28,  56, 2400, 32,  8)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- SEED: AMD Radeon RX 7000-series GPUs  (RDNA 3)
-- ============================================================

INSERT INTO gpus (name, compute_units, ray_accelerators, ai_accelerators, game_clock_mhz, infinity_cache_mb, vram_gb)
VALUES
    ('AMD Radeon RX 7900 XTX', 96, 96, 192, 2300, 96, 24),
    ('AMD Radeon RX 7900 XT',  84, 84, 168, 2000, 80, 20),
    ('AMD Radeon RX 7900 GRE', 80, 80, 160, 1880, 64, 16),
    ('AMD Radeon RX 7800 XT',  60, 60, 120, 2124, 64, 16),
    ('AMD Radeon RX 7700 XT',  54, 54, 108, 2171, 48, 12),
    ('AMD Radeon RX 7700',     40, 40,  80, NULL, 40, 16),
    ('AMD Radeon RX 7600 XT',  32, 32,  64, 2470, 32, 16),
    ('AMD Radeon RX 7600',     32, 32,  64, 2250, 32,  8)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- SEED: AMD Radeon RX 6000-series GPUs  (RDNA 2)
-- NOTE: RDNA 2 does not expose a discrete AI Accelerator count.
-- ============================================================

INSERT INTO gpus (name, compute_units, ray_accelerators, ai_accelerators, game_clock_mhz, infinity_cache_mb, vram_gb)
VALUES
    ('AMD Radeon RX 6950 XT',               80, 80, NULL, 2100, 128, 16),
    ('AMD Radeon RX 6900 XT',               80, 80, NULL, 2015, 128, 16),
    ('AMD Radeon RX 6800 XT Midnight Black', 72, 72, NULL, 2015, 128, 16),
    ('AMD Radeon RX 6800 XT',               72, 72, NULL, 2015, 128, 16),
    ('AMD Radeon RX 6800',                  60, 60, NULL, 1815, 128, 16),
    ('AMD Radeon RX 6750 XT',               40, 40, NULL, 2495,  96, 12),
    ('AMD Radeon RX 6700 XT',               40, 40, NULL, 2424,  96, 12),
    ('AMD Radeon RX 6700',                  36, 36, NULL, 2174,  80, 10),
    ('AMD Radeon RX 6650 XT',               32, 32, NULL, 2410,  32,  8),
    ('AMD Radeon RX 6600 XT',               32, 32, NULL, 2359,  32,  8),
    ('AMD Radeon RX 6600',                  28, 28, NULL, 2044,  32,  8),
    ('AMD Radeon RX 6500 XT',               16, 16, NULL, 2650,  16,  8),
    ('AMD Radeon RX 6500 XT 4GB',           16, 16, NULL, 2610,  16,  4),
    ('AMD Radeon RX 6400',                  12, 12, NULL, 2039,  16,  4)
ON CONFLICT (name) DO NOTHING;