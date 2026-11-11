# Law Firm Case Management

A platform for running one litigation firm: matters, hearings and case history, deadlines, documents, lawyers, clients, conflict checks and firm analytics. The design and schema notes are in [PROJECT_GUIDE.md](PROJECT_GUIDE.md).

## What it does

| Area | What you get |
|---|---|
| Matters | Open and edit matters, assign counsel, track status through to disposal and outcome |
| Case history | One timeline of hearings, remarks, status changes, documents and counsel changes |
| Hearings | Calendar and printable cause list, recording results, listing the next date in one step |
| Tasks and deadlines | Limitation, filing, reply and compliance dates, plus day-to-day tasks |
| Documents | Upload and download files per matter, up to 50 MB, stored in MongoDB |
| Team | Request-to-join with admin approval, or admin-created accounts with temporary passwords |
| Conflict check | Warns when a client is an opposing party elsewhere, or the reverse |
| Search | Across matters, people and documents, limited to what you may see |
| Analytics | Workload, matters with no next date, adjournment rates, time to disposal, outcomes |
| Audit log | Who did what, including file downloads. Entries cannot be changed |

### Who can do what

The API enforces these rules, not just the screens.

| | Admin | Lawyer | Staff |
|---|---|---|---|
| Open matters | All | Their own. Titles and numbers only for the rest | All |
| Hearings, tasks, remarks, documents | All | On their own matters | All |
| Edit a matter, change its status | Yes | Their own | No |
| Assign counsel | Yes | Where they are lead | No |
| Delete matters | Yes | No | No |
| Analytics, team, audit log | Yes | No | No |

## Tech stack

| Part | Tools |
|---|---|
| Backend | FastAPI, SQLAlchemy, Pydantic, JWT |
| Databases | PostgreSQL for records (Alembic migrations), MongoDB GridFS for files |
| Frontend | React, Material UI, Recharts, Axios. Runs in a browser or Electron |
| ML | scikit-learn, statsmodels |

## Running on Linux

Commands are marked:

- **ONE-TIME**: run once per machine.
- **EVERY TIME**: run each time you start the app.
- **OCCASIONAL**: run only when the stated condition applies.

All commands start from the project root unless they show a `cd`.

### Short version

If setup is already done, open two terminals:

```bash
# Terminal 1: backend
docker start law-firm-postgres law-firm-mongo
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

```bash
# Terminal 2: frontend
cd frontend
npm run dev
```

Then open http://localhost:5173. For the desktop window, run `npm run electron:start` instead of `npm run dev`.

## First-time setup

### 1. Install the prerequisites (ONE-TIME)

You need Python 3.11+ (tested on 3.14), Node.js 18+ (tested on 22), and Docker.

```bash
python3 --version
node -v
docker --version
```

### 2. Start the databases (ONE-TIME)

Replace `YOUR_PASSWORD` with a strong password. You will use it again in step 3. Skip a `docker run` if `docker ps -a` already lists that container.

```bash
docker run -d --name law-firm-postgres --restart unless-stopped --network host \
  -e POSTGRES_PASSWORD=YOUR_PASSWORD \
  -e POSTGRES_DB=law_firm_db \
  -v law_firm_pgdata:/var/lib/postgresql/data \
  postgres:16 -c listen_addresses=localhost

docker run -d --name law-firm-mongo --restart unless-stopped --network host \
  -v law_firm_mongodata:/data/db \
  mongo:7 --bind_ip 127.0.0.1
```

Both listen on this machine only. Check that they are ready:

```bash
docker exec law-firm-postgres pg_isready -U postgres      # "accepting connections"
docker exec law-firm-mongo mongosh --quiet --eval 'db.runCommand({ping:1}).ok'      # 1
```

### 3. Set up the backend (ONE-TIME)

`requirements.txt` is in the project root, not in `backend/`.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edit `backend/.env` and set these two lines, using the key the last command printed:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/law_firm_db
SECRET_KEY=the-key-you-just-generated
```

If the password contains symbols such as `@`, `:` or `$`, URL-encode them in `DATABASE_URL` (`$` becomes `%24`).

### 4. Create the database tables (ONE-TIME)

```bash
cd backend
source venv/bin/activate
alembic upgrade head                  # PostgreSQL: tables, triggers, views
python -m mongo_migrations upgrade    # MongoDB: file storage and indexes
```

**If you loaded the old `law_firm_schema.sql` before migrations existed**, run `alembic stamp 0001` once before `alembic upgrade head`. Your data is kept.

### 5. Train the matter type suggestion (ONE-TIME)

Trained `.pkl` files are not stored in git, so each machine trains its own. Until then, "Suggest matter type" reports that it isn't trained. Everything else works.

```bash
cd backend
source venv/bin/activate
pip install pandas numpy scikit-learn joblib statsmodels
python train_models.py --model classifier
```

This takes under a minute and needs no database. The full `requirements-ml.txt` is not needed: it also installs very large packages such as `torch`.

### 6. Set up the frontend (ONE-TIME)

```bash
cd frontend
npm install
```

### 7. Create the first admin (ONE-TIME)

Start the app (next section), open http://localhost:5173 and choose **Set up the first admin account**. The first account created is always the admin. After that, people join through **Request to join**, or an admin adds them under **Team & access**.

### Optional: load the demo firm (ONE-TIME)

For trying things out. **Do not do this on a real firm's database.** It adds sample records and accounts with published passwords. Run it instead of step 7, on an empty database:

```bash
docker exec -i law-firm-postgres psql -U postgres -d law_firm_db -v ON_ERROR_STOP=1 < database/sample_data.sql
docker exec -i law-firm-postgres psql -U postgres -d law_firm_db -v ON_ERROR_STOP=1 < database/sample_activity.sql
```

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | admin |
| `lawyer1` | `lawyer123` | lawyer |
| `staff1` | `staff123` | staff |

## Starting the app (EVERY TIME)

**1. Make sure the databases are running.** They restart with the machine, so this is usually a no-op.

```bash
docker start law-firm-postgres law-firm-mongo
```

**2. Start the backend in one terminal, and leave it running.**

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

The API is at http://localhost:8000 and its interactive docs are at http://localhost:8000/docs.

**3. Start the frontend in a second terminal.**

```bash
cd frontend
npm run dev                  # browser: http://localhost:5173
npm run electron:start       # or the desktop window
```

To stop, press `Ctrl+C` in both terminals. The containers keep running until you run `docker stop law-firm-postgres law-firm-mongo`.

## Occasional commands

**After pulling new code:** a change can include new migrations or packages, so run all of these.

```bash
cd backend
source venv/bin/activate
pip install -r ../requirements.txt
alembic upgrade head
python -m mongo_migrations upgrade
cd ../frontend
npm install
```

**See or undo migrations:**

```bash
cd backend
source venv/bin/activate
alembic current                       # PostgreSQL: where you are
alembic history
alembic downgrade -1                  # undo the last one (can lose its data)
python -m mongo_migrations status     # MongoDB
python -m mongo_migrations downgrade  # undo the last one
```

**Write a new migration.** Add a file to `backend/migrations/versions/` by hand, using an existing one as the pattern, or to `backend/mongo_migrations/` for MongoDB (`m003_name.py` with `upgrade(db)` and `downgrade(db)`). Avoid `alembic revision --autogenerate`: indexes, triggers and views live only in migrations, so it would propose dropping them.

**Back up the databases.** Run this regularly on real data. Records and files live separately, so you need both.

```bash
docker exec law-firm-postgres pg_dump -U postgres -Fc law_firm_db > law_firm_db_$(date +%F).dump
docker exec law-firm-mongo mongodump --quiet --db law_firm_documents --archive > law_firm_files_$(date +%F).archive
```

**Restore from a backup.** This overwrites what is there.

```bash
docker exec -i law-firm-postgres pg_restore -U postgres -d law_firm_db --clean --if-exists < YOUR_BACKUP.dump
docker exec -i law-firm-mongo mongorestore --quiet --drop --archive < YOUR_BACKUP.archive
```

**Reset to an empty database.** This deletes all PostgreSQL data.

```bash
cd backend
source venv/bin/activate
alembic downgrade base
alembic upgrade head
```

**Run the tests.** They create and delete their own databases, and need both containers running.

```bash
cd backend
source venv/bin/activate
python -m pytest tests -q
```

**Retrain models** when the data changes, or train the older locality and forecast models, which are admin-only API routes. These two need the database URL, because `train_models.py` does not read `.env`:

```bash
cd backend
source venv/bin/activate
export "$(grep '^DATABASE_URL=' .env)"
python train_models.py --model all
```

**Rebuild the classifier's training data.** You normally don't need this, because `backend/ml_data/matter_types.csv` is in git. See the notes at the top of `backend/ml_data/build_matter_dataset.py`.

**Point the frontend at another server** when building: `VITE_API_URL=https://your-server/api/v1 npm run build`.

## Troubleshooting

**Port 8000 or 5173 is already in use**

```bash
ss -ltnp | grep -E ':8000|:5173'
kill <PID>
```

**Backend can't connect to the database**

```bash
docker ps                                  # are both containers up?
grep '^DATABASE_URL=' backend/.env         # does the password match?
```

**`column ... does not exist` or `relation ... does not exist`**: the database is behind the code. Run `alembic upgrade head` from `backend/`.

**`No module named ...`**: the virtual environment isn't active. Run `source venv/bin/activate` from `backend/`.

**"File storage is not reachable"**: MongoDB isn't running. Run `docker start law-firm-mongo`.

**"Matter classifier not trained"**: run step 5.

**Connection reset on a published Docker port**: use `--network host` as shown in step 2, rather than `-p`.

**"Login failed" in the app**: check that the backend is running, and that `ALLOWED_ORIGINS` in `backend/.env` includes `http://localhost:5173`.

**A lawyer sees no matters**: their account may not be linked to a lawyer record, or they aren't assigned to anything. Check under **Team & access** and on the matter.

**Electron says it failed to install, or won't open**

```bash
cd frontend
node node_modules/electron/install.js
```

If it reports a sandbox error (`chrome-sandbox` or `setuid`), use the browser, or start Electron with the sandbox off, for local development only:

```bash
npm run dev                                                                            # terminal 1
npx wait-on http://localhost:5173 && NODE_ENV=development npx electron . --no-sandbox   # terminal 2
```

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # App entry point
│   │   ├── config.py          # Settings loaded from .env
│   │   ├── ai_models/         # Classifier, locality model, forecaster
│   │   ├── core/              # Security, role rules (permissions.py), audit log
│   │   ├── models/            # Database models
│   │   ├── schemas/           # Request and response schemas
│   │   └── routers/           # API endpoints
│   ├── migrations/            # PostgreSQL migrations (Alembic)
│   ├── mongo_migrations/      # MongoDB migrations
│   ├── ml_data/               # Classifier training data and its build script
│   ├── tests/                 # API tests
│   └── train_models.py        # Trains the ML models
├── frontend/
│   ├── electron/main.js       # Electron main process
│   └── src/
│       ├── theme.js           # Colors, fonts, component styles
│       ├── components/        # ui.jsx (shared parts), work.jsx, MatterForm, Layout
│       ├── context/           # Login state
│       ├── hooks/             # Data loading
│       ├── pages/             # Screens
│       └── services/api.js    # API client
├── database/
│   ├── sample_data.sql        # Demo firm (optional)
│   └── sample_activity.sql    # Demo hearings and tasks (optional)
├── requirements.txt           # Backend packages
└── requirements-ml.txt        # Every optional ML package (very large)
```

## Contributing

```bash
git pull origin main
git checkout -b feature/your-feature-name
git add <files>
git commit -m "Add: your feature description"
git push origin feature/your-feature-name
```

Then open a pull request.
