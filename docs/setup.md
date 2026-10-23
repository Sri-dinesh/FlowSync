# Development setup

## Environments

Use Python 3.11 for new installations: CPU Torch 2.3.1/Torchvision 0.18.1 wheels
and NumPy below 2 are the current installation baseline. Preserve existing
research environments and recorded dependency provenance. Use Node.js 24
(`.nvmrc`) and npm 10 or newer; Next.js requires Node 20.9 or newer.

From the repository root:

```bash
python3.11 -m venv server/.venv
server/.venv/bin/python -m pip install -r research/requirements.txt -r server/requirements-dev.txt
cp server/.env.example server/.env
cp client/.env.example client/.env.local
npm --prefix client ci
```

For just the application install `server/requirements.txt`. Optional detector
inference, training, dataset and export tools are in `server/requirements-vision.txt`.
Weights/datasets are not bundled. Camera startup may download an upstream model
when local weights and optional dependencies are available.

On Windows use `py -3.11 -m venv server/.venv`, then
`server\.venv\Scripts\python.exe` instead of the POSIX Python path. An existing
`server/venv` is also supported and is not renamed or deleted.

## Private configuration

Fill the environment files with values from your own development project:

| File | Variable | Purpose |
| --- | --- | --- |
| `server/.env` | `SUPABASE_URL` | Supabase project API URL |
| `server/.env` | `SUPABASE_SERVICE_KEY` | Server secret/service-role key |
| `server/.env` | `CORS_ORIGINS` | Comma-separated browser origins |
| `server/.env` | `SIGNAL_RED_DURATION` | Application all-red duration, default 3 seconds |
| `client/.env.local` | `DATABASE_URL` | PostgreSQL URL for Prisma; pooling may be required by hosting |
| `client/.env.local` | `DIRECT_URL` | Direct connection for schema management |
| `client/.env.local` | `NEXT_PUBLIC_SUPABASE_URL` | Public project URL |
| `client/.env.local` | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Public client key |
| `client/.env.local` | `NEXT_PUBLIC_FASTAPI_HTTP_URL` | HTTP backend, default `http://localhost:8000` |
| `client/.env.local` | `NEXT_PUBLIC_FASTAPI_WS_URL` | WebSocket backend, default `ws://localhost:8000` |

The backend also recognizes `SUPABASE_SECRET_KEY` and
`SUPABASE_SERVICE_ROLE_KEY`. It loads `server/.env` using an absolute path.
Never put a server secret/service-role key in a `NEXT_PUBLIC_` variable. Browser
values are embedded during the frontend build; hosted deployments need HTTPS/WSS.
Hosted browser origins must be listed explicitly in `CORS_ORIGINS`. Only local
development origins are added by default; arbitrary HTTP origins and the original
project's hosted domains are not implicitly trusted. CORS is not authentication.

## Database and storage

The schema is `client/prisma/schema.prisma`; the scenario SQL migration is
under `server/data/migrations/`. Use a dedicated development project. For a new,
empty development database, `npx prisma db push` from `client/` can initialize
the schema. Review schema changes before applying them to an existing database.
`npm ci` generates the Prisma client but does not apply a database schema.

Checkpoint persistence uses the `model-checkpoints` Supabase Storage bucket
and local `server/models/` files. Configure the bucket/permissions in your own
project. Verify model IDs, checkpoint metadata and hashes; a dashboard episode
label alone does not establish which weights were used.

## Run the application

Start services in separate terminals:

```bash
server/.venv/bin/python -m uvicorn app.main:app --app-dir server --reload --port 8000
npm --prefix client run dev
```

Dashboard: `http://localhost:3000`; API docs: `http://localhost:8000/docs`;
health: `http://localhost:8000/health`. Keep `research/` alongside `server/`:
the API imports research sensor/controller support modules.

## Containers and hosting

```bash
docker compose up --build server
```

Compose starts the backend only. It does not provision Supabase or start the
frontend. The repository-root build context includes the research modules
needed by the API. `.dockerignore` excludes local secrets and artifacts;
`server/.env` is supplied at runtime. Optional vision tools/weights require a
separately prepared image or local installation.

`render.yaml` describes backend hosting. Deploy the frontend from `client/`
with `npm ci` and `npm run build`, configuring its environment in the host.
Review [security scope](../SECURITY.md) before exposing an instance; hosting
configuration alone does not make this research service publicly hardened.
