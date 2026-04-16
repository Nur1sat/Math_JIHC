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

## Deployment

### Environment variables

Set these values before deploying:

- Vercel frontend:
  - `NEXT_SERVER_API_URL=https://your-render-service.onrender.com`
- Render backend:
  - `ENVIRONMENT=production`
  - `SECRET_KEY=<long-random-secret>` if you do not use the generated value from `render.yaml`
  - `CORS_ALLOW_ORIGINS=https://your-vercel-project.vercel.app`

Optional backend overrides:

- `DATABASE_PATH`
- `UPLOADS_DIR`
- `TOKEN_TTL_SECONDS`
- `CACHE_TTL_SECONDS`
- `MAX_UPLOAD_SIZE_BYTES`

### Deploy the frontend to Vercel

1. Import this repository into Vercel.
2. Set the project Root Directory to `frontend`.
3. Confirm the framework is detected as Next.js.
4. Add `NEXT_SERVER_API_URL` and point it to your Render backend URL, for example `https://math-jihc-api.onrender.com`.
5. Deploy.

The frontend already proxies all API and upload traffic through Next.js route handlers, so the browser talks to the Vercel app and Vercel forwards requests to Render server-side.

### Deploy the backend to Render

This repository includes a root-level `render.yaml` Blueprint for the FastAPI service.

1. Push the repo to GitHub, GitLab, or Bitbucket.
2. In Render, create a new Blueprint and point it at this repository.
3. Render will detect `render.yaml` and create a free Python web service rooted at `backend/`.
4. Set `CORS_ALLOW_ORIGINS` to your Vercel production URL.
5. Deploy the service.

If you create the service manually instead of using the Blueprint, use:

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `./start.sh`
- Health Check Path: `/health`
- Instance Type: `Free`

### Connect the frontend to the backend

After Render gives you an `.onrender.com` URL:

1. Copy that URL into the Vercel environment variable `NEXT_SERVER_API_URL`.
2. Redeploy the Vercel project if prompted.
3. Set Render `CORS_ALLOW_ORIGINS` to the Vercel production domain and redeploy Render.

### Custom domain or free subdomain later

- Vercel: add your custom domain or free subdomain in the project Domains settings, then update Render `CORS_ALLOW_ORIGINS` to include that HTTPS origin.
- Render: you can also attach a custom backend domain later, but it is not required for this setup because the frontend only needs the Render service URL as its upstream.

### Free-tier caveats

- Render Free web services spin down after 15 minutes of inactivity and can take about a minute to wake up again.
- Render Free web services use an ephemeral filesystem, so `backend/data.sqlite3` and `backend/uploads/` are reset on redeploy, restart, or spin-down.
- This makes the current SQLite-plus-local-uploads backend suitable for demos and evaluation on the free tier, but not for durable production data.
