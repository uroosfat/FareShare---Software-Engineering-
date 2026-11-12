-- FareShare PostgreSQL schema (Sprint 1)
-- Run in pgAdmin: create a database named "fareshare", open Query Tool, paste, run (F5).

DROP TABLE IF EXISTS trip_requests CASCADE;
DROP TABLE IF EXISTS trips CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    user_id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name               VARCHAR(100) NOT NULL,
    email                   VARCHAR(150) NOT NULL UNIQUE,
    password_hash           VARCHAR(255) NOT NULL,          -- bcrypt hash, never the plain password
    gender                  VARCHAR(10)  NOT NULL CHECK (gender IN ('female', 'male')),
    phone                   VARCHAR(20),
    completed_trips_count   INTEGER      NOT NULL DEFAULT 0 CHECK (completed_trips_count >= 0),
    fcm_token               VARCHAR(255),                   -- device token for push (Sprint 2)
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT users_iba_email CHECK (lower(email) LIKE '%@khi.iba.edu.pk')
);

CREATE TABLE vehicles (
    vehicle_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    owner_id        INTEGER      NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    make            VARCHAR(50)  NOT NULL,
    model           VARCHAR(50)  NOT NULL,
    color           VARCHAR(30)  NOT NULL,
    plate_number    VARCHAR(20)  NOT NULL,
    total_seats     INTEGER      NOT NULL CHECK (total_seats BETWEEN 1 AND 8),
    UNIQUE (owner_id, plate_number)
);

CREATE TABLE trips (
    trip_id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    manager_id          INTEGER        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    vehicle_id          INTEGER        REFERENCES vehicles(vehicle_id) ON DELETE SET NULL,  -- NULL when the group books an InDrive
    origin_area         VARCHAR(100)   NOT NULL,
    destination_area    VARCHAR(100)   NOT NULL,
    departure_time      TIMESTAMPTZ    NOT NULL,
    available_seats     INTEGER        NOT NULL CHECK (available_seats >= 0),
    cost_per_person     NUMERIC(8,2)   NOT NULL DEFAULT 0 CHECK (cost_per_person >= 0),  -- recorded only, no payments
    gender_filter       VARCHAR(10)    NOT NULL DEFAULT 'any' CHECK (gender_filter IN ('any', 'female', 'male')),
    status              VARCHAR(15)    NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'confirmed', 'completed', 'cancelled')),
    created_at          TIMESTAMPTZ    NOT NULL DEFAULT now()
);

CREATE TABLE trip_requests (
    request_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id         INTEGER      NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
    requester_id    INTEGER      NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    status          VARCHAR(15)  NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'accepted', 'declined', 'cancelled')),
    message         VARCHAR(300),
    requested_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    responded_at    TIMESTAMPTZ,
    UNIQUE (trip_id, requester_id)      -- one request per rider per trip
);

-- Indexes for the search/filter screens and "my trips" lists
CREATE INDEX idx_trips_status_departure ON trips (status, departure_time);
CREATE INDEX idx_trips_manager          ON trips (manager_id);
CREATE INDEX idx_requests_trip          ON trip_requests (trip_id);
CREATE INDEX idx_requests_requester     ON trip_requests (requester_id);
