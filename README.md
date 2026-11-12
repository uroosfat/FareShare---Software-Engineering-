# FareShare

A carpooling app for IBA Karachi students (theme: Environment & Sustainability). Students sign in with their @khi.iba.edu.pk email, post or find trips, and share the fare.

**Team (Section 102112):** Uroos Fatima (31094), Muhammad Shayan Hussain (30077), Waniya Jabeen (31624)

## Structure

| Folder | What is in it |
|---|---|
| `app/` | Flutter mobile app |
| `backend/` | FastAPI REST API (Python) |
| `docs/` | Wireframes, test plan, Scrum logs, schema notes |

## Tech stack
Flutter (Dart), FastAPI (Python), PostgreSQL. No Firebase Auth, Cloud Functions or Firestore.

## Run the backend locally
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in the values
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/health, you should see `{"status":"ok"}`. API docs are at `/docs`.

## Run the app
```bash
cd app
flutter pub get
flutter run
```

## Team workflow (the rule)
1. Never commit directly to `main`.
2. Start every task from a Trello card: `git checkout main && git pull`, then `git checkout -b feature/<short-name>` (for example `feature/register-api`).
3. Commit small and often, with clear messages.
4. Push the branch and open a **pull request** into `main`. Link the Trello card in the description.
5. At least one other teammate reviews it and ticks the Definition of Done checklist before it is merged.
6. Merge, delete the branch, move the Trello card to Done.

Branch prefixes: `feature/`, `fix/`, `docs/`.
