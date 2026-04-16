# Math_JIHC

A greenfield full-stack implementation of the provided student/admin math learning screens:

- `frontend/`: Next.js App Router frontend in React + Tailwind
- `backend/`: FastAPI backend with SQLite, task upload, auth, dashboard data, and cached read endpoints

## Included flows

- Student login
- Student dashboard
- Student test interface
- Admin login
- Admin dashboard
- Admin task management with create, edit, delete, and image upload

## Performance work

- Frontend same-origin proxy from Next.js to FastAPI
- In-flight request deduping in the frontend client
- TTL response cache for hot GET routes in the frontend
- FastAPI in-memory response cache with ETag support for hot GET routes
- Cache invalidation after submissions and task mutations
- SQLite WAL mode and indexes for hot lookup paths
- GZip enabled in FastAPI

## Demo accounts

- Student: `student@oasis.edu` / `student123`
- Admin: `admin@mathacademy.edu` / `admin123`

## Run backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs on `http://127.0.0.1:8000`.

## Run frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

The app runs on `http://127.0.0.1:3000`.

## Notes

- Uploaded task images are stored in `backend/uploads/`.
- SQLite is stored in `backend/data.sqlite3` and is auto-seeded on first boot.
- The frontend proxy expects the backend at `NEXT_SERVER_API_URL`.
