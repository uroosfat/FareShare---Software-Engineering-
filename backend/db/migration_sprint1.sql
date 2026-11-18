-- Sprint 1 migration: request expiry timer.
-- Run once in the Neon SQL Editor (and in local pgAdmin). Safe to run twice.

ALTER TABLE trip_requests ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- Drop whatever CHECK constraint currently limits trip_requests.status ...
DO $$
DECLARE c text;
BEGIN
  FOR c IN
    SELECT conname FROM pg_constraint
    WHERE conrelid = 'trip_requests'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) ILIKE '%status%'
  LOOP
    EXECUTE format('ALTER TABLE trip_requests DROP CONSTRAINT %I', c);
  END LOOP;
END $$;

-- ... and add one that also allows 'cancelled' and 'expired'.
ALTER TABLE trip_requests
  ADD CONSTRAINT trip_requests_status_check
  CHECK (status IN ('pending', 'accepted', 'declined', 'cancelled', 'expired'));
