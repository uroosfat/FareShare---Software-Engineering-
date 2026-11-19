# FareShare

A carpooling app for IBA Karachi students (theme: Environment & Sustainability). Students sign up with their `@khi.iba.edu.pk` email, post trips to or from an IBA campus (or find one), request a seat, and share the fare. Fewer cars on the road, lower cost per student.

**Course:** Software Engineering (Scrum), Section 102112, IBA Karachi, Fall 2026
**Team:** Uroos Fatima (31094), Muhammad Shayan Hussain (30077), Waniya Jabeen (31624)

## Quick links and Where to Finds

| What | Where |
|---|---|
| Live backend (API docs) | https://fareshare-api.onrender.com/docs |
| Backend health check | https://fareshare-api.onrender.com/health/db |
| Android app (APK) | GitHub **Releases** page of this repo, newest release, file `FareShare.apk` |
| Trello board | https://trello.com/b/6v93vDaT/fareshare-fall26 |
| Test Plan | Submitted on lms |
| Test cases (197) | Submitted on lms |
| Scrum logs (Planning, Daily Scrum, Review, Retrospective) | https://drive.google.com/drive/folders/1RHxM-jvH4LEDp6Kk4S7_qLlWGRyXZUIw |

## Tech stack

| Layer | Technology |
|---|---|
| Mobile app | Flutter (Dart), Material 3, `go_router`, `http`, `flutter_secure_storage` |
| Backend | FastAPI (Python), SQLAlchemy 2, JWT login (`python-jose`), `bcrypt` |
| Database | PostgreSQL (hosted on Neon) |
| Hosting | Render (backend), GitHub Releases (APK built by GitHub Actions) |
| Testing | pytest + FastAPI TestClient (133 automated tests) |

No Firebase Auth, Cloud Functions or Firestore is used.

## Repository structure

| Folder | What is in it |
|---|---|
| `app/` | Flutter mobile app (`lib/screens`, `lib/api`, `lib/auth`, `lib/widgets`) |
| `backend/` | FastAPI REST API (`app/`), SQL scripts (`db/`), tests (`tests/`), demo data (`seed.py`) |
| `docs/` | Project documents (see the links above) |
| `.github/workflows/` | `build-apk.yml`, builds the Android APK in the cloud |

## Features (Sprint 1)

- **Accounts:** sign up (IBA email only, password rules), log in, stay logged in, log out, edit profile, change password
- **Vehicles:** add, edit and delete a vehicle (a vehicle used by a trip cannot be deleted)
- **Post a trip:** own car or InDrive group, pickup area, IBA City or Main Campus, time, seats, cost, women-only / men-only / anyone
- **Find a trip:** search by pickup place, campus, day and time of day; filter by who can join; trips that are full, past or not allowed for your gender are hidden
- **Requests:** send a request with a message, 10-minute timer, one active request at a time, manager accepts or declines, rider cancels or leaves
- **Privacy:** a driver's phone number is shown to a rider only after the request is accepted
- **Trip flow:** manager confirms the pickup point, then marks the trip completed; riders confirm "Did you travel?" and the completed-trips count is updated
- **My trips:** the trips you manage and the trips you joined

Planned for Sprint 2: Forgot Password by email, push notifications (FCM), Report user.

## Try the app

### Option 1: Android phone (APK)

1. On your phone, open this repository's **Releases** page on GitHub and open the newest release.
2. Download **`FareShare.apk`**.
3. Open the file. If Android asks, allow **Install unknown apps** for your browser, then tap **Install**. If Play Protect warns about the app, tap **Install anyway** (the APK is debug-signed, for demo use).
4. **Wake the server first:** open https://fareshare-api.onrender.com/health/db in the phone browser. The free Render plan sleeps when idle, so the first request can take up to a minute.
5. Open FareShare and log in.

### Option 2: In a browser (for checking)

FareShare is a mobile app, so there is no deployed web version. The same code can run in a browser with Flutter (3.x):

```bash
cd app
flutter pub get
flutter run -d web-server --web-port 5000
```

Then open http://localhost:5000. The app talks to the live backend.

### Demo accounts

Four demo drivers have trips ready: `ayesha.demo`, `hamza.demo`, `sana.demo`, `bilal.demo` (all at `@khi.iba.edu.pk`), password `password1`. Trips go to or from both campuses, so change the campus filter on Home to see them all. Some are women-only or men-only, so what a rider sees depends on their gender. To act as a rider, sign up with your own `@khi.iba.edu.pk` email, or use a second demo account.

These are demo accounts with no real personal data.

## Run the backend locally

You need Python 3.11+ and a PostgreSQL database (local, or a free Neon project).

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env, then fill in the values
uvicorn app.main:app --reload
```

`.env` needs `DATABASE_URL`, `JWT_SECRET` and `ALLOWED_EMAIL_DOMAIN` (`khi.iba.edu.pk`). The `.env` file is never committed.

Create the tables by running the scripts in `backend/db/` on your database, in order: `schema.sql`, then the `migration_*.sql` files. To add the demo drivers and trips, run `python seed.py` from the `backend` folder.

Open http://127.0.0.1:8000/health (you should see `{"status":"ok"}`) and http://127.0.0.1:8000/docs for the API docs.

## Run the tests

```bash
cd backend
# with the virtual environment active
pip install pytest httpx
python -m pytest -v
```

The 133 tests use a throwaway in-memory database, so the real database is never touched. They cover sign up and login, vehicles, posting and searching trips, requests and the 10-minute timer, confirm pickup, completing a trip, permissions and privacy rules. The manual test cases for the app screens are in the Test cases sheet linked above.

## Build the Android APK

The workflow in `.github/workflows/build-apk.yml` builds `FareShare.apk` on GitHub's servers and publishes it as a GitHub Release. Open the **Actions** tab, choose **Build Android APK**, and run it (it also runs when `feature/android-apk` is pushed). Building locally needs the Android SDK and NDK: `cd app && flutter build apk --release`.

## API overview

The full, live list is at `/docs`. Main groups:

| Group | Endpoints |
|---|---|
| Auth and profile | `POST /auth/register`, `POST /auth/login`, `GET/PUT /me`, `POST /auth/change-password` |
| Vehicles | `GET/POST /vehicles`, `PUT/DELETE /vehicles/{id}` |
| Trips | `POST /trips`, `GET /trips` (search), `GET /trips/mine`, `GET/PUT /trips/{id}`, `POST /trips/{id}/cancel`, `/confirm`, `/complete`, `GET /trips/{id}/riders` |
| Requests | `POST /trips/{id}/requests`, `GET /requests/sent`, `GET /requests/received`, `POST /requests/{id}/accept`, `/decline`, `/cancel`, `/leave`, `/confirm-travel` |

## Team workflow (the rule)

1. Never commit directly to `main`.
2. Start every task from a Trello card: `git checkout main && git pull`, then `git checkout -b feature/<short-name>` (for example `feature/register-api`).
3. Commit small and often, with clear messages.
4. Push the branch and open a **pull request** into `main`. Link the Trello card in the description.
5. At least one other teammate reviews it and ticks the Definition of Done checklist before it is merged.
6. Merge, delete the branch, move the Trello card to Done.

Branch prefixes: `feature/`, `fix/`, `docs/`.

## Notes

- The backend runs on Render's free plan and the database on Neon's free plan. Both sleep when idle, so the first request after a pause can take up to a minute.
- Secrets (database URL, JWT secret) are kept in environment variables and are not in the repository.
