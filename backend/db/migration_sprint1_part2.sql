-- Sprint 1, part 2: confirm pickup and mark complete.
-- Run once in the Neon SQL Editor (and in local pgAdmin). Safe to run twice.
ALTER TABLE trips ADD COLUMN IF NOT EXISTS pickup_point VARCHAR(150);
ALTER TABLE trip_requests ADD COLUMN IF NOT EXISTS manager_marked BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE trip_requests ADD COLUMN IF NOT EXISTS rider_confirmed BOOLEAN;
